import os
from dotenv import load_dotenv
from openai import OpenAI
from src.interfaces.base_llm import BaseLLM
from src.utils.logger import logger

load_dotenv()


class OpenRouterLLM(BaseLLM):

    def __init__(self, model_name: str):
        api_key = os.getenv("OPENROUTER_API_KEY")

        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found. Check your .env file.")

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )

        self.model_name = model_name

    def generate(self, system_message: str, user_message: str) -> str:
        try:
            logger.info(f"Calling OpenRouter | model={self.model_name}")

            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.1,
                max_tokens=600
            )

            return completion.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"OpenRouter error for model={self.model_name}: {e}")
            return ""