# ai-engine/app/api/routes/chat.py
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse
from app.api.deps import verify_internal_token
from app.database import get_db, engine
from app.rag.pipeline import RAGPipeline
from app.rag.retriever import build_rag_prompt
from app.memory.conversation import get_conversation_history
from app.models.llm import get_llm
from sqlalchemy import text
import json
import datetime
import uuid

router = APIRouter(prefix="/chat", dependencies=[Depends(verify_internal_token)])
rag_pipeline = RAGPipeline()


@router.post("/stream")
async def chat_stream(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    conversation_id = body["conversation_id"]
    user_message = body["message"]
    knowledge_base_id = body["knowledge_base_id"]
    model_config = body.get("model_config", {})
    system_prompt = body.get("system_prompt")
    retrieval_config = body.get("retrieval_config", {})

    # 1. 先取对话历史（此时当前消息尚未入库，避免在 Prompt 中重复出现）
    history = get_conversation_history(conversation_id)

    # 2. 保存用户消息
    save_message(conversation_id, "user", user_message)

    # 3. RAG 检索
    results = rag_pipeline.retrieve(user_message, knowledge_base_id, retrieval_config)
    context = "\n\n".join(r["content"] for r in results)
    citations = [
        {
            "chunk_id": r["chunk_id"],
            "document_name": r["document_name"],
            "content_snippet": r["content"][:200],
            "similarity": r["similarity"],
        }
        for r in results
    ]

    # 4. 组装 Prompt
    messages = build_rag_prompt(system_prompt, context, history, user_message)

    # 5. 流式生成
    llm = get_llm(
        model=model_config.get("model"),
        temperature=model_config.get("temperature"),
    )

    async def event_generator():
        full_response = ""
        total_tokens = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

        # 先发送引用来源
        yield {"event": "citations", "data": json.dumps(citations)}

        async for chunk in llm.astream(messages):
            if chunk.content:
                full_response += chunk.content
                yield {
                    "event": "token",
                    "data": json.dumps({"token": chunk.content}),
                }
            # 最后一个 chunk 携带 usage 信息（需在 LLM 中开启 stream_usage）
            if chunk.usage_metadata:
                total_tokens = {
                    "prompt_tokens": chunk.usage_metadata.get("input_tokens", 0),
                    "completion_tokens": chunk.usage_metadata.get(
                        "output_tokens", 0
                    ),
                    "total_tokens": chunk.usage_metadata.get("total_tokens", 0),
                }

        # 保存助手回复
        save_message(
            conversation_id,
            "assistant",
            full_response,
            citations=citations,
            token_usage=total_tokens,
        )

        yield {
            "event": "done",
            "data": json.dumps({"full_content": full_response}),
        }

    return EventSourceResponse(event_generator())


def save_message(
    conversation_id: str,
    role: str,
    content: str,
    citations: list = None,
    token_usage: dict = None,
):
    with engine.begin() as conn:
        conn.execute(
            text(
                """
            INSERT INTO messages (id, conversation_id, role, content,
                                  citations, token_usage, created_at)
            VALUES (:id, :conv_id, :role, :content, :citations::jsonb,
                    :token_usage::jsonb, :created_at)
        """
            ),
            {
                "id": str(uuid.uuid4()),
                "conv_id": conversation_id,
                "role": role,
                "content": content,
                "citations": json.dumps(citations) if citations else None,
                "token_usage": json.dumps(token_usage) if token_usage else None,
                "created_at": datetime.datetime.now(),
            },
        )
