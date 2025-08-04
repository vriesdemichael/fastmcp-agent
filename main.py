from __future__ import annotations

from typing import Any, Dict, List

from fastapi import FastAPI
from openai.types import chat
from pydantic import BaseModel, ConfigDict

from agent import Agent
from settings import Settings

settings = Settings()
app = FastAPI()
agent = Agent(settings)


class ChatCompletionRequest(BaseModel):
    """Subset of OpenAI chat completion params used by this API.

    OpenAI's ``CompletionCreateParams`` is a ``TypedDict`` union which FastAPI
    cannot parse directly, so this lightweight model accepts any additional
    fields for forward compatibility.
    """

    model: str | None = None
    messages: List[chat.ChatCompletionMessageParam]

    model_config = ConfigDict(extra="allow")


@app.post("/v1/chat/completions")
async def create_chat_completion(
    request: ChatCompletionRequest,
) -> Dict[str, Any]:
    response = await agent.run(request.messages, model=request.model)
    return response.model_dump()


@app.get("/v1/models")
async def list_models() -> Dict[str, Any]:
    return {
        "data": [{"id": settings.openai_model, "object": "model"}],
        "object": "list",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
