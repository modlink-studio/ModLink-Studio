from __future__ import annotations


class MarkerCodec:
    """Map session-local string labels to stable numeric BrainFlow markers."""

    def __init__(self) -> None:
        self._label_to_code: dict[str, float] = {}
        self._next_code = 1

    def encode(self, label: str) -> float:
        normalized = str(label).strip()
        if not normalized:
            raise ValueError("marker label must not be empty")

        code = self._label_to_code.get(normalized)
        if code is not None:
            return code

        code = float(self._next_code)
        self._label_to_code[normalized] = code
        self._next_code += 1
        return code

    def snapshot(self) -> dict[str, float]:
        return dict(self._label_to_code)
