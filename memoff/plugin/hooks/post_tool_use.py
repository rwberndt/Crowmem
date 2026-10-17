#!/usr/bin/env python3
"""PostToolUse: feed each tool call into the episodic store. The salience
gate (not this hook) decides whether any of it becomes a durable memory --
this just reports the observation."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import _client as c  # noqa: E402

MAX_CONTENT_CHARS = 2000
ERROR_MARKERS = ("error", "traceback", "failed", "exception")


def main() -> None:
    stdin = c.read_stdin_json()
    tool_name = stdin.get("tool_name", "unknown_tool")
    tool_input = stdin.get("tool_input", {}) or {}
    tool_result = stdin.get("tool_result", {}) or {}
    result_text = tool_result.get("text", "") if isinstance(tool_result, dict) else str(tool_result)

    looked_like_error = any(marker in result_text.lower() for marker in ERROR_MARKERS)
    event_type = "tool_error" if looked_like_error else "tool_success"

    summary_input = json.dumps(tool_input)[:500] if tool_input else ""
    content = f"Tool {tool_name} called with {summary_input}. Result: {result_text[:MAX_CONTENT_CHARS]}"

    c.remember_event(
        content=content,
        event_type=event_type,
        project=c.store_name(),
        metadata={"tool": tool_name, "task": c.issue_task()},
    )
    c.emit_empty()


if __name__ == "__main__":
    main()
