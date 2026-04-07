from typing import TypedDict, List, Any
from langgraph.graph import StateGraph, END
from src.utils.metrics import metrics
from src.utils.logger import logger
from src.providers.retrievers.hybrid_retriever import HybridRetriever
from src.utils.query_rewriter import QueryRewriter
from src.llm.rag import generate_answer


class RAGState(TypedDict):
    query: str
    query_type: str
    rewritten_query: str
    retrieved_docs: List[Any]
    retrieved_metas: List[Any]
    retrieved_scores: List[Any]
    retrieval_score: float
    answer: str
    retry_count: int
    max_retries: int
    retrieval_status: str
    top_k: int
    answer_status: str
    execution_path: List[str]
    confidence: float
    grounding_score: float
    next_step: str


rewriter = QueryRewriter()

_retriever = None
def get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever


_app = None
def get_app():
    global _app
    if _app is None:
        _app = build_graph()
    return _app


def track(state: RAGState, node_name: str):
    path = state.get("execution_path", [])
    path.append(node_name)
    state["execution_path"] = path


def _is_meaningful_query(query: str) -> bool:
    return bool(query and query.strip())


# ------------------ NODES ------------------

def detect_query_type(state: RAGState) -> RAGState:
    track(state, "detect")

    query = (state.get("query") or "").strip()
    state["query"] = query

    if not _is_meaningful_query(query):
        state["query_type"] = "invalid"
    elif any(c.isdigit() for c in query):
        state["query_type"] = "structured"
    elif len(query.split()) <= 6:
        state["query_type"] = "factual"
    else:
        state["query_type"] = "exploratory"

    return state


def rewrite_node(state: RAGState) -> RAGState:
    track(state, "rewrite")

    original_query = state.get("query", "")
    retry = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    # On first pass (retry=0), just use the original query directly.
    # Only attempt LLM rewriting on subsequent retries, and only if
    # we already have some context docs to guide the rewrite.
    if retry == 0:
        state["rewritten_query"] = original_query
        return state

    if retry >= max_retries:
        state["rewritten_query"] = original_query
        return state

    # Use any previously retrieved docs as context for rewriting
    existing_docs = state.get("retrieved_docs") or []

    try:
        rewritten = rewriter.rewrite(original_query, existing_docs)
        state["rewritten_query"] = (rewritten or original_query).strip()
    except Exception:
        state["rewritten_query"] = original_query

    logger.info(
        f"Query rewrite | retry={retry} | "
        f"original='{original_query}' | rewritten='{state['rewritten_query']}'"
    )

    return state


def adjust_k_node(state: RAGState) -> RAGState:
    track(state, "adjust_k")

    qtype = state.get("query_type", "exploratory")

    if qtype == "structured":
        state["top_k"] = 3
    elif qtype == "factual":
        state["top_k"] = 5
    else:
        state["top_k"] = min(12, 5 + state.get("retry_count", 0) * 2)

    return state


def retrieve_node(state: RAGState) -> RAGState:
    track(state, "retrieve")

    query = state.get("rewritten_query") or state.get("query")
    k = state.get("top_k", 5)

    try:
        docs, metas, scores = get_retriever().retrieve(
            query, k, rewrite_before_retrieve=False
        )
    except Exception as e:
        print(f"❌ RETRIEVAL EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        docs, metas, scores = [], [], []

    print(f"🔍 RETRIEVED DOCS: {len(docs)} for query: '{query}'")

    state["retrieved_docs"] = docs or []
    state["retrieved_metas"] = metas or []
    state["retrieved_scores"] = scores or []
    state["retrieval_score"] = max(scores) if scores else 0.0

    return state


def filter_retrieval_node(state: RAGState) -> RAGState:
    track(state, "filter")

    docs = state.get("retrieved_docs") or []
    metas = state.get("retrieved_metas") or []
    scores = state.get("retrieved_scores") or []

    if not scores:
        return state

    max_score = max(scores)
    # FIX: lowered threshold — after normalization scores are 0–1,
    # using 0.5 * max_score was too aggressive and filtered everything out
    threshold = max(0.05, 0.3 * max_score)

    f_docs, f_metas, f_scores = [], [], []

    for d, m, s in zip(docs, metas, scores):
        if isinstance(s, (int, float)) and s >= threshold:
            f_docs.append(d)
            f_metas.append(m)
            f_scores.append(s)

    # Always keep at least top 2 even if below threshold
    if not f_docs and docs:
        f_docs, f_metas, f_scores = docs[:2], metas[:2], scores[:2]

    state["retrieved_docs"] = f_docs
    state["retrieved_metas"] = f_metas
    state["retrieved_scores"] = f_scores
    state["retrieval_score"] = max(f_scores) if f_scores else 0.0

    return state


def check_retrieval_node(state: RAGState) -> RAGState:
    track(state, "check")

    docs = state.get("retrieved_docs") or []
    scores = state.get("retrieved_scores") or []

    if not docs or not scores:
        state["retrieval_status"] = "fail"
        return state

    # FIX: After RRF + normalization, scores are in 0–1 range but
    # rarely exceed 0.75. Loosened thresholds so we reach "generate".
    top_score = max(scores)

    if top_score > 0.3:
        state["retrieval_status"] = "good"
    elif top_score > 0.1:
        state["retrieval_status"] = "weak"
    else:
        state["retrieval_status"] = "fail"

    return state


def generate_node(state: RAGState) -> RAGState:
    track(state, "generate")

    docs = state.get("retrieved_docs") or []

    try:
        if docs:
            answer, _ = generate_answer(
                query=state.get("query", ""),
                documents=docs,
                metadatas=state.get("retrieved_metas"),
                scores=state.get("retrieved_scores"),
            )
        else:
            answer, _ = generate_answer(
                query=state.get("query", ""),
                documents=[],
                metadatas=[],
                scores=[]
            )

    except Exception as e:
        print(f"❌ GENERATION ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        answer = "⚠️ Failed to generate answer."

    state["answer"] = answer or "No answer generated."
    return state


def validate_answer_node(state: RAGState) -> RAGState:
    track(state, "validate")

    answer = state.get("answer", "")
    docs = state.get("retrieved_docs") or []

    if not answer:
        state["answer_status"] = "retry"
        return state

    if not docs:
        state["answer_status"] = "good"
        return state

    answer_tokens = set(answer.lower().split())
    hits = 0

    for doc in docs:
        overlap = len(answer_tokens.intersection(set(doc.lower().split())))
        if overlap > max(5, int(0.1 * len(answer_tokens))):
            hits += 1

    grounding = hits / len(docs)
    state["grounding_score"] = grounding

    # FIX: lowered grounding threshold — 0.3 was too strict,
    # causing valid answers to be retried and eventually dropped
    state["answer_status"] = "good" if grounding > 0.1 else "retry"

    return state


def compute_confidence_node(state: RAGState) -> RAGState:
    track(state, "compute_confidence")

    retrieval_conf = state.get("retrieval_score", 0.0)
    grounding = state.get("grounding_score", 0.0)

    state["confidence"] = (0.6 * retrieval_conf) + (0.4 * grounding)
    return state


def decision_node(state: RAGState) -> RAGState:
    track(state, "decision")

    retry = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    # Safety valve against infinite loops
    if len(state.get("execution_path", [])) > 20:
        state["next_step"] = "end"
        return state

    # If query is invalid, end immediately
    if state.get("query_type") == "invalid":
        state["next_step"] = "end"
        return state

    # Haven't retrieved yet — go retrieve
    if not state.get("rewritten_query") and not state.get("retrieved_docs"):
        state["next_step"] = "retrieve"
        return state

    # Have docs but no answer yet — go generate
    if state.get("retrieved_docs") and not state.get("answer"):
        state["next_step"] = "generate"
        return state

    # Have a good answer — done
    if state.get("answer") and state.get("answer_status") == "good":
        state["next_step"] = "end"
        return state

    # Retrieval failed and we have retries left — rewrite and retry
    if state.get("retrieval_status") == "fail" and retry < max_retries:
        state["retry_count"] = retry + 1
        state["next_step"] = "rewrite"
        return state

    # Answer needs retry and we have retries left
    if state.get("answer_status") == "retry" and retry < max_retries:
        state["retry_count"] = retry + 1
        state["next_step"] = "rewrite"
        return state

    # Exhausted retries or weak retrieval with an answer — just end
    state["next_step"] = "end"
    return state


def router(state: RAGState) -> str:
    return state.get("next_step", "end")


def build_graph():
    graph = StateGraph(RAGState)

    graph.add_node("detect", detect_query_type)
    graph.add_node("rewrite", rewrite_node)
    graph.add_node("adjust_k", adjust_k_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("filter", filter_retrieval_node)
    graph.add_node("check", check_retrieval_node)
    graph.add_node("generate", generate_node)
    graph.add_node("validate", validate_answer_node)
    graph.add_node("compute_confidence", compute_confidence_node)
    graph.add_node("decision", decision_node)

    graph.set_entry_point("detect")

    graph.add_edge("detect", "rewrite")  # FIX: always rewrite first, then decide

    graph.add_edge("rewrite", "adjust_k")
    graph.add_edge("adjust_k", "retrieve")
    graph.add_edge("retrieve", "filter")
    graph.add_edge("filter", "check")
    graph.add_edge("check", "decision")

    graph.add_conditional_edges("decision", router, {
        "retrieve": "adjust_k",
        "rewrite": "rewrite",
        "generate": "generate",
        "end": END
    })

    graph.add_edge("generate", "validate")
    graph.add_edge("validate", "compute_confidence")
    graph.add_edge("compute_confidence", "decision")

    return graph.compile()


def run_pipeline(query: str) -> dict:
    if not query or not query.strip():
        return {"answer": "No query provided."}

    metrics.reset()
    app = get_app()

    result = app.invoke(
        {
            "query": query.strip(),
            "query_type": "",
            "rewritten_query": "",
            "retrieved_docs": [],
            "retrieved_metas": [],
            "retrieved_scores": [],
            "retrieval_score": 0.0,
            "answer": "",
            "retry_count": 0,
            "max_retries": 2,
            "retrieval_status": "",
            "top_k": 5,
            "answer_status": "",
            "execution_path": [],
            "confidence": 0.0,
            "grounding_score": 0.0,
            "next_step": ""
        },
        config={"recursion_limit": 50}
    )

    print(f"✅ Execution path: {result.get('execution_path', [])}")

    return {
        "answer": result.get("answer") or "⚠️ No answer generated",
        "execution_path": result.get("execution_path", []),
        "confidence": float(result.get("confidence", 0.0)),
        "grounding_score": float(result.get("grounding_score", 0.0)),
        "retrieval_score": float(result.get("retrieval_score", 0.0)),
        "sources": result.get("retrieved_metas", [])
    }