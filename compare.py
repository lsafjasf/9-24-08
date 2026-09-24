"""对拍脚本：用标准样例集（fixtures/cases.json）逐条比对实现输出，
生成对拍报告 REPORT.md 与差异清单。另含程序生成的超长路径用例。

用法：python3 compare.py [cases.json]   退出码：0 无差异，1 有差异。
"""

from __future__ import annotations

import json
import os
import sys

import urlnorm
from urlnorm import URLParseError

HERE = os.path.dirname(os.path.abspath(__file__))


def _url_to_dict(u: urlnorm.URL) -> dict:
    return {
        "scheme": u.scheme,
        "userinfo": u.userinfo,
        "host": u.host,
        "port": u.port,
        "path": u.path,
        "query": u.query,
        "fragment": u.fragment,
        "has_authority": u.has_authority,
    }


def run_parse_case(case: dict) -> dict:
    """返回 {input, expected, actual, ok, note}。"""
    result = {"input": case["input"], "ok": False, "expected": None, "actual": None, "note": ""}
    try:
        u = urlnorm.parse(case["input"])
        actual = _url_to_dict(u)
    except URLParseError as exc:
        actual = {"error": str(exc)}
    if "error" in case:
        result["expected"] = {"error": case["error"], "position": case.get("position")}
        ok = isinstance(actual, dict) and "error" in actual and case["error"] in actual["error"]
        if ok and "position" in case:
            ok = "(position %d)" % case["position"] in actual["error"]
        result["actual"] = actual
    else:
        result["expected"] = case["expected"]
        result["actual"] = actual
        ok = actual == case["expected"]
    result["ok"] = ok
    return result


def run_normalize_case(case: dict) -> dict:
    actual = urlnorm.serialize(urlnorm.normalize(case["input"]))
    again = urlnorm.serialize(urlnorm.normalize(actual))
    ok = actual == case["expected"] and again == actual
    note = "" if again == actual else "规范化不幂等: %r" % again
    return {"input": case["input"], "expected": case["expected"],
            "actual": actual, "ok": ok, "note": note}


def run_resolution_case(base: str, case: dict) -> dict:
    actual = urlnorm.serialize(urlnorm.resolve(base, case["ref"]))
    accept = case.get("accept", [])
    ok = actual == case["expected"] or actual in accept
    note = case.get("note", "")
    return {"input": "base=%r ref=%r" % (base, case["ref"]),
            "expected": case["expected"], "actual": actual,
            "ok": ok, "note": note}


def run_safe_case(case: dict) -> dict:
    try:
        actual = urlnorm.serialize(urlnorm.resolve_safe(case["base"], case["ref"]))
        err = None
    except URLParseError as exc:
        actual, err = None, str(exc)
    if "error" in case:
        ok = err is not None and case["error"] in err
        actual = err
        expected = "error: " + case["error"]
    else:
        ok = err is None and actual == case["expected"]
        expected = case["expected"]
    return {"input": "base=%r ref=%r" % (case["base"], case["ref"]),
            "expected": expected, "actual": actual, "ok": ok, "note": ""}


def generated_cases() -> list:
    """程序生成的边界用例：超长相对路径、深层 '..'."""
    results = []
    long_rel = "/".join("seg%04d" % i for i in range(5000))
    base = "http://a/d/"
    expected = "http://a/d/" + long_rel
    actual = urlnorm.serialize(urlnorm.resolve(base, long_rel))
    results.append({"input": "base=%r ref=<5000 段相对路径, 长 %d>" % (base, len(long_rel)),
                    "expected": expected[:60] + "...", "actual": actual[:60] + "...",
                    "ok": actual == expected, "note": "超长相对路径"})

    deep = "../" * 10000 + "g"
    expected = "http://a/g"
    actual = urlnorm.serialize(urlnorm.resolve("http://a/b/c/d", deep))
    results.append({"input": "base='http://a/b/c/d' ref='../'*10000+'g'",
                    "expected": expected, "actual": actual,
                    "ok": actual == expected, "note": "深层 .. 不越根"})

    long_abs = "http://a/" + "/".join("x" * 200 for _ in range(500))
    n1 = urlnorm.serialize(urlnorm.normalize(long_abs))
    n2 = urlnorm.serialize(urlnorm.normalize(n1))
    results.append({"input": "<超长绝对路径, 长 %d>" % len(long_abs),
                    "expected": "幂等", "actual": "幂等" if n1 == n2 else "不幂等",
                    "ok": n1 == n2, "note": "超长路径规范化幂等"})
    return results


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    cases_path = argv[0] if argv else os.path.join(HERE, "fixtures", "cases.json")
    with open(cases_path, encoding="utf-8") as fh:
        cases = json.load(fh)

    sections = []
    sections.append(("解析用例", [run_parse_case(c) for c in cases["parse_cases"]]))
    sections.append(("规范化用例", [run_normalize_case(c) for c in cases["normalize_cases"]]))
    base = cases["resolution_base"]
    sections.append(("相对引用解析用例 (base=%s)" % base,
                     [run_resolution_case(base, c) for c in cases["resolution_cases"]]))
    sections.append(("受限解析用例（越权检测）", [run_safe_case(c) for c in cases["safe_resolve_cases"]]))
    sections.append(("生成的边界用例", generated_cases()))

    lines = ["# 对拍报告", ""]
    diffs = []
    total = 0
    for title, results in sections:
        passed = sum(1 for r in results if r["ok"])
        total += len(results)
        lines.append("## %s（%d/%d 通过）" % (title, passed, len(results)))
        lines.append("")
        lines.append("| # | 输入 | 期望 | 实际 | 结果 |")
        lines.append("|---|------|------|------|------|")
        for idx, r in enumerate(results, 1):
            status = "PASS" if r["ok"] else "**DIFF**"
            exp = json.dumps(r["expected"], ensure_ascii=False)
            act = json.dumps(r["actual"], ensure_ascii=False)
            lines.append("| %d | `%s` | `%s` | `%s` | %s |"
                         % (idx, r["input"].replace("|", "\\|"),
                            exp.replace("|", "\\|"), act.replace("|", "\\|"), status))
            if not r["ok"]:
                diffs.append((title, idx, r))
        lines.append("")

    lines.append("## 差异清单")
    lines.append("")
    if not diffs:
        lines.append("无差异：全部 %d 条用例与期望一致。" % total)
    else:
        for title, idx, r in diffs:
            lines.append("- [%s #%d] 输入 `%s`" % (title, idx, r["input"]))
            lines.append("  - 期望: `%s`" % json.dumps(r["expected"], ensure_ascii=False))
            lines.append("  - 实际: `%s`" % json.dumps(r["actual"], ensure_ascii=False))
            if r["note"]:
                lines.append("  - 备注: %s" % r["note"])
    lines.append("")

    report = "\n".join(lines)
    report_path = os.path.join(HERE, "REPORT.md")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(report)

    n_diff = len(diffs)
    print("共用例 %d 条，通过 %d 条，差异 %d 条。报告: %s" % (total, total - n_diff, n_diff, report_path))
    return 1 if n_diff else 0


if __name__ == "__main__":
    sys.exit(main())
