"""Minimal, dependency-free semantic-version parsing and range satisfaction.

Supports the subset used by ULI manifests:

    exact:   1.2.3
    comparators: >=1.0.0  >1.0.0  <=2.0.0  <2.0.0  =1.2.3  ==1.2.3
    caret:   ^1.2.3   -> >=1.2.3 <2.0.0     ^0.2.3 -> >=0.2.3 <0.3.0
    tilde:   ~1.2.3   -> >=1.2.3 <1.3.0
    wildcard: 1.x  1.2.x  *  (and empty string)
    conjunction: ">=1.0.0 <2.0.0" or ">=1.0.0, <2.0.0"
    disjunction: ">=1.0.0 <2.0.0 || >=3.0.0"

Pre-release/build metadata are parsed but ignored for ordering, which is an
explicitly documented MVP limitation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_VERSION_RE = re.compile(
    r"^\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:-([0-9A-Za-z.\-]+))?(?:\+[0-9A-Za-z.\-]+)?\s*$"
)


class VersionError(ValueError):
    pass


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int = 0
    patch: int = 0

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.major}.{self.minor}.{self.patch}"

    def as_tuple(self) -> tuple[int, int, int]:
        return (self.major, self.minor, self.patch)


def parse_version(text: str) -> Version:
    m = _VERSION_RE.match(text or "")
    if not m:
        raise VersionError(f"Invalid semantic version: {text!r}")
    return Version(int(m.group(1)), int(m.group(2) or 0), int(m.group(3) or 0))


def _cmp(a: Version, op: str, b: Version) -> bool:
    if op in (">=",):
        return a >= b
    if op == ">":
        return a > b
    if op == "<=":
        return a <= b
    if op == "<":
        return a < b
    if op in ("=", "=="):
        return a == b
    raise VersionError(f"Unknown operator {op!r}")


_WILDCARD_RE = re.compile(r"^\s*(\d+)(?:\.(\d+))?\.(?:x|X|\*)\s*$")
_PARTIAL_WILDCARD_RE = re.compile(r"^\s*(\d+|x|X|\*)\s*$")


def _caret_upper(v: Version) -> Version:
    if v.major > 0:
        return Version(v.major + 1, 0, 0)
    if v.minor > 0:
        return Version(0, v.minor + 1, 0)
    return Version(0, 0, v.patch + 1)


def _tilde_upper(v: Version) -> Version:
    return Version(v.major, v.minor + 1, 0)


def _match_token(version: Version, token: str) -> bool:
    token = token.strip()
    if token in ("", "*", "x", "X"):
        return True

    m = _PARTIAL_WILDCARD_RE.match(token)
    if m:
        return True  # bare major wildcard, e.g. "1" or "x"

    m = _WILDCARD_RE.match(token)
    if m:
        major = int(m.group(1))
        minor = m.group(2)
        if minor is None:
            return version.major == major
        return version.major == major and version.minor == int(minor)

    if token.startswith("^"):
        base = parse_version(token[1:])
        return version >= base and version < _caret_upper(base)
    if token.startswith("~"):
        base = parse_version(token[1:])
        return version >= base and version < _tilde_upper(base)

    for op in (">=", "<=", "==", ">", "<", "="):
        if token.startswith(op):
            base = parse_version(token[len(op):])
            return _cmp(version, op, base)

    return version == parse_version(token)


def satisfies_range(version: str | Version, range_text: str | None) -> bool:
    """Return True if *version* satisfies *range_text*.

    An empty/None range means "any version" (only used for optional metadata).
    """
    v = parse_version(version) if isinstance(version, str) else version
    if range_text is None or str(range_text).strip() == "":
        return True

    for clause in str(range_text).split("||"):
        tokens = [t for t in re.split(r"[\s,]+", clause.strip()) if t]
        if not tokens:
            return True
        if all(_match_token(v, t) for t in tokens):
            return True
    return False


def parse_constraints(range_text: str) -> list[str]:
    """Return normalised token list for a range (used for error messages)."""
    return [t for clause in str(range_text).split("||") for t in re.split(r"[\s,]+", clause.strip()) if t]
