"""The hook should spend extraction calls on reusable changes, not tool chatter."""

import importlib.util
from pathlib import Path


HOOK_PATH = Path(__file__).resolve().parents[2] / "memoff" / "plugin" / "hooks" / "post_tool_use.py"
spec = importlib.util.spec_from_file_location("memoff_post_tool_use", HOOK_PATH)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


def test_read_containing_error_word_is_not_a_tool_failure():
    event = hook.build_event({
        "tool_name": "Read",
        "tool_input": {"file_path": "services.py"},
        "tool_response": {"file": {"content": "class FileNotSupportedError(Exception): pass"}},
    })
    assert event is None


def test_successful_edit_records_short_change_and_file(monkeypatch, tmp_path):
    monkeypatch.setenv("MEMOFF_WORKSPACE", str(tmp_path))
    path = tmp_path / "xitkit" / "services.py"
    event = hook.build_event({
        "tool_name": "Edit",
        "tool_input": {"file_path": str(path), "old_string": "return relative", "new_string": "return absolute"},
        "tool_response": {"filePath": str(path), "oldString": "return relative", "newString": "return absolute"},
    })
    assert event is not None
    content, event_type, metadata = event
    assert event_type == "code_change"
    assert "xitkit/services.py" in content
    assert "return absolute" in content
    assert metadata == {"tool": "Edit", "memory_only": True, "file": "xitkit/services.py"}


def test_edit_summary_omits_unchanged_extension_rules():
    event = hook.build_event({
        "tool_name": "Edit",
        "tool_input": {
            "file_path": "xitkit/services.py",
            "old_string": "for pattern in ('**/*.xit', '**/*.md'):\n    files.extend(directory.glob(pattern))\nreturn relative(files)",
            "new_string": "for pattern in ('**/*.xit', '**/*.md'):\n    files.extend(directory.glob(pattern))\nreturn resolved(files)",
        },
        "tool_response": {"success": True},
    })
    assert event is not None
    assert "return resolved(files)" in event[0]
    assert "'**/*.md'" not in event[0]


def test_edit_summary_drops_whitespace_only_hunks():
    event = hook.build_event({
        "tool_name": "Edit",
        "tool_input": {"file_path": "services.py", "old_string": "x = 1\n    \nreturn old", "new_string": "x = 1\n\nreturn new"},
        "tool_response": {"success": True},
    })
    assert event is not None
    assert "return new" in event[0]
    assert "-    " not in event[0]


def test_explicit_failure_keeps_diagnostic():
    event = hook.build_event({
        "tool_name": "Bash",
        "tool_input": {"command": "pytest tests/test_services.py"},
        "tool_response": {"stdout": "1 failed", "exitCode": 1},
    })
    assert event is not None
    assert event[1] == "tool_error"
    assert "1 failed" in event[0]


def test_successful_shell_output_is_skipped_even_when_it_mentions_failures():
    event = hook.build_event({
        "tool_name": "Bash",
        "tool_input": {"command": "pytest -q | tail -20"},
        "tool_response": {"stdout": "14 tests failed in a previous run", "stderr": "", "interrupted": False},
    })
    assert event is None
