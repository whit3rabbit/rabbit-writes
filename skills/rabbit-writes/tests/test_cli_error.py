"""
test_cli_error.py - unit tests for LLM-friendly CLI argument parser and error formatting.
"""

import io
import sys

import helpers  # noqa: F401
from rwlib.cli_error import LLMArgumentParser, format_file_error, format_llm_error


def test_llm_argument_parser_custom_error():
    parser = LLMArgumentParser(
        prog="test_script.py",
        description="Test description for script",
        examples=["python3 test_script.py input.txt --flag"]
    )
    parser.add_argument("input_file", help="Input file path")
    parser.add_argument("--flag", action="store_true", help="Enable flag")

    stderr_buf = io.StringIO()
    orig_stderr = sys.stderr
    try:
        sys.stderr = stderr_buf
        try:
            parser.parse_args([])
            assert False, "Should have raised SystemExit"
        except SystemExit as exc:
            assert exc.code == 2, f"Expected code 2, got {exc.code}"
    finally:
        sys.stderr = orig_stderr

    output = stderr_buf.getvalue()
    assert "CLI ERROR:" in output, f"CLI ERROR missing in output: {output}"
    assert "the following arguments are required: input_file" in output
    assert "Script: test_script.py" in output
    assert "input_file (REQUIRED" in output
    assert "--flag (OPTIONAL" in output
    assert "python3 test_script.py input.txt --flag" in output


def test_format_file_error():
    err_msg = format_file_error(
        script_name="scan.py",
        path="non_existent.md",
        parameter_name="file",
        expected_type="file path",
        details="No such file or directory",
        examples=["python3 scan.py draft.md"]
    )
    assert "FILE / I/O ERROR:" in err_msg
    assert "Parameter: 'file' (expected type: file path)" in err_msg
    assert "Provided Path: 'non_existent.md'" in err_msg
    assert "python3 scan.py draft.md" in err_msg
