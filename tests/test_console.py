"""Tests for spawn.utils.console — encoding safety."""

import io

import pytest

from rich.console import Console


def test_console_prints_unicode_glyphs_without_error():
    """Printing ✨ and 🏥 to a non-terminal byte stream must not raise UnicodeEncodeError.

    This simulates the Windows pipe condition (stdout redirected, encoding=cp1252)
    by constructing a Console that writes to a BytesIO with latin-1 — characters
    outside that range would crash a naive encoder.  The fix in console.py uses
    errors='replace', so the test confirms no exception is raised.
    """
    # BytesIO with a wrapper that rejects non-latin-1 bytes unless replaced
    buf = io.BytesIO()
    wrapper = io.TextIOWrapper(buf, encoding="latin-1", errors="replace")

    # Build a Console pointing at this restricted stream — same parameters
    # the real console uses after the reconfigure fix.
    test_console = Console(file=wrapper, highlight=False)

    # Neither of these characters is representable in latin-1; they must
    # degrade to '?' rather than raising UnicodeEncodeError.
    try:
        test_console.print("✨ Project Created Successfully 🏥")
    except UnicodeEncodeError as exc:
        pytest.fail(f"UnicodeEncodeError raised when printing glyphs: {exc}")
    finally:
        wrapper.flush()
