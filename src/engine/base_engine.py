from typing import Any


class BaseEngine:
    def process(self, message: str, *args: Any, **kwargs: Any) -> dict:
        raise NotImplementedError
