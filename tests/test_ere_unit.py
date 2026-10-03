#!/usr/bin/env python3
"""Unit tests of hooks/lib/ai_ere.py, the ERE translator (spec D3, R6 unit part).

Every expectation here was read from bash 5.3 on glibc 2.43 under LC_ALL=C:
where EreError is expected, `[[ $s =~ $p ]]` answers 2. The engine
differential (test_pattern_differential.py) keeps comparing ai_ere with bash.

    python3 tests/test_ere_unit.py
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hooks", "lib"))
import ai_ere

ALPHA = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def members(pattern: str) -> bytes:
    """The bytes of the one set token the pattern is."""
    tokens = ai_ere.tokenize(pattern)
    assert len(tokens) == 1 and tokens[0][0] == "set", tokens
    mask = tokens[0][1]
    return bytes(b for b in range(256) if mask >> b & 1)


def lits(text: str) -> list[tuple[str, object]]:
    return [("lit", c) for c in text.encode()]


class Brackets(unittest.TestCase):
    def test_members(self):
        cases = {
            "[abc]": b"abc", "[a-c]": b"abc", "[a-a]": b"a", "[]a]": b"]a", "[a-]": b"-a",
            "[-a]": b"-a", "[--]": b"-", "[%--]": b"%&'()*+,-", "[]-a]": b"]^_`a", "[a^]": b"^a",
            "[\\]": b"\\", "[[a]": b"[a", "[[:space:]]": b"\t\n\v\f\r ", "[[:digit:]x]": b"0123456789x",
            "[[:alpha:]-]": b"-" + ALPHA, "[[:alpha:][:digit:]]": b"0123456789" + ALPHA,
            "[[=a=]]": b"a", "[[=a=]-]": b"-a", "[[.-.]]": b"-", "[[.].]]": b"]", "[[...]]": b".",
            "[[=]=]]": b"]", "[[.a.]-c]": b"abc", "[a-[.c.]]": b"abc", "[[.-.]-0]": b"-./0",
            "[é]": b"\xa9\xc3", "\\w": b"0123456789" + ALPHA[:26] + b"_" + ALPHA[26:],
            "\\s": b"\t\n\v\f\r ",
        }
        for pattern, want in cases.items():
            with self.subTest(pattern=pattern):
                self.assertEqual(members(pattern), want)

    def test_classes_are_ascii(self):
        sizes = {"alnum": 62, "alpha": 52, "blank": 2, "cntrl": 33, "digit": 10, "graph": 94,
                 "lower": 26, "print": 95, "punct": 32, "space": 6, "upper": 26, "xdigit": 22}
        for name, size in sizes.items():
            with self.subTest(name=name):
                got = members(f"[[:{name}:]]")
                self.assertEqual((len(got), got.isascii()), (size, True))
        self.assertEqual(members("[[:punct:]]"), b"!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")

    def test_negated(self):
        self.assertEqual(members("[^]a]"), bytes(b for b in range(256) if b not in b"]a"))
        self.assertIn(b"\n", members("[^a]"))
        self.assertEqual(len(members("\\W")), 256 - 63)
        self.assertEqual(len(members("\\S")), 256 - 6)

    def test_rejected(self):
        for pattern in ("[", "[^", "[a", "[]", "[^]", "[a-z", "[a\\", "[[:alpha:]", "[[:alpha", "[[.]",
                        "[z-a]", "[a--]", "[a-c-e]", "[[:alpha:]-z]", "[[=a=]-z]", "[a-[=b=]]",
                        "[a-[:alpha:]]", "[[:foo:]]", "[[::]]", "[[:ALPHA:]]", "[[.space.]]",
                        "[[=ab=]]", "[[..]]", "[[.ab.]-c]"):
            with self.subTest(pattern=pattern), self.assertRaises(ai_ere.EreError):
                ai_ere.tokenize(pattern)


class Tokens(unittest.TestCase):
    def test_tokens(self):
        cases = {
            "a.b": [("lit", 0x61), ("any", None), ("lit", 0x62)],
            "^a$": [("anchor", "^"), ("lit", 0x61), ("anchor", "$")],
            "(a|)": [("(", None), ("lit", 0x61), ("|", None), (")", None)],
            "a*+?": [("lit", 0x61), ("dup", (0, None)), ("dup", (1, None)), ("dup", (0, 1))],
            "\\<\\>\\b\\B\\`\\'": [("anchor", c) for c in "<>bB`'"],
            "\\1\\9": [("ref", 1), ("ref", 9)],
            "\\0\\n\\d\\|\\(\\{\\}\\.\\\\": lits("0nd|({}.\\"),
            "}a}": lits("}a}"),
            "é": [("lit", 0xC3), ("lit", 0xA9)],
        }
        for pattern, want in cases.items():
            with self.subTest(pattern=pattern):
                self.assertEqual(ai_ere.tokenize(pattern), want)

    def test_intervals(self):
        cases = {"a{2}": (2, 2), "a{2,}": (2, None), "a{,3}": (0, 3), "a{,}": (0, None), "a{0}": (0, 0),
                 "a{007}": (7, 7), "a{1\\,2}": (1, 2), "a{1\\0}": (10, 10), "a{\\0}": (0, 0),
                 "a{32767}": (32767, 32767), "a{0,32767}": (0, 32767)}
        for pattern, bounds in cases.items():
            with self.subTest(pattern=pattern):
                self.assertEqual(ai_ere.tokenize(pattern), [("lit", 0x61), ("dup", bounds)])

    def test_rejected(self):
        for pattern in ("a\\", "a{", "a{1", "a{1,", "a{}", "a{x}", "a{ 1}", "a{2,1}", "a{1,2,3}",
                        "a{32768}", "a{0,32768}", "a{99999999999}", "a{1\\}", "a{\\1}", "a{1\\"):
            with self.subTest(pattern=pattern), self.assertRaises(ai_ere.EreError):
                ai_ere.tokenize(pattern)


# (pattern, subject, what bash answers: 0 match, 1 no match, 2 invalid)
VERDICTS = [
    ("a|b", "b", 0), ("(a)(b)\\2", "abb", 0), ("(a)\\12", "aa2", 0), ("(a)\\12", "aa", 1),
    ("((a)|b)\\2", "aa", 0), ("(a)(b|\\1)", "aa", 0), ("(a|(b))\\2", "bb", 0),
    ("((((((((((a))))))))))\\9", "aa", 0), ("(a){0}\\1", "a", 1), ("(a){0}b\\1", "b", 1),
    ("a**", "a", 0), ("a+?", "", 0), ("^a{2}?$", "", 0), ("^a*+a$", "aa", 0), ("a{2}{3}", "aaaaaa", 0),
    ("^a+{2}$", "a", 1), ("^a+{2}$", "aa", 0), ("^a?{3}$", "aaa", 0), ("^a?{3}$", "aaaa", 1),
    ("^a*{0}$", "", 0), ("^a*{0}$", "a", 1), ("^a{2}*$", "aaa", 1),
    ("x{0}", "", 0), ("a{1\\0}", "a" * 10, 0), ("(a*)*", "b", 0), ("()*", "x", 0), ("(^)*", "x", 0),
    ("a)", "a)", 0), (")", ")", 0), ("(a))", "a)", 0), ("()", "x", 0), ("(|a)", "x", 0), ("a|", "", 0),
    ("", "x", 0), ("a^", "a", 1), ("x\\|y", "x|y", 0), ("\\.", "a", 1), ("}", "}", 0),
    ("a$", "a\n", 1), ("^.$", "\n", 0), ("^[^a]$", "\n", 0), ("^$", "", 0),
    ("^.$", "\u00e9", 1), ("^..$", "\u00e9", 0), ("\u00e9?x", "x", 1), ("^[\u00e9]$", "\u00e9", 1),
    ("\\B", "", 0), ("\\B", "a", 1), ("\\B", " ", 0), ("a\\B", "a", 1), ("\\Bb", "ab", 0),
    ("\\b", "", 1), ("a\\b", "a", 0), ("\\<", "", 1), ("\\>", "a", 0), ("\\<a\\>", "a", 0),
    ("\\`a", "a", 0), ("a\\'", "a", 0), ("a\\'", "a\n", 1), ("\\w\\W\\s\\S", "a- x", 0),
    ("*a", "a", 2), ("+a", "a", 2), ("?a", "a", 2), ("{1}a", "a", 2), ("a|*b", "b", 2), ("(*a)", "a", 2),
    ("(+a)", "a", 2), ("(?a)", "a", 2), ("(|{1}a)", "a", 2), ("^*", "x", 2), ("$*", "x", 2),
    ("\\b*", "x", 2), ("\\<+", "x", 2), ("^{1}", "x", 2), ("a\\", "a", 2), ("(", "x", 2),
    ("(a", "a", 2), ("a)(", "a)(", 2), ("(a\\1)", "aa", 2), ("(a)\\2", "aa", 2), ("\\1", "", 2),
    ("(a)|\\1", "a", 2), ("(a)|b\\1", "b", 2), ("[a", "a", 2), ("a{", "a{", 2),
]


class Compile(unittest.TestCase):
    def test_verdicts(self):
        for pattern, subject, want in VERDICTS:
            with self.subTest(pattern=pattern, subject=subject):
                ere = ai_ere.compile(pattern)
                self.assertEqual(2 if ere is None else 0 if ere.search(subject) else 1, want)

    def test_translate(self):
        cases = {"a+?": "a*", "a***b": "a*b", "a+{2}": "a{2,}", "a?{3}": "a{0,3}", "a??": "a?",
                 "a*{0}": "a{0}", "(a)+{0,2}": "(a)*", "a{2}?": "(?:a{2})?", "a{2}{3}": "(?:a{2}){3}",
                 "(a)\\12": "(a)(?:\\1)2", "^a$": "\\Aa\\Z", "a{,2}": "a{0,2}",
                 "[^a]": "[^a]", "\\w": "[0-9A-Z_a-z]", "\\.": "\\.", "\u00e9": "\\xc3\\xa9",
                 "[[:space:]]": "[\\x09-\\x0d\\x20]"}
        for pattern, want in cases.items():
            with self.subTest(pattern=pattern):
                self.assertEqual(ai_ere.translate(pattern), want)
        with self.assertRaises(ai_ere.EreError):
            ai_ere.translate("a|*b")

    def test_captures(self):
        self.assertEqual(ai_ere.compile("(a)|(b)").captures("xb"), (None, "b"))
        self.assertIsNone(ai_ere.compile("x").captures("y"))
        self.assertEqual(ai_ere.compile("(.*)").captures("\udcff\u00e9"), ("\udcff\u00e9",))
        self.assertTrue(ai_ere.compile("a").search("\ud800a"))

    def test_cache(self):
        self.assertIs(ai_ere.compile("a(b)"), ai_ere.compile("a(b)"))
        self.assertEqual(ai_ere.compile("a(b)").source, "a(b)")
        self.assertIsNone(ai_ere.compile("(("))
        self.assertIn("((", ai_ere._CACHE)  # pylint: disable=protected-access

    def test_recursion_is_not_cached(self):
        deep, limit = "(" * 400 + "a" + ")" * 400, sys.getrecursionlimit()
        sys.setrecursionlimit(300)
        try:
            self.assertIsNone(ai_ere.compile(deep))
        finally:
            sys.setrecursionlimit(limit)
        self.assertNotIn(deep, ai_ere._CACHE)  # pylint: disable=protected-access
        sys.setrecursionlimit(max(limit, 5000))
        try:
            self.assertTrue(ai_ere.compile(deep).search("a"))
        finally:
            sys.setrecursionlimit(limit)


if __name__ == "__main__":
    unittest.main()
