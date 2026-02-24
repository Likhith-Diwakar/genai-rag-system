from src.llm.rag import call_llm
from src.utils.logger import logger


def structure_table_text(raw_text: str) -> str:
    """
    Takes OCR extracted table text
    and converts it into clean structured table
    using Groq Llama model.
    Only called when table-like content is detected.
    """

    logger.info("Structuring detected table via Groq LLM")

    system_message = """
You are a data structuring assistant.

Your task:
- Convert OCR extracted table text into clean structured format.
- Preserve ALL original values exactly.
- Do NOT hallucinate.
- Do NOT summarize.
- Maintain row-column relationships clearly.
- If structure is unclear, return readable table without inventing columns.

Return only the cleaned structured table.
"""

    user_message = f"""
OCR TABLE TEXT:
{raw_text}
"""

    return call_llm(system_message, user_message)