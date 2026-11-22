from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation: list[ChatMessage] = Field(default_factory=list, max_length=20)
    language: str = Field(default="en", min_length=2, max_length=20)


class ChatResponse(BaseModel):
    reply: str
    provider: str
    disclaimer: str
