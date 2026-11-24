"""Guards against invisible control characters in source files.

Twice during the build, a scripted edit turned the regex word boundary `\\b` into a literal
backspace byte. The code still ran, but the regex silently never matched. This test fails fast.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def test_no_control_characters_in_sources():
    bad = []
    for pattern in ("app/**/*.py", "eval/*.py", "scripts/*.py", "tests/*.py", "app/templates/*.html"):
        for f in ROOT.glob(pattern):
            for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if CONTROL.search(line):
                    bad.append(f"{f.relative_to(ROOT)}:{n}")
    assert not bad, bad
