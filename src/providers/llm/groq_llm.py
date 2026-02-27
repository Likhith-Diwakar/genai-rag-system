# src/providers/llm/groq_llm.py

import os
from dotenv import load_dotenv
from groq import Groq, RateLimitError
from src.interfaces.base_llm import BaseLLM
from src.utils.logger import logger

load_dotenv()

PRIMARY_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "llama-3.1-8b-instant"


class GroqLLM(BaseLLM):

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found. Check your .env file.")
        self.client = Groq(api_key=api_key)

    def _call(self, model: str, system_message: str, user_message: str) -> str:
        try:
            logger.info(f"Calling Groq | model={model}")

            completion = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.1,
                max_tokens=600,
            )

            return completion.choices[0].message.content.strip()

        except RateLimitError:
            logger.warning(f"Rate limit reached for model={model}")
            return ""

        except Exception as e:
            logger.error(f"Groq error for model={model}: {e}")
            return ""

    def generate(self, system_message: str, user_message: str) -> str:
        answer = self._call(PRIMARY_MODEL, system_message, user_message)

        if answer:
            return answer

        logger.info("Primary model unavailable. Falling back.")

        answer = self._call(FALLBACK_MODEL, system_message, user_message)

        if answer:
            return answer

        return "I do not know based on the provided documents."