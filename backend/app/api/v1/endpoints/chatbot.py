from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ai_provider import generate_text

router = APIRouter(prefix="/chat", tags=["AI chatbot"])


@router.post("/messages", response_model=ChatResponse, dependencies=[Depends(get_current_user)])
async def chat(payload: ChatRequest) -> ChatResponse:
    system_prompt = (
        "You are CIVICPULSE AI, a helpful guide to public services. "
        "Use plain language and respond in the requested language. Do not invent official requirements, "
        "guarantee eligibility, or claim to submit forms. Encourage users to confirm critical details with "
        "the responsible department. Do not ask for passwords, full identity numbers, or payment card data."
    )
    context = "\n".join(f"{message.role}: {message.content}" for message in payload.conversation)
    prompt = f"Preferred language: {payload.language}\nRecent conversation:\n{context}\nCitizen: {payload.message}"
    reply, provider = await generate_text(system_prompt, prompt)
    return ChatResponse(
        reply=reply,
        provider=provider,
        disclaimer="AI-generated guidance can be inaccurate. Confirm important details with the official department.",
    )
