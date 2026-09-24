"""urlnorm 自测（标准库 unittest）。运行：python3 -m unittest test_urlnorm -v"""

import json
import os
import unittest

import compare
import urlnorm
from urlnorm import EscapesBaseError, URLParseError

HERE = os.path.dirname(os.path.abspath(__file__))


class TestParse(unittest.TestCase):
    def test_full_url(self):
        u = urlnorm.parse("http://user:pass@Example.COM:8080/a/b?x=1#f")
        self.assertEqual(u.scheme, "http")
        self.assertEqual(u.userinfo, "user:pass")
        self.assertEqual(u.host, "Example.COM")
        self.assertEqual(u.port, 8080)
        self.assertEqual(u.path, "/a/b")
        self.assertEqual(u.query, "x=1")
        self.assertEqual(u.fragment, "f")

    def test_empty_and_fragment_query_only(self):
        self.assertEqual(urlnorm.serialize(urlnorm.parse("")), "")
        u = urlnorm.parse("#only-frag")
        self.assertEqual((u.path, u.query, u.fragment), ("", None, "only-frag"))
        u = urlnorm.parse("?only-query")
        self.assertEqual((u.path, u.query, u.fragment), ("", "only-query", None))

    def test_port_omitted_vs_explicit_default(self):
        omitted = urlnorm.parse("http://a/")
        explicit = urlnorm.parse("http://a:80/")
        self.assertIsNone(omitted.port)
        self.assertEqual(explicit.port, 80)
        self.assertFalse(omitted.port_is_explicit_default)
        self.assertTrue(explicit.port_is_explicit_default)
        self.assertNotEqual(omitted, explicit)  # 解析层可区分

    def test_empty_port_treated_as_omitted(self):
        self.assertIsNone(urlnorm.parse("http://a:/").port)

    def test_ipv6_literal(self):
        u = urlnorm.parse("http://[2001:db8::1]:8080/p")
        self.assertEqual((u.host, u.port), ("2001:db8::1", 8080))
        self.assertEqual(urlnorm.serialize(u), "http://[2001:db8::1]:8080/p")

    def test_invalid_percent_rejected_with_position(self):
        with self.assertRaises(URLParseError) as ctx:
            urlnorm.parse("http://a/%zz")
        self.assertEqual(ctx.exception.position, 9)
        with self.assertRaises(URLParseError) as ctx:
            urlnorm.parse("http://a/pa%2")
        self.assertEqual(ctx.exception.position, 11)
        with self.assertRaises(URLParseError):
            urlnorm.parse("http://a/100%")

    def test_illegal_chars_rejected(self):
        with self.assertRaises(URLParseError):
            urlnorm.parse("http://a b/")
        with self.assertRaises(URLParseError):
            urlnorm.parse("http://a/\t")

    def test_bad_port_and_ipv6(self):
        for bad in ("http://a:xx/", "http://a:99999/", "http://2001:db8::1/",
                    "http://[2001:db8::1", "http://[not-an-ip]/"):
            with self.assertRaises(URLParseError, msg=bad):
                urlnorm.parse(bad)


class TestNormalize(unittest.TestCase):
    def test_lowercase_and_default_port(self):
        n = urlnorm.normalize("HTTP://Example.COM:80/")
        self.assertEqual(urlnorm.serialize(n), "http://example.com/")

    def test_dot_segments_never_above_root(self):
        self.assertEqual(urlnorm.remove_dot_segments("/../../g"), "/g")
        self.assertEqual(urlnorm.remove_dot_segments("../../../../g"), "g")

    def test_percent_uppercase(self):
        n = urlnorm.normalize("http://a/%2f%ab%C3")
        self.assertEqual(n.path, "/%2F%AB%C3")

    def test_ipv6_canonical(self):
        n = urlnorm.normalize("http://[2001:0DB8:0:0:0:0:0:1]/")
        self.assertEqual(urlnorm.serialize(n), "http://[2001:db8::1]/")

    def test_idempotent(self):
        samples = [
            "HTTP://Example.COM:80/a/./b/../c/%2f?Q=%ab#F",
            "http://[2001:0DB8::1]:80/x/../../y",
            "https://a:443/p?q#f",
            "//Host/./a",
            "relative/../path/%7e",
            "",
        ]
        for s in samples:
            once = urlnorm.serialize(urlnorm.normalize(s))
            twice = urlnorm.serialize(urlnorm.normalize(once))
            self.assertEqual(once, twice, msg=s)


class TestResolve(unittest.TestCase):
    BASE = "http://a/b/c/d;p?q"

    def test_rfc3986_samples(self):
        with open(os.path.join(HERE, "fixtures", "cases.json"), encoding="utf-8") as fh:
            cases = json.load(fh)
        for case in cases["resolution_cases"]:
            actual = urlnorm.serialize(urlnorm.resolve(self.BASE, case["ref"]))
            accept = [case["expected"]] + case.get("accept", [])
            self.assertIn(actual, accept, msg=case["ref"])

    def test_cross_protocol_relative(self):
        self.assertEqual(urlnorm.serialize(urlnorm.resolve(self.BASE, "//cdn.x/a")),
                         "http://cdn.x/a")

    def test_long_relative_path(self):
        rel = "/".join("s%04d" % i for i in range(5000))
        out = urlnorm.serialize(urlnorm.resolve("http://a/d/", rel))
        self.assertEqual(out, "http://a/d/" + rel)

    def test_deep_dotdot_stays_in_root(self):
        out = urlnorm.serialize(urlnorm.resolve("http://a/b/c/d", "../" * 10000 + "g"))
        self.assertEqual(out, "http://a/g")


class TestResolveSafe(unittest.TestCase):
    def test_within_base_dir_ok(self):
        out = urlnorm.resolve_safe("http://a/b/c/d", "g")
        self.assertEqual(urlnorm.serialize(out), "http://a/b/c/g")

    def test_escape_via_dotdot_rejected(self):
        with self.assertRaises(EscapesBaseError):
            urlnorm.resolve_safe("http://a/b/c/d", "../g")
        with self.assertRaises(EscapesBaseError):
            urlnorm.resolve_safe("http://a/b/c/d", "../../g")

    def test_cross_authority_rejected(self):
        with self.assertRaises(EscapesBaseError):
            urlnorm.resolve_safe("http://a/b/c/d", "//evil.com/x")

    def test_cross_scheme_rejected(self):
        with self.assertRaises(EscapesBaseError):
            urlnorm.resolve_safe("http://a/b/c/d", "https://a/b/c/g")

    def test_encoded_dotdot_not_decoded(self):
        # %2e%2e 不会被解码成 '..'，因此不视为越权
        out = urlnorm.resolve_safe("http://a/b/c/d", "%2e%2e/g")
        self.assertEqual(urlnorm.serialize(out), "http://a/b/c/%2E%2E/g")


class TestFixtures(unittest.TestCase):
    """直接跑对拍逻辑，要求样例集零差异。"""

    def test_no_diffs(self):
        rc = compare.main([])
        self.assertEqual(rc, 0, "对拍存在差异，详见 REPORT.md")


if __name__ == "__main__":
    unittest.main()
