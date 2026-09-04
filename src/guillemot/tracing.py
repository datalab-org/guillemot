"""Logging configuration to save traces both locally
and report them to logfire if the token is present.

"""

import pathlib
from typing import IO, Optional, Sequence

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)

TRACE_FILENAME = "trace.jsonl"


class SessionFileSpanExporter(SpanExporter):
    """Write each finished span as a line of JSON into the session directory."""

    def __init__(self, filename: str = TRACE_FILENAME):
        self.filename = filename
        self._path: Optional[pathlib.Path] = None
        self._file: Optional[IO[str]] = None

    @property
    def path(self) -> Optional[pathlib.Path]:
        """Where spans are being written, or None if nothing has been written yet."""
        return self._path

    def _open(self) -> IO[str]:
        if self._file is None:
            from guillemot.session import session_dir

            self._path = session_dir() / self.filename
            self._file = self._path.open("a", encoding="utf-8")
        return self._file

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if not spans:
            return SpanExportResult.SUCCESS
        try:
            handle = self._open()
            for span in spans:
                handle.write(span.to_json(indent=None) + "\n")
            handle.flush()
        except Exception:
            return SpanExportResult.FAILURE
        return SpanExportResult.SUCCESS

    def force_flush(self, timeout_millis: int = 30_000) -> bool:
        if self._file is not None:
            self._file.flush()
        return True

    def shutdown(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None


def configure_tracing() -> Optional[SessionFileSpanExporter]:
    """Configure logfire so that spans are saved to the session directory.

    They are additionally sent to the logfire dashboard when `LOGFIRE_TOKEN` is set.
    Returns the exporter, or None if logfire is not installed.
    """
    import os

    try:
        import logfire
    except ImportError:
        return None  # Logfire is optional

    exporter = SessionFileSpanExporter()
    logfire.configure(
        token=os.getenv("LOGFIRE_TOKEN"),
        send_to_logfire="if-token-present",
        console=False,
        additional_span_processors=[SimpleSpanProcessor(exporter)],
    )
    return exporter


def record_context_usage(used: int, limit: int | None) -> None:
    """Record how full the context window is, as a logfire span of its own.

    The `chat` spans carry `gen_ai.usage.input_tokens`, but a raw token count says
    nothing about how close the run is to the window it has to fit in — which is the
    thing worth watching, since the prompt is re-sent and re-read on every request.
    """
    try:
        import logfire
    except ImportError:
        return

    if limit:
        logfire.info(
            "context {used}/{limit} tokens ({fraction:.0%} full)",
            used=used,
            limit=limit,
            fraction=used / limit,
        )
    else:
        logfire.info("context {used} tokens", used=used, limit=None)
