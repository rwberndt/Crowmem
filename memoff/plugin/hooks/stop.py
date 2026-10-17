#!/usr/bin/env python3
"""Stop: the only point in the hook lifecycle that sees the agent's own
self-report. SessionEnd carries no outcome signal at all (just a `reason`
per the confirmed hook schema), so this stashes the STATUS line for
SessionEnd to pick up -- a best-effort proxy for the private grader's
verdict, not the verdict itself. See memoff/memory.yml's `notes`.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import _client as c  # noqa: E402

STATUS_RE = re.compile(r"STATUS:\s*(implemented|not_implemented)", re.IGNORECASE)


def main() -> None:
    stdin = c.read_stdin_json()
    message = stdin.get("last_assistant_message", "") or ""
    match = STATUS_RE.search(message)
    status = match.group(1).lower() if match else "unknown"

    directory = c.state_dir()
    if directory:
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, "status"), "w", encoding="utf-8") as f:
            f.write(status)

    c.emit_empty()


if __name__ == "__main__":
    main()
