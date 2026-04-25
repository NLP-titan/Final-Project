from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    handler: Callable[[dict], dict]

    @property
    def spec(self) -> dict:
        """Anthropic / OpenAI-compatible tool spec."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    def run(self, arguments: dict) -> dict:
        try:
            return self.handler(arguments or {})
        except Exception as exc:  # surfaced to the model so it can recover
            return {"error": f"{type(exc).__name__}: {exc}"}
