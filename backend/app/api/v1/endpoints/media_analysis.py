import re

from fastapi import APIRouter, File, Form, UploadFile

from app.core.config import settings
from app.core.dependencies import CurrentUser, Database
from app.core.errors import APIError
from app.models import Verification
from app.schemas.verification import VerificationEvidence, VerificationRead
from app.services.verification_media import (
    MEDIA_LIMITATIONS,
    analyze_image_bytes,
    analyze_transcript,
    analyze_video_frames,
    extract_video_frames,
    transcribe_audio,
    validate_audio_duration,
)

router = APIRouter(prefix="/media-analysis", tags=["Media analysis"])
DISCLAIMERS = (
    "Automated media review is fallible and cannot establish authenticity or prove manipulation. "
    "Do not label media fake based only on AI indicators or scores. Human review is required."
)
SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
AUDIO_EXTENSIONS = {
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mp4": ".m4a",
    "audio/ogg": ".ogg",
    "audio/webm": ".webm",
}
VIDEO_EXTENSIONS = {
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
}


async def _read_limited(file: UploadFile) -> bytes:
    content = await file.read(settings.max_media_size_bytes + 1)
    if not content:
        raise APIError(400, "empty_media", "The uploaded media is empty.")
    if len(content) > settings.max_media_size_bytes:
        raise APIError(413, "media_too_large", "The uploaded media exceeds the configured size limit.")
    return content


def _validate_signature(content: bytes, content_type: str, media_kind: str) -> None:
    if media_kind == "image":
        valid = (
            (content_type == "image/jpeg" and content.startswith(b"\xff\xd8\xff"))
            or (content_type == "image/png" and content.startswith(b"\x89PNG\r\n\x1a\n"))
            or (
                content_type == "image/webp"
                and content.startswith(b"RIFF")
                and content[8:12] == b"WEBP"
            )
        )
    elif media_kind == "audio":
        valid = (
            (content_type == "audio/mpeg" and (content.startswith(b"ID3") or _has_mp3_frame_sync(content)))
            or (
                content_type in {"audio/wav", "audio/x-wav"}
                and content.startswith(b"RIFF")
                and content[8:12] == b"WAVE"
            )
            or (content_type == "audio/ogg" and content.startswith(b"OggS"))
            or (
                content_type in {"audio/mp4", "audio/webm"}
                and len(content) >= 12
                and content[4:8] == b"ftyp"
            )
            or (content_type == "audio/webm" and content.startswith(b"\x1a\x45\xdf\xa3"))
        )
    else:
        valid = (
            (content_type in {"video/mp4", "video/quicktime"} and len(content) >= 12 and content[4:8] == b"ftyp")
            or (content_type == "video/webm" and content.startswith(b"\x1a\x45\xdf\xa3"))
        )
    if not valid:
        raise APIError(415, "invalid_media", "The media bytes do not match the declared media type.")


def _has_mp3_frame_sync(content: bytes) -> bool:
    return len(content) >= 2 and content[0] == 0xFF and content[1] & 0xE0 == 0xE0


def _read_result(
    record: Verification,
    provider: str,
) -> VerificationRead:
    return VerificationRead(
        id=record.id,
        subject_type=record.subject_type,
        provider=provider,
        assessment=record.assessment,
        confidence=record.confidence,
        analysis=record.analysis,
        sources=record.sources,
        evidence=record.evidence,
        transcript=record.transcript,
        limitations=record.limitations or MEDIA_LIMITATIONS,
        created_at=record.created_at,
        disclaimer=DISCLAIMERS,
    )


@router.post("/images", response_model=VerificationRead, status_code=201)
async def analyze_image(
    user: CurrentUser,
    db: Database,
    file: UploadFile = File(...),
    context: str = Form(default="", max_length=4_000),
) -> VerificationRead:
    if file.content_type not in SUPPORTED_IMAGE_TYPES:
        raise APIError(415, "unsupported_media_type", "Upload a JPEG, PNG, or WebP image.")
    content = await _read_limited(file)
    _validate_signature(content, file.content_type, "image")
    analysis, provider = await analyze_image_bytes(content, file.content_type, context)
    evidence = [
        VerificationEvidence(kind="visual_observation", description=item[:2_000])
        for item in analysis.observations
        if item.strip()
    ]
    record = Verification(
        user_id=user.id,
        subject="Uploaded image",
        subject_type="image",
        provider=provider,
        assessment=analysis.assessment,
        confidence=analysis.confidence,
        analysis=analysis.analysis,
        sources=[],
        evidence=[item.model_dump(mode="json") for item in evidence],
        limitations=MEDIA_LIMITATIONS,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _read_result(record, provider)


@router.post("/audio", response_model=VerificationRead, status_code=201)
async def analyze_audio(
    user: CurrentUser,
    db: Database,
    file: UploadFile = File(...),
    context: str = Form(default="", max_length=4_000),
) -> VerificationRead:
    content_type = file.content_type or ""
    extension = AUDIO_EXTENSIONS.get(content_type)
    if extension is None:
        raise APIError(415, "unsupported_media_type", "Upload MP3, WAV, M4A, OGG, or WebM audio.")
    content = await _read_limited(file)
    _validate_signature(content, content_type, "audio")
    validate_audio_duration(content)
    safe_filename = f"audio{extension}"
    transcript, transcription_provider = await transcribe_audio(content, safe_filename, content_type)
    analysis, provider = await analyze_transcript(transcript, context)
    transcript_excerpt = re.sub(r"\s+", " ", transcript).strip()[:1_000]
    evidence = (
        [
            VerificationEvidence(
                kind="transcript_excerpt",
                description=f"Machine-generated transcript (may contain transcription errors): {transcript_excerpt}",
            )
        ]
        if transcript_excerpt
        else []
    )
    record = Verification(
        user_id=user.id,
        subject="Uploaded audio",
        subject_type="audio",
        provider=f"{transcription_provider}+{provider}",
        assessment="inconclusive",
        confidence=None,
        analysis=analysis.analysis,
        sources=[],
        evidence=[item.model_dump(mode="json") for item in evidence],
        limitations=[
            *MEDIA_LIMITATIONS,
            "Speech recognition can mishear words, names, accents, or background speech; verify against the original audio.",
            "No trusted external sources were compared, so spoken claims remain unverified.",
        ],
        transcript=transcript,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _read_result(record, record.provider)


@router.post("/videos", response_model=VerificationRead, status_code=201)
async def analyze_video(
    user: CurrentUser,
    db: Database,
    file: UploadFile = File(...),
    context: str = Form(default="", max_length=4_000),
) -> VerificationRead:
    content_type = file.content_type or ""
    extension = VIDEO_EXTENSIONS.get(content_type)
    if extension is None:
        raise APIError(415, "unsupported_media_type", "Upload an MP4, MOV, or WebM video.")
    content = await _read_limited(file)
    _validate_signature(content, content_type, "video")
    frames = extract_video_frames(content, extension)
    analysis, provider = await analyze_video_frames(frames, context)
    evidence = []
    for observation in analysis.frame_observations:
        if observation.frame_index < len(frames):
            evidence.append(
                VerificationEvidence(
                    kind="video_frame_observation",
                    description=observation.description,
                    timestamp_seconds=frames[observation.frame_index][0],
                )
            )
    record = Verification(
        user_id=user.id,
        subject="Uploaded video",
        subject_type="video",
        provider=provider,
        assessment=analysis.assessment,
        confidence=analysis.confidence,
        analysis=analysis.analysis,
        sources=[],
        evidence=[item.model_dump(mode="json") for item in evidence],
        limitations=[
            *MEDIA_LIMITATIONS,
            f"Only {len(frames)} sampled frames were analyzed; events between frames may be missed.",
            "Audio tracks are not analyzed in video uploads.",
        ],
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _read_result(record, provider)
