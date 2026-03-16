from src.providers.llm.openrouter_llm import OpenRouterLLM
from src.utils.logger import logger


class QueryRewriter:

    def __init__(self):

        try:
            self.llm = OpenRouterLLM("openai/gpt-4o-mini")
        except Exception:
            logger.exception("Failed to initialize OpenRouterLLM")
            self.llm = None

    def rewrite(self, query, contexts):

        if not self.llm or not contexts:
            return query

        try:

            context_snippets = []

            for c in contexts:

                if isinstance(c, dict):
                    text = c.get("text") or c.get("document") or ""
                else:
                    text = str(c)

                if text:
                    context_snippets.append(text[:300])

            if not context_snippets:
                return query

            context_text = "\n".join(context_snippets)

            system_message = (
                "You are a search query optimizer for a document retrieval system. "
                "Rewrite the user query to improve document retrieval while preserving the original intent. "
                "Use the provided context only to understand the topic of the documents. "
                "Do NOT introduce new facts or entities that are not related to the query. "
                "Only clarify wording or expand the query slightly if needed."
            )

            user_message = f"""
Original Query:
{query}

Relevant Context:
{context_text}

Return only the improved search query.
"""

            response = self.llm.generate(system_message, user_message)

            if not response:
                return query

            rewritten = response.strip()

            if not rewritten:
                return query

            logger.info(
                f"Query rewritten | original='{query}' | rewritten='{rewritten}'"
            )

            return rewritten

        except Exception:
            logger.exception("Query rewriting failed")
            return query