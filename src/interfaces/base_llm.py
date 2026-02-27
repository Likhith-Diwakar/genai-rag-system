from abc import ABC, abstractmethod

class BaseLLM(ABC):
    @abstractmethod
    def generate(self, system_message: str, user_message: str) -> str:
        pass