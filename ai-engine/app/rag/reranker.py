# ai-engine/app/rag/reranker.py
import json
import urllib.request
from app.config import settings

RERANK_URL = (
    "https://dashscope.aliyuncs.com/api/v1/services/rerank/"
    "text-rerank/text-rerank/v1"
)


def rerank(query: str, results: list[dict], top_n: int) -> list[dict]:
    """调用 DashScope text-rerank（gte-rerank 系列）对召回结果重排

    重排后 similarity 字段替换为相关性分数（0~1），引用来源按此展示。
    候选少于 2 条、未配置 API Key 或服务调用失败时，降级返回原顺序。
    """
    if len(results) < 2 or not settings.openai_api_key:
        return results[:top_n]

    payload = {
        "model": settings.rerank_model,
        "input": {
            "query": query,
            "documents": [r["content"] for r in results],
        },
        "parameters": {"top_n": top_n, "return_documents": False},
    }
    req = urllib.request.Request(
        RERANK_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
        # results 已按相关性降序返回，index 指向原候选列表
        return [
            {**results[item["index"]], "similarity": item["relevance_score"]}
            for item in body["output"]["results"]
        ]
    except Exception as e:
        print(f"rerank failed, fallback to original order: {e}")
        return results[:top_n]
