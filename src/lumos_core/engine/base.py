class BaseEngine:
    def process(self, message: str) -> dict:
        raise NotImplementedError
