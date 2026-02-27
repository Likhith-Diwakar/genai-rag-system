import os
from PIL import Image
from dotenv import load_dotenv
from src.utils.logger import logger
from google import genai
from google.genai.types import GenerateContentConfig


# --------------------------------------------------
# Load environment
# --------------------------------------------------
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_NAME = "models/gemini-2.5-flash"

client = None
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info(f"Gemini client initialized | model={MODEL_NAME}")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini client: {e}")


# --------------------------------------------------
# Strong structured extraction prompt
# --------------------------------------------------
STRUCTURED_PROMPT = """
You are an advanced document vision extraction system.

Your task:
Extract ALL visible structured and textual information exactly as shown.

STRICT RULES:
- Do NOT summarize.
- Do NOT interpret.
- Do NOT estimate missing values.
- Do NOT calculate anything.
- Preserve numeric values EXACTLY as written.
- Preserve percentages EXACTLY as written.

IF THE IMAGE CONTAINS A TABLE:
- Reconstruct it as a clean markdown table.
- Preserve headers exactly.
- Preserve row/column alignment.
- Do not merge rows.
- Do not remove columns.
- Return ONLY the markdown table.

IF THE IMAGE CONTAINS A CHART OR GRAPH:
Extract in this format:

CHART_TITLE: <title if visible>

X_AXIS_LABEL: <label if visible>
Y_AXIS_LABEL: <label if visible>

LEGEND:
- <legend item 1>
- <legend item 2>

DATA_POINTS:
- <label> : <value>
- <label> : <value>

Preserve all numeric values exactly.

IF THE IMAGE CONTAINS SCANNED TEXT:
- Return exact transcription.
- Maintain reading order.

Return ONLY extracted structured content.
"""


# --------------------------------------------------
# Optional image optimization
# --------------------------------------------------
def _optimize_image(pil_image: Image.Image) -> Image.Image:
    max_dimension = 1600

    width, height = pil_image.size

    if max(width, height) > max_dimension:
        ratio = max_dimension / float(max(width, height))
        new_size = (int(width * ratio), int(height * ratio))
        pil_image = pil_image.resize(new_size, Image.LANCZOS)

    return pil_image


# --------------------------------------------------
# Vision extraction
# --------------------------------------------------
def run_vision_extraction(pil_image: Image.Image) -> str:

    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set. Skipping vision extraction.")
        return ""

    if not client:
        logger.warning("Gemini client not initialized. Skipping vision extraction.")
        return ""

    try:
        logger.info("Calling Gemini Vision API...")

        optimized_image = _optimize_image(pil_image)

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[STRUCTURED_PROMPT, optimized_image],
            config=GenerateContentConfig(
                temperature=0,   # deterministic output
                # top_p intentionally omitted — top_p=0.0 can cause API errors
                # temperature=0 already ensures determinism
            ),
        )

        if not response:
            logger.warning("Gemini returned no response object.")
            return ""

        text_output = getattr(response, "text", None)

        if not text_output:
            # Log full response for debugging when text is empty
            logger.warning(f"Gemini returned empty text. Full response: {response}")
            return ""

        cleaned = text_output.strip()

        # Safety: prevent useless hallucinated filler
        if len(cleaned) < 5:
            logger.warning(f"Gemini output too short (len={len(cleaned)}), discarding.")
            return ""

        logger.info(f"Gemini extraction successful. Output length: {len(cleaned)} chars")
        return cleaned

    except Exception as e:
        logger.error(f"Gemini vision extraction failed: {e}")
        return ""