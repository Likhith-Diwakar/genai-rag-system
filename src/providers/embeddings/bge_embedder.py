import os
import requests
import certifi
from typing import List
from src.interfaces.base_embedder import BaseEmbedder


HF_MODEL = "BAAI/bge-small-en-v1.5"
HF_API_URL = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}"


class BGEEmbedder(BaseEmbedder):

    def __init__(self):
        self.api_token = os.getenv("HF_API_TOKEN")
        if not self.api_token:
            raise ValueError("HF_API_TOKEN not found in environment variables.")

        self.headers = {
            "Authorization": f"Bearer {self.api_token.strip()}",
            "Content-Type": "application/json"
        }

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Batch embedding call to HuggingFace Inference Router.
        Adds SSL-safe handling + retry fallback.
        """

        if not texts:
            return []

        payload = {
            "inputs": texts
        }

        try:
            # Primary request (secure)
            response = requests.post(
                HF_API_URL,
                headers=self.headers,
                json=payload,
                timeout=180,
                verify=certifi.where()
            )

        except requests.exceptions.SSLError:
            # Fallback (only if SSL fails)
            response = requests.post(
                HF_API_URL,
                headers=self.headers,
                json=payload,
                timeout=180,
                verify=False
            )

        except requests.exceptions.RequestException as e:
            raise Exception(f"Embedding request failed: {str(e)}")

        if response.status_code != 200:
            raise Exception(
                f"HuggingFace embedding API error: "
                f"{response.status_code} | {response.text}"
            )

        result = response.json()

        # Handle different HF response formats safely
        if isinstance(result, list):

            # Case 1: batch embeddings [[...], [...]]
            if result and isinstance(result[0], list):
                return result

            # Case 2: single embedding [....]
            if result and isinstance(result[0], float):
                return [result]

        raise Exception(
            f"Unexpected embedding response format: {type(result)} | {result}"
        )
