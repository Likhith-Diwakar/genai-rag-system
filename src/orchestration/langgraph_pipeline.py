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

# FIX: singleton retriever (unchanged from original)
_retriever = None
def get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever


# FIX: compile the graph once at module level instead of rebuilding it
# on every call to run_pipeline(). build_graph() compiles the StateGraph
# which involves node registration and edge validation — doing this per
# query wastes ~50-100ms and creates unnecessary objects.
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


def log_state_summary(state: RAGState):
    print("\nSTATE SUMMARY:")
    print("Query:", state.get("query"))
    print("Docs:", len(state.get("retrieved_docs", [])))
    print("Retrieval Score:", state.get("retrieval_score"))
    print("Grounding:", state.get("grounding_score"))
    print("Confidence:", state.get("confidence"))


def _is_meaningful_query(query: str) -> bool:
    return bool(query and query.strip())


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
    original_query = state.get("query", "")
    retry = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    # First pass — use query as-is, no rewrite needed, don't log to path
    if retry == 0 and not state.get("retrieved_docs"):
        state["rewritten_query"] = original_query
        return state

    # Skip rewrite if we already have good docs (retry loop but docs exist)
    if state.get("retrieved_docs"):
        return state

    # Max retries reached — fall back to original query, don't log to path
    if retry >= max_retries:
        state["rewritten_query"] = original_query
        return state

    # Actual rewrite on retry passes — track it in the path
    track(state, "rewrite")

    try:
        rewritten = rewriter.rewrite(original_query, [])
    except Exception:
        rewritten = original_query

    state["rewritten_query"] = (rewritten or original_query).strip()
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
        docs, metas, scores = get_retriever().retrieve(query, k, rewrite_before_retrieve=False)
    except Exception:
        docs, metas, scores = [], [], []

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
    threshold = max(0.1, 0.5 * max_score)

    f_docs, f_metas, f_scores = [], [], []

    for d, m, s in zip(docs, metas, scores):
        if isinstance(s, (int, float)) and s >= threshold:
            f_docs.append(d)
            f_metas.append(m)
            f_scores.append(s)

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

    top_score = max(scores)
    avg_score = sum(scores) / len(scores)

    if top_score > 0.75 and avg_score > 0.5:
        state["retrieval_status"] = "good"
    elif top_score > 0.5:
        state["retrieval_status"] = "weak"
    else:
        state["retrieval_status"] = "fail"

    return state


def generate_node(state: RAGState) -> RAGState:
    track(state, "generate")

    docs = state.get("retrieved_docs") or []

    if not docs:
        state["answer"] = ""
        return state

    try:

        answer, _ = generate_answer(
            query=state.get("query", ""),
            documents=docs,
            metadatas=state.get("retrieved_metas"),
            scores=state.get("retrieved_scores")
        )
    except Exception:
        answer = ""

    state["answer"] = answer or ""
    return state


def validate_answer_node(state: RAGState) -> RAGState:
    track(state, "validate")

    answer = state.get("answer", "")
    docs = state.get("retrieved_docs") or []

    if not answer or not docs:
        state["answer_status"] = "retry"
        return state

    answer_tokens = set(answer.lower().split())
    hits = 0

    for doc in docs:
        overlap = len(answer_tokens.intersection(set(doc.lower().split())))
        if overlap > max(5, int(0.1 * len(answer_tokens))):
            hits += 1

    grounding = hits / len(docs)
    state["grounding_score"] = grounding

    state["answer_status"] = "good" if grounding > 0.3 else "retry"
    return state


def compute_confidence_node(state: RAGState) -> RAGState:
    track(state, "confidence")

    retrieval_conf = state.get("retrieval_score", 0.0)
    grounding = state.get("grounding_score", 0.0)

    state["confidence"] = (0.6 * retrieval_conf) + (0.4 * grounding)
    return state


def decision_node(state: RAGState) -> RAGState:
    track(state, "decision")

    retry = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if state.get("query_type") == "invalid":
        state["next_step"] = "generate"

    elif not state.get("retrieved_docs") and retry == 0:
        # First pass — skip rewrite, go straight to retrieve
        state["next_step"] = "retrieve"

    elif not state.get("retrieved_docs") and retry < max_retries:
        # Retry pass — retrieval previously failed, now rewrite
        state["retry_count"] += 1
        state["next_step"] = "rewrite"

    elif state.get("retrieval_status") in ["fail", "weak"] and retry < max_retries:
        state["retry_count"] += 1
        state["next_step"] = "rewrite"

    elif state.get("retrieved_docs") and not state.get("answer"):
        state["next_step"] = "generate"

    elif state.get("answer_status") == "retry" and retry < max_retries:
        state["retry_count"] += 1
        state["next_step"] = "rewrite"

    else:
        state["next_step"] = "end"

    print("NEXT STEP:", state.get("next_step"))
    log_state_summary(state)

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
    graph.add_node("confidence", compute_confidence_node)
    graph.add_node("decision", decision_node)

    graph.set_entry_point("detect")

    graph.add_edge("detect", "decision")

    graph.add_conditional_edges("decision", router, {
        "retrieve": "adjust_k",   # first pass — skip rewrite, go straight to adjust_k
        "rewrite": "rewrite",     # retry pass — rewrite then adjust_k
        "generate": "generate",
        "end": END
    })

    graph.add_edge("rewrite", "adjust_k")
    graph.add_edge("adjust_k", "retrieve")
    graph.add_edge("retrieve", "filter")
    graph.add_edge("filter", "check")
    graph.add_edge("check", "decision")

    graph.add_edge("generate", "validate")
    graph.add_edge("validate", "confidence")
    graph.add_edge("confidence", "decision")

    return graph.compile()


def run_pipeline(query: str) -> str:
    if not query or not query.strip():
        return "No query provided."

    metrics.reset()  # ✅ ADD THIS HERE
    # FIX: use singleton compiled graph instead of rebuilding on every call
    app = get_app()

    result = app.invoke({
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
    })

    print("\nGRAPH PATH:", " -> ".join(result.get("execution_path", [])))

    metrics.log(logger)  # ✅ ADD THIS
    return result.get("answer") or "No response generated."