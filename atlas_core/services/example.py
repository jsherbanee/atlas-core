"""Example service implementations for Atlas Core."""


class ExampleService:
    """A basic service example."""

    def process(self, payload: dict) -> dict:
        return {"status": "ok", "payload": payload}
