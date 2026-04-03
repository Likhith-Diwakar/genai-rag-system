import os
from dotenv import load_dotenv
from groq import Groq, RateLimitError

from src.interfaces.base_llm import BaseLLM
from src.utils.logger import logger
from src.utils.metrics import metrics

load_dotenv()

PRIMARY_MODEL = os.getenv("GROQ_PRIMARY_MODEL", "llama-3.3-70b-versatile")
FALLBACK_MODEL = os.getenv("GROQ_FALLBACK_MODEL", "llama-3.1-8b-instant")


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

            response = completion.choices[0].message.content.strip()

            if response:
                metrics.inc_model(model)

                # Token + Cost tracking
                usage = getattr(completion, "usage", None)
                if usage:
                    input_tokens = getattr(usage, "prompt_tokens", 0)
                    output_tokens = getattr(usage, "completion_tokens", 0)

                    metrics.add_tokens(input_tokens, output_tokens)
                    metrics.add_cost(model, input_tokens, output_tokens)

            return response

        except RateLimitError:
            logger.warning(f"Rate limit reached for model={model}")
            metrics.inc("llm_retries")
            return ""

        except Exception as e:
            logger.error(f"Groq error for model={model}: {e}")
            metrics.inc("llm_retries")
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