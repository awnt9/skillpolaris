from __future__ import annotations

import time


class SourceRateLimiter:
    """Enforces a minimum interval between HTTP calls per source."""

    def __init__(self) -> None:
        self._last_call_at: dict[str, float] = {}

    def wait(self, source: str, min_interval_seconds: float) -> None:
        if min_interval_seconds <= 0:
            return

        now = time.monotonic()
        last = self._last_call_at.get(source)
        if last is not None:
            elapsed = now - last
            remaining = min_interval_seconds - elapsed
            if remaining > 0:
                time.sleep(remaining)

        self._last_call_at[source] = time.monotonic()
