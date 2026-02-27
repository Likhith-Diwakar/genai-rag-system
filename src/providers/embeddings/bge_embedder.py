import os
import requests
from typing import List
from src.interfaces.base_embedder import BaseEmbedder


HF_MODEL = "BAAI/bge-small-en-v1.5"
HF_API_URL = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}"


class BGEEmbedder(BaseEmbedder):

    def __init__(self):
        self.api_token = os.getenv("HF_API_TOKEN")
        if not self.api_token:
            raise ValueError("HF_API_TOKEN not found in environment variables.")

    def embed(self, texts: List[str]) -> List[List[float]]:
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        embeddings = []

        for text in texts:
            response = requests.post(
                HF_API_URL,
                headers=headers,
                json={
                    "inputs": text
                },
                timeout=60
            )

            if response.status_code != 200:
                raise Exception(
                    f"HuggingFace embedding API error: "
                    f"{response.status_code} | {response.text}"
                )

            vector = response.json()

            # Some responses return nested list
            if isinstance(vector, list) and isinstance(vector[0], list):
                vector = vector[0]

            embeddings.append(vector)

        return embeddings