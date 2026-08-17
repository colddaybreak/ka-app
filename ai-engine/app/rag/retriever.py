# ai-engine/app/rag/retriever.py
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage


def build_rag_prompt(
    system_prompt: str, context: str, history: list[dict], user_message: str
) -> list:
    """组装 RAG Prompt"""
    messages = []

    # 系统提示词（含 RAG 上下文）
    system_content = (
        system_prompt
        or "你是一个知识库助手，根据提供的参考资料回答用户问题。如果参考资料中没有相关信息，请如实告知。"
    )
    if context:
        system_content += f"\n\n参考资料：\n{context}"
    messages.append(SystemMessage(content=system_content))

    # 对话历史
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    # 当前用户消息
    messages.append(HumanMessage(content=user_message))

    return messages
