"""Text parsing utilities for Atlas Core."""


class TextParser:
    """A minimal text parser implementation."""

    def parse(self, text: str) -> dict:
        return {"text": text, "length": len(text)}
