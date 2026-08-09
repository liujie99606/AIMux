from __future__ import annotations

from app.utils.tokens import extract_usage_from_sse_line


class SseUsageParser:
    """增量解析 SSE 用量事件，并合并分散在不同事件中的 token 字段。"""

    def __init__(self) -> None:
        self._pending = b""
        self._input_tokens: int | None = None
        self._output_tokens: int | None = None
        self._total_tokens: int | None = None
        self._cached_tokens: int | None = None

    @property
    def usage(self) -> tuple[int | None, int | None, int | None, int | None]:
        """返回当前已聚合的 token 用量，缺失总量时按输入和输出估算。"""
        total_tokens = self._total_tokens
        if total_tokens is None and (self._input_tokens is not None or self._output_tokens is not None):
            total_tokens = (self._input_tokens or 0) + (self._output_tokens or 0)
        return self._input_tokens, self._output_tokens, total_tokens, self._cached_tokens

    def feed(self, chunk: bytes) -> None:
        self._pending += chunk
        lines = self._pending.splitlines(keepends=True)
        self._pending = b""
        if lines and not lines[-1].endswith((b"\n", b"\r")):
            self._pending = lines.pop()
        for line in lines:
            self._merge(extract_usage_from_sse_line(line.strip()))

    def finish(self) -> None:
        if self._pending:
            self._merge(extract_usage_from_sse_line(self._pending.strip()))
            self._pending = b""

    def _merge(self, parsed: tuple[int | None, int | None, int | None, int | None]) -> None:
        """以最新非空字段更新已解析的用量。"""
        input_tokens, output_tokens, total_tokens, cached_tokens = parsed
        if input_tokens is not None:
            self._input_tokens = input_tokens
        if output_tokens is not None:
            self._output_tokens = output_tokens
        if total_tokens is not None:
            self._total_tokens = total_tokens
        if cached_tokens is not None:
            self._cached_tokens = cached_tokens
