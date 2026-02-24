import os
import base64
import requests
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from src.utils.logger import logger


# Load environment variables
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Correct OpenRouter Vision model
VISION_MODEL = "qwen/qwen-2-vl-7b-instruct"

STRUCTURED_PROMPT = """
Extract all visible textual data from this image.

If this is a table:
- Return a clean markdown table.
- Preserve headers and structure.
- Preserve numeric values exactly.

If this is a chart or graph:
- Extract:
    - Chart title
    - Axis labels
    - Legend entries
    - Data values per category
- Preserve numeric values exactly.
- Maintain logical reading order.

Return only extracted structured content.
"""


def _pil_to_base64(pil_image: Image.Image) -> str:
    buffered = BytesIO()
    pil_image.save(buffered, format="PNG")
    img_bytes = buffered.getvalue()
    return base64.b64encode(img_bytes).decode("utf-8")


def run_vision_extraction(pil_image: Image.Image) -> str:
    if not OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY not set.")
        return ""

    try:
        logger.info("Calling Vision API for image extraction...")

        image_base64 = _pil_to_base64(pil_image)

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "genai-rag-system"
        }

        payload = {
            "model": VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": STRUCTURED_PROMPT
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0,
            "max_tokens": 2048
        }

        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=90
        )

        if response.status_code != 200:
            logger.error(
                f"Vision API error: {response.status_code} - {response.text}"
            )
            return ""

        data = response.json()

        if "choices" not in data or not data["choices"]:
            logger.error(f"Unexpected Vision API response format: {data}")
            return ""

        content = data["choices"][0]["message"]["content"]

        logger.info("Vision extraction successful.")
        return content.strip()

    except Exception as e:
        logger.error(f"Vision extraction failed: {e}")
        return ""