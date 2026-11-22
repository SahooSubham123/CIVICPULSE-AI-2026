def test_registration_and_login(client):
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "resident@example.test",
            "full_name": "Resident One",
            "password": "long-enough-password",
        },
    )
    assert registration.status_code == 201
    assert "password_hash" not in registration.json()

    login = client.post(
        "/api/v1/auth/login",
        data={"username": "resident@example.test", "password": "long-enough-password"},
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"


def test_grievance_is_private_and_trackable(client, citizen, monkeypatch):
    from app.api.v1.endpoints import grievances
    from app.core.errors import APIError

    async def unavailable_assessment(*_args):
        del _args
        raise APIError(503, "ai_provider_unavailable", "AI triage is not configured.")

    monkeypatch.setattr(grievances, "assess_grievance", unavailable_assessment)
    created = client.post(
        "/api/v1/grievances",
        headers=citizen,
        json={
            "category": "Street lighting",
            "title": "Streetlight is not working",
            "description": "The streetlight has been out for three nights.",
            "location": "12th Main Road, Bengaluru",
        },
    )
    assert created.status_code == 201
    grievance = created.json()

    listed = client.get("/api/v1/grievances", headers=citizen)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["ai_triage_status"] == "unavailable"
    assert listed.json()["items"][0]["priority"] == "medium"
    assert listed.json()["items"][0]["review_status"] == "pending"

    tracking = client.get(f"/api/v1/tracking/{grievance['reference_number']}")
    assert tracking.status_code == 200
    assert "user_id" not in tracking.json()


def test_ai_triage_is_advisory_until_admin_review(client, citizen, admin_headers, monkeypatch):
    from app.api.v1.endpoints import grievances
    from app.services.grievance_triage import TriageAssessment

    async def fake_assessment(title, description, category):
        assert title == "Streetlight not working"
        assert description.startswith("The streetlight")
        assert category == "Street lighting"
        return TriageAssessment(
            category="Public safety",
            priority="high",
            confidence=0.82,
            rationale="A dark street may create a safety concern.",
        ), "test"

    monkeypatch.setattr(grievances, "assess_grievance", fake_assessment)
    created = client.post(
        "/api/v1/grievances",
        headers=citizen,
        json={
            "category": "Street lighting",
            "title": "Streetlight not working",
            "description": "The streetlight has been out for three nights.",
            "location": "12th Main Road, Bengaluru",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )
    assert created.status_code == 201
    report = created.json()
    assert report["ai_suggested_category"] == "Public safety"
    assert report["ai_suggested_priority"] == "high"
    assert report["category"] == "Street lighting"
    assert report["priority"] == "medium"
    assert report["status"] == "received"
    assert report["review_status"] == "pending"
    assert report["latitude"] == 12.9716

    reviewed = client.patch(
        f"/api/v1/grievances/{report['id']}",
        headers=admin_headers,
        json={"category": "Public safety", "priority": "high", "review_status": "reviewed"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["review_status"] == "reviewed"
    assert reviewed.json()["reviewed_by_id"]
    assert reviewed.json()["priority"] == "high"


def test_grievance_image_evidence_is_private_and_validated(client, citizen, monkeypatch):
    from app.api.v1.endpoints import grievances
    from app.core.errors import APIError

    async def unavailable_assessment(*_args):
        del _args
        raise APIError(503, "ai_provider_unavailable", "AI triage is not configured.")

    monkeypatch.setattr(grievances, "assess_grievance", unavailable_assessment)
    image = b"\x89PNG\r\n\x1a\n" + b"test-image-data"
    submitted = client.post(
        "/api/v1/grievances/submit",
        headers=citizen,
        data={
            "category": "Roads & infrastructure",
            "title": "Pothole on the road",
            "description": "A large pothole is creating a hazard on the road.",
            "location": "12th Main Road, Bengaluru",
            "latitude": "12.9716",
            "longitude": "77.5946",
        },
        files={"file": ("road.png", image, "image/png")},
    )
    assert submitted.status_code == 201
    report = submitted.json()
    assert report["has_evidence"] is True
    assert report["evidence_content_type"] == "image/png"

    evidence = client.get(f"/api/v1/grievances/{report['id']}/evidence", headers=citizen)
    assert evidence.status_code == 200
    assert evidence.content == image

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "other-resident@example.test",
            "full_name": "Other Resident",
            "password": "other-long-password",
        },
    )
    other_token = client.post(
        "/api/v1/auth/login",
        data={"username": "other-resident@example.test", "password": "other-long-password"},
    ).json()["access_token"]
    denied = client.get(
        f"/api/v1/grievances/{report['id']}/evidence",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert denied.status_code == 404

    invalid = client.post(
        "/api/v1/grievances/submit",
        headers=citizen,
        data={
            "category": "Roads & infrastructure",
            "title": "Pothole on the road",
            "description": "A large pothole is creating a hazard on the road.",
            "location": "12th Main Road, Bengaluru",
        },
        files={"file": ("not-image.png", b"not an image", "image/png")},
    )
    assert invalid.status_code == 415
    assert invalid.json()["error"]["code"] == "invalid_media"


def test_admin_routes_require_admin(client, citizen, admin_headers):
    denied = client.get("/api/v1/admin/overview", headers=citizen)
    assert denied.status_code == 403

    allowed = client.get("/api/v1/admin/overview", headers=admin_headers)
    assert allowed.status_code == 200
    assert allowed.json()["total_users"] == 2


def test_invalid_payload_uses_consistent_error_shape(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "full_name": "A", "password": "short"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_service_execution_requires_confirmation_and_is_not_silently_simulated(client, citizen):
    plan = client.post(
        "/api/v1/services/automation/plans",
        headers=citizen,
        json={"service_name": "Birth certificate", "jurisdiction": "Bengaluru"},
    )
    assert plan.status_code == 201
    response = client.post(
        f"/api/v1/services/automation/{plan.json()['task_id']}/execute",
        headers=citizen,
        json={"user_confirmed": True},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_execution_unavailable"


def test_service_assistance_creates_guidance_only_and_keeps_field_values_ephemeral(
    client,
    citizen,
    monkeypatch,
):
    from app.api.v1.endpoints import service_automation
    from app.core.config import settings
    from app.schemas.services import ServiceAssistanceAssessment, ServiceFormField

    monkeypatch.setattr(settings, "government_service_portals", {})

    async def fake_assessment(service_request, jurisdiction):
        assert service_request == "Apply for a birth certificate"
        assert jurisdiction == "Bengaluru"
        return ServiceAssistanceAssessment(
            service_name="Birth certificate",
            procedure=["Check the official portal.", "Review the application requirements."],
            required_documents=["Proof of birth"],
            form_fields=[
                ServiceFormField(
                    field_id="applicant_name",
                    label="Applicant name",
                    required=True,
                )
            ],
            tracking_guidance=["Use the acknowledgement number on the official portal."],
        )

    monkeypatch.setattr(service_automation, "assess_service_request", fake_assessment)
    response = client.post(
        "/api/v1/services/automation/assist",
        headers=citizen,
        json={"service_request": "Apply for a birth certificate", "jurisdiction": "Bengaluru"},
    )
    assert response.status_code == 201
    result = response.json()
    assert result["service_name"] == "Birth certificate"
    assert result["form_fields"][0]["field_id"] == "applicant_name"
    assert "password" in result["privacy_notice"].lower()
    assert "submit" in result["safety_notice"].lower()
    assert result["supported_portals"] == []

    plans = client.get("/api/v1/services/automation/plans", headers=citizen)
    assert plans.status_code == 200
    assert plans.json()["total"] == 1
    assert plans.json()["items"][0]["steps"] == result["procedure"]
    assert "form_fields" not in plans.json()["items"][0]


def test_service_assistance_rejects_credential_collection():
    from pydantic import ValidationError

    from app.schemas.services import (
        ServiceAssistanceAssessment,
        ServiceAssistanceRequest,
        ServiceFormField,
    )

    try:
        ServiceFormField(field_id="portal_password", label="Portal password")
    except ValidationError:
        pass
    else:
        raise AssertionError("Portal credentials must not be included as form fields")
    try:
        ServiceAssistanceRequest(
            service_request="Help me enter my portal password",
            jurisdiction="Bengaluru",
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("Portal credentials must not be included in service requests")
    try:
        ServiceAssistanceAssessment(
            service_name="Certificate application",
            procedure=["Store the citizen's portal password for later."],
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("Credential-containing service plans must not be accepted")


def test_portal_inspection_restricts_configured_origin(monkeypatch):
    from app.core.config import settings
    from app.core.errors import APIError
    from app.services.government_portals import resolve_portal_url

    monkeypatch.setattr(
        settings,
        "government_service_portals",
        {"state_services": "https://services.example.gov/"},
    )
    target, origin = resolve_portal_url("state_services", "/applications")
    assert target == "https://services.example.gov/applications"
    assert origin == ("https", "services.example.gov", 443)
    try:
        resolve_portal_url("state_services", "https://example.com/")
    except APIError as error:
        assert error.code == "invalid_portal_path"
    else:
        raise AssertionError("External portal URLs must be rejected")


def test_portal_configuration_requires_credential_free_https():
    from pydantic import ValidationError

    from app.core.config import Settings

    for portal_url in (
        "http://services.example.gov/",
        "https://user:password@services.example.gov/",
        "https://services.example.gov:8443/",
    ):
        try:
            Settings(government_service_portals={"state_services": portal_url})
        except ValidationError:
            continue
        raise AssertionError(f"Unsafe government portal URL was accepted: {portal_url}")


def test_eligibility_compares_supplied_values_against_scheme_rules(client, citizen, admin_headers):
    created = client.post(
        "/api/v1/schemes",
        headers=admin_headers,
        json={
            "name": "Example youth support",
            "department": "Example department",
            "description": "A test-only scheme for exercising eligibility checks.",
            "benefit": "Training support",
            "eligibility_criteria": [
                {"field": "age", "operator": "lte", "value": 25, "label": "Age 25 or younger"},
                {"field": "state", "operator": "eq", "value": "Karnataka", "label": "Resident of Karnataka"},
            ],
        },
    )
    assert created.status_code == 201

    response = client.post(
        "/api/v1/eligibility/check",
        headers=citizen,
        json={"age": 31, "state": "Karnataka"},
    )
    assert response.status_code == 200
    result = next(item for item in response.json() if item["scheme_name"] == "Example youth support")
    assert result["assessment"] == "does_not_match"


def test_media_analysis_rejects_mismatched_image_content(client, citizen):
    response = client.post(
        "/api/v1/media-analysis/images",
        headers=citizen,
        files={"file": ("not-an-image.png", b"not an image", "image/png")},
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "invalid_media"


def test_claim_without_trusted_evidence_is_inconclusive(client, citizen, monkeypatch):
    from app.api.v1.endpoints import fact_verification

    async def no_sources(_urls):
        del _urls
        return [], ["No configured sources were reachable."]

    async def unexpected_model_call(*_args):
        del _args
        raise AssertionError("Claims without fetched trusted evidence must not be sent for verdicts.")

    monkeypatch.setattr(fact_verification, "fetch_trusted_sources", no_sources)
    monkeypatch.setattr(fact_verification, "analyze_claim", unexpected_model_call)
    response = client.post(
        "/api/v1/verification/claims",
        headers=citizen,
        json={"claim": "A claim with no evidence"},
    )
    assert response.status_code == 201
    result = response.json()
    assert result["assessment"] == "inconclusive"
    assert result["confidence"] is None
    assert result["evidence"] == []
    assert result["sources"] == []
    assert result["limitations"]

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "other-verifier@example.test",
            "full_name": "Other Verifier",
            "password": "other-test-password",
        },
    )
    other_token = client.post(
        "/api/v1/auth/login",
        data={"username": "other-verifier@example.test", "password": "other-test-password"},
    ).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}
    assert client.get("/api/v1/verification", headers=other_headers).json() == []
    assert client.get(
        f"/api/v1/verification/{result['id']}",
        headers=other_headers,
    ).status_code == 404


def test_claim_uses_only_fetched_trusted_evidence_and_discards_model_citations(
    client,
    citizen,
    monkeypatch,
):
    from app.api.v1.endpoints import fact_verification
    from app.core.config import settings
    from app.schemas.verification import AIAnalysis
    from app.services.verification_evidence import FetchedSource

    monkeypatch.setattr(settings, "trusted_fact_source_domains", ["example.gov"])

    async def fetched(urls):
        assert urls == [("https://news.example.gov/fact-check", "news.example.gov")]
        return [
            FetchedSource(
                url="https://news.example.gov/fact-check",
                publisher="news.example.gov",
                text="The city announced the service on Monday. It begins next week.",
            )
        ], []

    async def model(system_prompt, user_prompt):
        assert "news.example.gov" in user_prompt
        assert "invent" in system_prompt
        return AIAnalysis(
            assessment="supported",
            confidence=0.73,
            analysis="The supplied excerpt is consistent with the claim.",
            sources=["https://fabricated.example/article"],
        ), "test-provider"

    monkeypatch.setattr(fact_verification, "fetch_trusted_sources", fetched)
    monkeypatch.setattr(fact_verification, "analyze_claim", model)
    response = client.post(
        "/api/v1/verification/claims",
        headers=citizen,
        json={
            "claim": "The city announced the service",
            "source_urls": ["https://news.example.gov/fact-check"],
        },
    )
    assert response.status_code == 201
    report = response.json()
    assert report["assessment"] == "supported"
    assert report["sources"] == ["https://news.example.gov/fact-check"]
    assert report["evidence"][0]["kind"] == "trusted_source_excerpt"
    assert report["evidence"][0]["source_url"] == "https://news.example.gov/fact-check"
    assert "fabricated.example" not in str(report["sources"])

    history = client.get("/api/v1/verification", headers=citizen)
    assert history.status_code == 200
    assert history.json()[0]["limitations"] == report["limitations"]


def test_claim_rejects_unconfigured_source_domains(client, citizen, monkeypatch):
    from app.api.v1.endpoints import fact_verification
    from app.core.config import settings

    monkeypatch.setattr(settings, "trusted_fact_source_domains", ["example.gov"])

    async def unexpected_fetch(_urls):
        del _urls
        raise AssertionError("Untrusted source URLs must be rejected before fetching.")

    monkeypatch.setattr(fact_verification, "fetch_trusted_sources", unexpected_fetch)
    response = client.post(
        "/api/v1/verification/claims",
        headers=citizen,
        json={
            "claim": "A sufficiently long claim",
            "source_urls": ["https://example.com/article"],
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "untrusted_source"


def test_visual_indicators_are_not_reported_as_proof_of_falsity(client, citizen, monkeypatch):
    from app.api.v1.endpoints import media_analysis
    from app.schemas.verification import AIAnalysis

    async def indicators(_content, _content_type, _context):
        del _content, _content_type, _context
        return AIAnalysis(
            assessment="possible_manipulation_indicators",
            confidence=0.99,
            analysis="A visual artifact may warrant closer review.",
            observations=["An inconsistent shadow is visible."],
        ), "test-provider"

    monkeypatch.setattr(media_analysis, "analyze_image_bytes", indicators)
    response = client.post(
        "/api/v1/media-analysis/images",
        headers=citizen,
        files={
            "file": (
                "sample.png",
                b"\x89PNG\r\n\x1a\nexample",
                "image/png",
            )
        },
    )
    assert response.status_code == 201
    report = response.json()
    assert report["assessment"] == "possible_manipulation_indicators"
    assert "fake" in report["disclaimer"].lower()
    assert "not evidence" in report["limitations"][1].lower()
    assert report["evidence"][0]["kind"] == "visual_observation"


def test_audio_claims_remain_inconclusive_without_external_evidence(client, citizen, monkeypatch):
    import io
    import wave

    from app.api.v1.endpoints import media_analysis
    from app.schemas.verification import AIAnalysis

    async def transcribe(_content, _filename, _content_type):
        del _content, _filename, _content_type
        return "A machine-generated transcript with a spoken claim.", "transcriber"

    async def analyze(transcript, context):
        assert transcript.startswith("A machine-generated transcript")
        assert context == "Unverified context"
        return AIAnalysis(
            assessment="supported",
            confidence=0.99,
            analysis="The transcript contains a claim, but no sources were checked.",
        ), "analyzer"

    monkeypatch.setattr(media_analysis, "transcribe_audio", transcribe)
    monkeypatch.setattr(media_analysis, "analyze_transcript", analyze)
    wav_data = io.BytesIO()
    with wave.open(wav_data, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b"\x00\x00" * 8000)

    response = client.post(
        "/api/v1/media-analysis/audio",
        headers=citizen,
        data={"context": "Unverified context"},
        files={"file": ("sample.wav", wav_data.getvalue(), "audio/wav")},
    )
    assert response.status_code == 201
    report = response.json()
    assert report["assessment"] == "inconclusive"
    assert report["confidence"] is None
    assert report["transcript"].startswith("A machine-generated transcript")
    assert report["evidence"][0]["kind"] == "transcript_excerpt"
    assert "No trusted external sources" in report["limitations"][-1]


def test_video_report_uses_actual_sample_timestamps_and_no_provider_sources(
    client,
    citizen,
    monkeypatch,
):
    from app.api.v1.endpoints import media_analysis
    from app.schemas.verification import AIAnalysis, FrameObservation

    def frames(_content, _extension):
        del _content, _extension
        return [(2.5, b"frame-one"), (8.0, b"frame-two")]

    async def analyze(samples, context):
        assert len(samples) == 2
        assert context == ""
        return AIAnalysis(
            assessment="possible_manipulation_indicators",
            confidence=0.91,
            analysis="A frame detail may warrant human review.",
            sources=["https://invented.example/source"],
            frame_observations=[
                FrameObservation(frame_index=1, description="A visual discontinuity is present.")
            ],
        ), "test-provider"

    monkeypatch.setattr(media_analysis, "extract_video_frames", frames)
    monkeypatch.setattr(media_analysis, "analyze_video_frames", analyze)
    response = client.post(
        "/api/v1/media-analysis/videos",
        headers=citizen,
        files={
            "file": (
                "sample.mp4",
                b"\x00\x00\x00\x18ftypisomexample-video",
                "video/mp4",
            )
        },
    )
    assert response.status_code == 201
    report = response.json()
    assert report["assessment"] == "possible_manipulation_indicators"
    assert report["sources"] == []
    assert report["evidence"][0]["timestamp_seconds"] == 8.0
    assert "audio tracks are not analyzed" in report["limitations"][-1].lower()


def test_audio_duration_is_bounded():
    import io
    import wave

    from app.core.errors import APIError
    from app.services.verification_media import validate_audio_duration

    def wav_with_duration(seconds):
        output = io.BytesIO()
        with wave.open(output, "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(1)
            audio.writeframes(b"\x00\x00" * seconds)
        return output.getvalue()

    validate_audio_duration(wav_with_duration(600))
    try:
        validate_audio_duration(wav_with_duration(601))
    except APIError as error:
        assert error.code == "audio_too_long"
    else:
        raise AssertionError("Audio longer than ten minutes must be rejected.")


def test_video_frame_sampling_is_capped(tmp_path):
    import cv2
    import numpy as np

    from app.services.verification_media import extract_video_frames

    video_path = tmp_path / "sample.avi"
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        2.0,
        (32, 32),
    )
    assert writer.isOpened()
    try:
        for index in range(12):
            writer.write(np.full((32, 32, 3), index, dtype=np.uint8))
    finally:
        writer.release()

    frames = extract_video_frames(video_path.read_bytes(), ".avi")
    assert len(frames) == 6
    assert frames[0][0] == 0
    assert frames[-1][0] == 5.5


def test_trusted_source_urls_reject_queries_and_credentials():
    from app.core.errors import APIError
    from app.services.verification_evidence import validate_source_urls

    for url in (
        "https://user:password@trusted.example/article",
        "https://trusted.example/article?token=secret",
    ):
        try:
            validate_source_urls([url])
        except APIError as error:
            assert error.code == "invalid_source_url"
        else:
            raise AssertionError("Source URLs with credentials or query strings must be rejected.")
