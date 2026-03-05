import os
from dotenv import load_dotenv
import google.generativeai as genai

from src.interfaces.base_llm import BaseLLM
from src.utils.logger import logger

load_dotenv()


MODEL_NAME = "gemini-1.5-flash"


class GeminiLLM(BaseLLM):

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY not found. Check your .env file.")

        genai.configure(api_key=api_key)

        self.model = genai.GenerativeModel(MODEL_NAME)

    def generate(self, system_message: str, user_message: str) -> str:
        try:
            logger.info(f"Calling Gemini | model={MODEL_NAME}")

            prompt = f"{system_message}\n\n{user_message}"

            response = self.model.generate_content(prompt)

            # Safe response extraction
            if hasattr(response, "text") and response.text:
                return response.text.strip()

            # Fallback if response structure changes
            if hasattr(response, "candidates"):
                for candidate in response.candidates:
                    if hasattr(candidate, "content"):
                        parts = getattr(candidate.content, "parts", [])
                        for part in parts:
                            if hasattr(part, "text"):
                                return part.text.strip()

            logger.warning("Gemini returned empty response")
            return ""

        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return ""