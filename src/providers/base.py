"""Provider adapter contract for structured message generation."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProviderResult:
    output_text: str
    request_id: str | None
    model: str | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None


class MessageProvider(Protocol):
    def generate(self, payload: dict, system_prompt: str) -> ProviderResult:
        """Generate structured message JSON for the supplied allowlisted payload."""
