"""POSIX ERE as bash's [[ =~ ]] compiles it, translated to Python's re (spec D3).

Every pattern decision of the shell guards is `[[ $s =~ $re ]]`, that is
glibc's regcomp(REG_EXTENDED) without REG_NEWLINE (ai-hook-common.sh:227-238).
This module parses a pattern as glibc's posix/regcomp.c does and rejects what
it rejects. It works on UTF-8 bytes, which is glibc in the C locale, on every
OS (H2); under a UTF-8 locale glibc counts characters instead, so a non-ASCII
pattern or subject there is a declared divergence (D6). Standard library only;
it runs under `python3 -I -S`.
"""
from __future__ import annotations

import re

RE_DUP_MAX = 0x7FFF
_ALL = (1 << 256) - 1


class EreError(ValueError):
    """A pattern glibc's regcomp rejects; bash's [[ =~ ]] answers 2 for it."""


def _span(lo: int, hi: int) -> int:
    """The bytes lo..hi as a 256-bit set."""
    return ((1 << (hi + 1)) - 1) ^ ((1 << lo) - 1)


def _of(chars: bytes) -> int:
    return sum(1 << c for c in set(chars))


_DIGIT, _UPPER, _LOWER, _GRAPH = _span(0x30, 0x39), _span(0x41, 0x5A), _span(0x61, 0x7A), _span(0x21, 0x7E)
# glibc's build_charclass in the C locale: the twelve names, ASCII only.
_CLASSES = {
    "alnum": _UPPER | _LOWER | _DIGIT, "alpha": _UPPER | _LOWER, "blank": _of(b" \t"),
    "cntrl": _span(0, 0x1F) | 1 << 0x7F, "digit": _DIGIT, "graph": _GRAPH,
    "lower": _LOWER, "print": _GRAPH | 1 << 0x20, "punct": _GRAPH & ~(_UPPER | _LOWER | _DIGIT),
    "space": _of(b" \t\n\v\f\r"), "upper": _UPPER, "xdigit": _DIGIT | _of(b"ABCDEFabcdef"),
}
_WORD = _CLASSES["alnum"] | 1 << 0x5F
# A backslash and the byte after it (peek_token): the GNU operators; \1-\9 are
# back-references and every other byte stands for itself, so \n is "n".
_ESCAPES = {
    0x77: ("set", _WORD), 0x57: ("set", _ALL ^ _WORD),
    0x73: ("set", _CLASSES["space"]), 0x53: ("set", _ALL ^ _CLASSES["space"]),
    **{ord(c): ("anchor", c) for c in "<>bB`'"},
}
_PLAIN = {
    0x7C: ("|", None), 0x28: ("(", None), 0x29: (")", None), 0x2E: ("any", None),
    0x5E: ("anchor", "^"), 0x24: ("anchor", "$"),
    0x2A: ("dup", (0, None)), 0x2B: ("dup", (1, None)), 0x3F: ("dup", (0, 1)),
}
_SYMBOLS = {0x2E: "coll", 0x3D: "equiv", 0x3A: "class"}


def tokenize(pattern: str) -> list[tuple[str, object]]:
    """The pattern's tokens, as glibc's peek_token reads its UTF-8 bytes in the C locale.

    A token is ("lit", byte), ("set", 256-bit int), ("any", None),
    ("anchor", one of ^ $ < > b B ` '), ("ref", 1-9), ("(", None),
    (")", None), ("|", None) or ("dup", (min, max or None)). Bracket
    expressions and intervals are read here, whole: outside brackets a '['
    always opens one and a '{' is an interval or an error wherever it stands
    (parse_dup_op, without RE_INVALID_INTERVAL_ORD), so reading them before the
    structure is known changes no verdict. Raises EreError.
    """
    data = _encode(pattern)
    tokens: list[tuple[str, object]] = []
    i = 0
    while i < len(data):
        c, i = data[i], i + 1
        if c == 0x5C:
            if i == len(data):
                raise EreError("trailing backslash")
            c, i = data[i], i + 1
            tokens.append(("ref", c - 0x30) if 0x31 <= c <= 0x39 else _ESCAPES.get(c, ("lit", c)))
        elif c == 0x5B:
            mask, i = _bracket(data, i)
            tokens.append(("set", mask))
        elif c == 0x7B:
            bounds, i = _interval(data, i)
            tokens.append(("dup", bounds))
        else:
            tokens.append(_PLAIN.get(c, ("lit", c)))
    return tokens


def _number(data: bytes, i: int) -> tuple[int, int, int]:
    """glibc's fetch_number: (value, index past the stop, the stop byte '}' or ',').

    The value is -1 without digits and -2 after anything else. Each token
    counts: an escaped byte is one, \\0 is a digit and \\, a comma.
    """
    num = -1
    while True:
        if i >= len(data) or (data[i] == 0x5C and i + 1 == len(data)):
            raise EreError("unterminated interval")
        c, escaped = (data[i + 1], True) if data[i] == 0x5C else (data[i], False)
        i += 1 + escaped
        if c == 0x2C or (c == 0x7D and not escaped):
            return num, i, c
        digit = c == 0x30 if escaped else 0x30 <= c <= 0x39
        num = -2 if not digit or num == -2 else min(RE_DUP_MAX + 1, max(num, 0) * 10 + c - 0x30)


def _interval(data: bytes, i: int) -> tuple[tuple[int, int | None], int]:
    """parse_dup_op on "{m}", "{m,}", "{,n}" and "{m,n}"; i is past the '{'."""
    lo, i, stop = _number(data, i)
    if lo == -1 and stop == 0x2C:
        lo = 0
    hi = lo
    if stop == 0x2C:
        hi, i, stop = _number(data, i)
    if lo < 0 or hi == -2 or stop != 0x7D or (hi != -1 and lo > hi):
        raise EreError("invalid interval")
    if max(lo, hi) > RE_DUP_MAX:
        raise EreError("interval over RE_DUP_MAX")
    return (lo, None if hi == -1 else hi), i


def _bracket(data: bytes, i: int) -> tuple[int, int]:
    """parse_bracket_exp in the C locale; i is past the '['. Returns (byte set, index past ']').

    A backslash is literal here. Without REG_NEWLINE a non-matching list
    matches a newline.
    """
    negate = data[i:i + 1] == b"^"
    i += negate
    mask, first = 0, True
    while True:
        elem, i = _element(data, i, first)
        first = False
        if elem[0] in ("class", "equiv") or data[i:i + 1] != b"-" or data[i + 1:i + 2] == b"]":
            mask |= _single(elem)
        else:
            end, i = _element(data, i + 1, True)
            lo, hi = _endpoint(elem), _endpoint(end)
            if lo > hi:
                raise EreError("reversed range")
            mask |= _span(lo, hi)
        if i >= len(data):
            raise EreError("unterminated [")
        if data[i] == 0x5D:
            return (mask ^ _ALL if negate else mask), i + 1


def _element(data: bytes, i: int, first: bool) -> tuple[tuple[str, object], int]:
    """parse_bracket_element: ("char", byte), or ("coll" | "equiv" | "class", name)."""
    if i >= len(data):
        raise EreError("unterminated [")
    c = data[i]
    if c == 0x5B and data[i + 1:i + 2] in (b".", b"=", b":"):
        delim = data[i + 1]
        end = data.find(bytes((delim, 0x5D)), i + 2)
        if end < 0:
            raise EreError("unterminated [")
        return (_SYMBOLS[delim], data[i + 2:end]), end + 2
    if c == 0x2D and not first and data[i + 1:i + 2] != b"]":
        raise EreError("'-' starts a range after a range or a class")
    return ("char", c), i + 1


def _single(elem: tuple[str, object]) -> int:
    kind, value = elem
    if kind == "char":
        return 1 << value
    if kind == "class":
        name = value.decode("latin-1")
        if name not in _CLASSES:
            raise EreError(f"unknown class [:{name}:]")
        return _CLASSES[name]
    if len(value) != 1:
        raise EreError("multi-character collating element")
    return 1 << value[0]


def _endpoint(elem: tuple[str, object]) -> int:
    kind, value = elem
    if kind == "char":
        return value
    if kind == "coll" and len(value) == 1:
        return value[0]
    raise EreError("a class or a multi-character element as a range endpoint")


def _encode(text: str) -> bytes:
    """UTF-8 that never raises: surrogateescape, so captures round-trip, else surrogatepass."""
    try:
        return text.encode("utf-8", "surrogateescape")
    except UnicodeEncodeError:
        return text.encode("utf-8", "surrogatepass")


class _Parser:
    """glibc's parse_reg_exp, parse_branch and parse_expression, over tokens, to a tree."""

    def __init__(self, tokens: list[tuple[str, object]]):
        self.tokens = tokens + [("end", None)]
        self.pos = self.groups = 0
        self.closed: set[int] = set()  # completed_bkref_map: the groups \1-\9 may name

    def stops(self, depth: int) -> bool:
        kind = self.tokens[self.pos][0]
        return kind in ("|", "end") or (kind == ")" and depth > 0)

    def regexp(self, depth: int) -> tuple:
        """Branches; each starts from the groups closed before the first, so `(a)|\\1` is invalid."""
        before = set(self.closed)
        branches = [self.branch(depth)]
        while self.tokens[self.pos][0] == "|":
            self.pos += 1
            after, self.closed = self.closed, set(before)
            branches.append(self.branch(depth))
            self.closed |= after
        return ("alt", branches)

    def branch(self, depth: int) -> tuple:
        items = []
        while not self.stops(depth):
            items.append(self.expression(depth))
        return ("cat", items)

    def expression(self, depth: int) -> tuple:
        """One atom and the quantifiers after it; a ')' reaches here only at depth 0."""
        kind, value = self.tokens[self.pos]
        self.pos += 1
        if kind == "dup":
            raise EreError("a quantifier with nothing to repeat")
        if kind == "anchor":
            return (kind, value)  # glibc returns before the quantifier loop: "^*" is invalid
        if kind == "(":
            self.groups += 1
            number, inner = self.groups, self.regexp(depth + 1)
            if self.tokens[self.pos][0] != ")":
                raise EreError("unmatched (")
            self.pos += 1
            if number <= 9:
                self.closed.add(number)
            node: tuple = ("group", number, inner)
        elif kind == "ref" and value not in self.closed:
            raise EreError(f"\\{value} names an open or absent group")
        else:
            node = ("lit", 0x29) if kind == ")" else (kind, value)
        while self.tokens[self.pos][0] == "dup":
            bounds = self.tokens[self.pos][1]
            merged = _merge(node[2], bounds) if node[0] == "dup" else None
            node = ("dup", node, bounds) if merged is None else ("dup", node[1], merged)
            self.pos += 1
        return node


def _merge(inner: tuple[int, int | None], outer: tuple[int, int | None]) -> tuple[int, int | None] | None:
    """A *, + or ? under another repeat as one: x+{2} is x{2,}, x?{3} is x{0,3}, x*** is x*.

    Nested, as (?:(?:x*)*)*, Python backtracks through every split of a run,
    which doubles with each byte. None for any other inner repeat: x{2}* is
    not one interval.
    """
    if inner not in ((0, None), (1, None), (0, 1)):
        return None
    if outer[1] == 0:
        return 0, 0
    return inner[0] * outer[0], None if inner[1] is None else outer[1]


_W = "[0-9A-Z_a-z]"
# No REG_NEWLINE: ^ and $ hold only at the ends of the subject, and $ not before a final newline.
# \B is spelled out: Python before 3.14 does not match it on "", glibc does.
_ANCHORS = {"^": r"\A", "$": r"\Z", "`": r"\A", "'": r"\Z", "b": r"\b",
            "<": f"(?<!{_W})(?={_W})", ">": f"(?<={_W})(?!{_W})",
            "B": f"(?:(?<={_W})(?={_W})|(?<!{_W})(?!{_W}))"}


def _emit(node: tuple) -> str:
    kind = node[0]
    if kind in ("alt", "cat"):
        return ("|" if kind == "alt" else "").join(_emit(item) for item in node[1])
    if kind == "group":
        return f"({_emit(node[2])})"
    if kind == "dup":
        inner = _emit(node[1])
        if node[1][0] == "dup":  # POSIX has no lazy or possessive form: a{2}? is (a{2})?
            inner = f"(?:{inner})"
        return inner + _quantifier(*node[2])
    if kind == "ref":
        return f"(?:\\{node[1]})"  # so that \1 then 2 never reads as \12
    if kind == "anchor":
        return _ANCHORS[node[1]]
    if kind == "any":
        return "."
    if kind == "set":
        return _class(node[1])
    return re.escape(chr(node[1])) if 0x20 <= node[1] < 0x7F else f"\\x{node[1]:02x}"


def _quantifier(lo: int, hi: int | None) -> str:
    if hi is None:
        return {0: "*", 1: "+"}.get(lo, f"{{{lo},}}")
    if (lo, hi) == (0, 1):
        return "?"
    return f"{{{lo}}}" if lo == hi else f"{{{lo},{hi}}}"


def _class(mask: int) -> str:
    """A byte set as [...] of ranges, or [^...] of its complement when that is smaller."""
    negate = bin(mask).count("1") > 128
    mask ^= _ALL if negate else 0
    if not mask:
        return r"[\x00-\xff]" if negate else r"[^\x00-\xff]"
    parts, c = [], 0
    while c < 256:
        if mask >> c & 1:
            end = c
            while end < 255 and mask >> (end + 1) & 1:
                end += 1
            parts.append(_byte(c) if end == c else f"{_byte(c)}-{_byte(end)}")
            c = end
        c += 1
    return "[" + "^" * negate + "".join(parts) + "]"


def _byte(c: int) -> str:
    return chr(c) if chr(c).isascii() and (chr(c).isalnum() or c == 0x5F) else f"\\x{c:02x}"


def translate(pattern: str) -> str:
    """The Python regex, over bytes with re.DOTALL, for a glibc ERE. Raises EreError where regcomp fails."""
    return _emit(_Parser(tokenize(pattern)).regexp(0))


class Ere:
    """A pattern glibc accepts, compiled. The subject is matched as its UTF-8 bytes."""

    __slots__ = ("source", "_rx")

    def __init__(self, source: str, rx: re.Pattern[bytes]):
        self.source, self._rx = source, rx

    def search(self, line: str) -> bool:
        """Whether [[ $line =~ $source ]] answers 0."""
        return self._rx.search(_encode(line)) is not None

    def captures(self, line: str) -> tuple[str | None, ...] | None:
        """The groups of the match, None for a group that took no part; None without a match.

        Python's match is leftmost-first and glibc's leftmost-longest, so a
        capture can differ where the decision cannot (D3).
        """
        found = self._rx.search(_encode(line))
        if found is None:
            return None
        return tuple(None if g is None else g.decode("utf-8", "surrogateescape") for g in found.groups())


_CACHE: dict[str, Ere | None] = {}


def compile(pattern: str) -> Ere | None:  # pylint: disable=redefined-builtin
    """The pattern compiled, or None, which never matches, where glibc's regcomp fails. Cached per process.

    A re.error from a translation the parser accepted also gives None; the
    engine differential then shows it as a divergence. So does a pattern
    nested deeper than Python's recursion limit, which glibc accepts; that
    None depends on the caller's stack depth, so it is not cached.
    """
    if pattern not in _CACHE:
        try:
            rx = re.compile(translate(pattern).encode("ascii"), re.DOTALL)
        except (EreError, re.error):
            rx = None
        except RecursionError:
            return None
        _CACHE[pattern] = None if rx is None else Ere(pattern, rx)
    return _CACHE[pattern]
