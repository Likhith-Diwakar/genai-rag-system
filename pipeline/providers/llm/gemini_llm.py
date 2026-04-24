import os
import warnings
from dotenv import load_dotenv
import google.generativeai as genai

from pipeline.interfaces.base_llm import BaseLLM
from pipeline.utils.logger import logger
from pipeline.utils.metrics import metrics

warnings.filterwarnings("ignore", category=FutureWarning)

load_dotenv()


class GeminiLLM(BaseLLM):

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found. Check your .env file.")

        genai.configure(api_key=api_key)

        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.model = genai.GenerativeModel(self.model_name)

    def _extract_text(self, response) -> str:
        try:
            if hasattr(response, "text") and response.text:
                return response.text.strip()

            if hasattr(response, "candidates"):
                for candidate in response.candidates:
                    content = getattr(candidate, "content", None)
                    if content:
                        parts = getattr(content, "parts", [])
                        for part in parts:
                            if hasattr(part, "text") and part.text:
                                return part.text.strip()
        except Exception:
            pass

        return ""

    def generate(self, system_message: str, user_message: str) -> str:
        try:
            logger.info(f"Calling Gemini | model={self.model_name}")

            prompt = f"{system_message}\n\n{user_message}"

            response = self.model.generate_content(prompt)

            text = self._extract_text(response)

            if text:
                metrics.inc_model(self.model_name)

                # ⚠️ Gemini doesn't expose tokens directly
                # Optional: estimate later if needed

                return text

            logger.warning("Gemini returned empty response")
            metrics.inc("llm_retries")
            return ""

        except Exception as e:
            logger.error(f"Gemini error: {e}")
            metrics.inc("llm_retries")
            return ""
