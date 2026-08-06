from __future__ import annotations

from app.utils.tokens import extract_usage_from_sse_line


class SseUsageParser:
    """Incrementally parse SSE data lines without retaining the entire stream."""

    def __init__(self) -> None:
        self._pending = b""
        self.usage: tuple[int | None, int | None, int | None] = (None, None, None)

    def feed(self, chunk: bytes) -> None:
        self._pending += chunk
        lines = self._pending.splitlines(keepends=True)
        self._pending = b""
        if lines and not lines[-1].endswith((b"\n", b"\r")):
            self._pending = lines.pop()
        for line in lines:
            parsed = extract_usage_from_sse_line(line.strip())
            if any(value is not None for value in parsed):
                self.usage = parsed

    def finish(self) -> None:
        if self._pending:
            parsed = extract_usage_from_sse_line(self._pending.strip())
            if any(value is not None for value in parsed):
                self.usage = parsed
            self._pending = b""
