# ai-engine/app/rag/fusion.py
def rrf_fusion(result_lists: list[list[dict]], k: int = 60) -> list[dict]:
    """Reciprocal Rank Fusion：融合多路按相关性降序的召回结果

    score(d) = Σ 1 / (k + rank_i(d))，仅依赖各路排名而非原始分数，
    因此不要求各路分数量纲一致（向量相似度与 ts_rank 可直接融合）。
    k 为平滑常数，取值越大，不同路之间的排名差异影响越小，常用 60。
    """
    fused: dict[str, dict] = {}
    scores: dict[str, float] = {}

    for results in result_lists:
        for rank, item in enumerate(results, start=1):
            chunk_id = item["chunk_id"]
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
            # 重复分块保留最先出现那路的原始信息（含 similarity）
            if chunk_id not in fused:
                fused[chunk_id] = item

    return sorted(fused.values(), key=lambda r: scores[r["chunk_id"]], reverse=True)


def weighted_fusion(
    result_lists: list[list[dict]], weights: list[float]
) -> list[dict]:
    """加权分数融合：各路分数先做 min-max 归一化，再加权求和

    归一化消除各路量纲差异（向量余弦相似度与 ts_rank）。
    某路只有一条候选时归一化分取 1.0；空路直接跳过。
    """
    fused: dict[str, dict] = {}
    scores: dict[str, float] = {}

    for results, weight in zip(result_lists, weights):
        if not results:
            continue
        raw = [r["similarity"] for r in results]
        lo, hi = min(raw), max(raw)
        for item in results:
            norm = 1.0 if hi == lo else (item["similarity"] - lo) / (hi - lo)
            chunk_id = item["chunk_id"]
            scores[chunk_id] = scores.get(chunk_id, 0.0) + weight * norm
            # 重复分块保留最先出现那路的原始信息（含 similarity）
            if chunk_id not in fused:
                fused[chunk_id] = item

    return sorted(fused.values(), key=lambda r: scores[r["chunk_id"]], reverse=True)
