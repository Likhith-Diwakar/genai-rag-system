from src.providers.llm.groq_llm import GroqLLM
from src.utils.logger import logger

llm = GroqLLM()


MODEL_REGISTRY = {
    "groq": {
        "description": "Fast reasoning model suitable for general question answering and RAG style responses"
    },
    "gpt4o": {
        "description": "Very strong at summarization, structured output, and generating concise bullet point responses"
    },
    "claude": {
        "description": "Excellent at long explanations, detailed reasoning, document understanding, and deep analysis"
    },
    "gemini": {
        "description": "Best for multimodal understanding including charts, graphs, images, scanned documents and visual data"
    }
}


# Router cache (performance optimization)
_router_cache = {}


def route_llm(query: str) -> str:
    """
    Dynamically selects the best model using Groq LLM reasoning.
    """

    cache_key = query.strip().lower()

    if cache_key in _router_cache:
        model = _router_cache[cache_key]
        logger.info(f"Router cache hit | model={model}")
        return model

    model_info = "\n".join(
        f"{name}: {data['description']}"
        for name, data in MODEL_REGISTRY.items()
    )

    prompt = f"""
You are an AI model router.

Your job is to select the most suitable model to answer a user query.

Available models and their capabilities:

{model_info}

User Query:
{query}

Return ONLY one model name from the available list.
"""

    try:
        selected_model = llm.generate(
            system_message="You are an intelligent LLM routing system.",
            user_message=prompt
        ).strip().lower()

    except Exception as e:
        logger.error(f"Router LLM failure: {e}")
        selected_model = ""

    if selected_model not in MODEL_REGISTRY:
        logger.warning(
            f"Router returned unknown model '{selected_model}', defaulting to groq"
        )
        selected_model = "groq"

    _router_cache[cache_key] = selected_model

    logger.info(f"[LLM Router] Selected model: {selected_model}")

    return selected_model