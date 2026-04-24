import os
from dotenv import load_dotenv
from openai import OpenAI

from pipeline.interfaces.base_llm import BaseLLM
from pipeline.utils.logger import logger
from pipeline.utils.metrics import metrics

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

            response = completion.choices[0].message.content.strip()

            if response:
                metrics.inc_model(self.model_name)

                #Token + Cost tracking
                usage = getattr(completion, "usage", None)
                if usage:
                    input_tokens = getattr(usage, "prompt_tokens", 0)
                    output_tokens = getattr(usage, "completion_tokens", 0)

                    metrics.add_tokens(input_tokens, output_tokens)
                    metrics.add_cost(self.model_name, input_tokens, output_tokens)

            return response

        except Exception as e:
            logger.error(f"OpenRouter error for model={self.model_name}: {e}")
            metrics.inc("llm_retries")
            return ""
