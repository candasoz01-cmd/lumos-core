from abc import ABC, abstractmethod

class BaseEngine(ABC):

    @abstractmethod
    def process(self, message: str) -> dict:
        pass
