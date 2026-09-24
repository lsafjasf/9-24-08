"""URL 解析、相对引用解析与规范化库（RFC 3986），仅使用标准库。

明确不调用任何运行时的 URL 解析能力（不使用 urllib.parse 等）。
ipaddress 仅用于校验/规范化 IPv6 字面量，属于 IP 地址库而非 URL 解析。

处理规则（明确约定）：
- 输入中不允许出现空格、控制字符（<0x20）与 DEL（0x7F），否则报错并给出位置。
- 每个 '%' 后必须紧跟两个十六进制字符，否则报错并给出在原串中的位置；绝不默默修正。
- 协议（scheme）须匹配 [A-Za-z][A-Za-z0-9+.-]* 且后跟 ':'，否则整体视为路径。
- 授权部分（authority）为 '//' 之后到下一个 '/' 之间的内容：
  [userinfo "@"] host [":" port]。多个 '@' 时以最后一个分隔。
- IPv6 / IPvFuture 字面量必须用 '[' ']' 包裹；裸主机中出现多个 ':' 视为非法。
- 端口：省略（无 ':'）与显式写默认端口（如 http 的 ':80'）在解析结果中可区分；
  ':' 后为空视为省略；端口必须是 0-65535 的数字。
- 空主机允许（如 file:///path）。
- 点段消解严格按 RFC 3986 5.2.4，绝不会弹出根之上（多余的 '..' 被丢弃）。
- 相对引用解析按 RFC 3986 5.2.2 严格模式（ref 自带 scheme 时整体采用 ref）。
- 规范化：scheme/host 小写、IPv6 压缩形式、省略 scheme 默认端口、点段消解、
  百分号编码统一为大写（不解码、不新增编码）。规范化幂等。
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass

__all__ = [
    "URL",
    "URLParseError",
    "EscapesBaseError",
    "parse",
    "serialize",
    "normalize",
    "resolve",
    "resolve_safe",
    "remove_dot_segments",
    "DEFAULT_PORTS",
]

DEFAULT_PORTS = {
    "http": 80,
    "https": 443,
    "ftp": 21,
    "ws": 80,
    "wss": 443,
    "gopher": 70,
}

_SCHEME_RE = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*):")
_PCT_RE = re.compile(r"%([0-9A-Fa-f]{2})")
_IPVFUTURE_RE = re.compile(r"^v[0-9A-Fa-f]+\.[A-Za-z0-9._~!$&'()*+,;=:-]+$")
_HOST_FORBIDDEN = re.compile(r"[/?#\[\]@]")
_HEX = "0123456789abcdefABCDEF"


class URLParseError(ValueError):
    """URL 解析错误。position 为在原始输入串中的下标（可为 None）。"""

    def __init__(self, message: str, position: int | None = None):
        self.position = position
        if position is not None:
            message = "%s (position %d)" % (message, position)
        super().__init__(message)


class EscapesBaseError(URLParseError):
    """相对引用解析结果越出基准目录允许范围。"""


@dataclass(frozen=True)
class URL:
    """解析结果。port 为 None 表示省略；query/fragment 为 None 表示不存在。"""

    scheme: str | None
    userinfo: str | None
    host: str | None
    port: int | None
    path: str
    query: str | None
    fragment: str | None
    has_authority: bool = False

    @property
    def port_is_explicit_default(self) -> bool:
        """显式写出了该 scheme 的默认端口（如 http://a:80/）。"""
        return (
            self.scheme is not None
            and self.port is not None
            and DEFAULT_PORTS.get(self.scheme.lower()) == self.port
        )

    def __str__(self) -> str:  # pragma: no cover - 便捷方法
        return serialize(self)


def _validate_chars(url: str) -> None:
    for i, ch in enumerate(url):
        code = ord(ch)
        if code <= 0x20 or code == 0x7F:
            raise URLParseError(
                "illegal control/whitespace character U+%04X" % code, i
            )


def _validate_percent(url: str) -> None:
    i = url.find("%")
    while i != -1:
        if i + 2 >= len(url) or url[i + 1] not in _HEX or url[i + 2] not in _HEX:
            bad = url[i : i + 3]
            raise URLParseError("invalid percent-encoding %r" % bad, i)
        i = url.find("%", i + 3)


def _parse_port(text: str) -> int | None:
    if text == "":
        return None  # 规则：':' 后为空视为省略
    if not text.isdigit():
        raise URLParseError("port must be digits, got %r" % text)
    value = int(text)
    if value > 65535:
        raise URLParseError("port out of range (0-65535): %d" % value)
    return value


def _validate_ip_literal(host: str) -> None:
    if host[:1].lower() == "v" and _IPVFUTURE_RE.match(host):
        return
    try:
        ipaddress.IPv6Address(host)
    except ValueError:
        raise URLParseError("invalid IPv6/IPvFuture literal %r" % host) from None


def _parse_authority(authority: str):
    userinfo = None
    if "@" in authority:
        userinfo, authority = authority.rsplit("@", 1)

    host: str | None
    port: int | None = None
    if authority.startswith("["):
        end = authority.find("]")
        if end == -1:
            raise URLParseError("unterminated '[' in IP literal")
        host = authority[1:end]
        _validate_ip_literal(host)
        rest = authority[end + 1 :]
        if rest:
            if not rest.startswith(":"):
                raise URLParseError("unexpected %r after ']'" % rest)
            port = _parse_port(rest[1:])
    else:
        if authority.count(":") > 1:
            raise URLParseError("IPv6 literal must be enclosed in '[' and ']'")
        if ":" in authority:
            host, _, port_text = authority.partition(":")
            port = _parse_port(port_text)
        else:
            host = authority

    if host is not None and _HOST_FORBIDDEN.search(host):
        raise URLParseError("illegal character in host %r" % host)
    return userinfo, host, port


def parse(url: str) -> URL:
    """把 URL/相对引用解析为 URL 结构；非法输入抛 URLParseError。"""
    if not isinstance(url, str):
        raise TypeError("url must be str, got %s" % type(url).__name__)
    _validate_chars(url)
    _validate_percent(url)

    fragment = None
    i = url.find("#")
    if i != -1:
        fragment = url[i + 1 :]
        url = url[:i]

    query = None
    i = url.find("?")
    if i != -1:
        query = url[i + 1 :]
        url = url[:i]

    scheme = None
    m = _SCHEME_RE.match(url)
    if m:
        scheme = m.group(1)
        url = url[m.end() :]

    has_authority = False
    userinfo = host = None
    port = None
    if url.startswith("//"):
        has_authority = True
        rest = url[2:]
        j = rest.find("/")
        if j == -1:
            authority, url = rest, ""
        else:
            authority, url = rest[:j], rest[j:]
        userinfo, host, port = _parse_authority(authority)

    return URL(
        scheme=scheme,
        userinfo=userinfo,
        host=host,
        port=port,
        path=url,
        query=query,
        fragment=fragment,
        has_authority=has_authority,
    )


def serialize(u: URL) -> str:
    parts = []
    if u.scheme is not None:
        parts.append(u.scheme + ":")
    if u.has_authority:
        parts.append("//")
        if u.userinfo is not None:
            parts.append(u.userinfo + "@")
        host = u.host or ""
        if ":" in host:  # IPv6/IPvFuture 字面量
            parts.append("[" + host + "]")
        else:
            parts.append(host)
        if u.port is not None:
            parts.append(":" + str(u.port))
    parts.append(u.path)
    if u.query is not None:
        parts.append("?" + u.query)
    if u.fragment is not None:
        parts.append("#" + u.fragment)
    return "".join(parts)


def remove_dot_segments(path: str) -> str:
    """RFC 3986 5.2.4。多余的 '..' 直接丢弃，不会弹出根之上。"""
    inp = path
    out = ""
    while inp:
        if inp.startswith("../"):
            inp = inp[3:]
        elif inp.startswith("./"):
            inp = inp[2:]
        elif inp.startswith("/./"):
            inp = "/" + inp[3:]
        elif inp == "/.":
            inp = "/"
        elif inp.startswith("/../"):
            inp = "/" + inp[4:]
            out = out[: out.rfind("/")] if "/" in out else ""
        elif inp == "/..":
            inp = "/"
            out = out[: out.rfind("/")] if "/" in out else ""
        elif inp in (".", ".."):
            inp = ""
        else:
            if inp.startswith("/"):
                j = inp.find("/", 1)
            else:
                j = inp.find("/")
            if j == -1:
                out += inp
                inp = ""
            else:
                out += inp[:j]
                inp = inp[j:]
    return out


def _upper_pct(text: str | None) -> str | None:
    if text is None:
        return None
    return _PCT_RE.sub(lambda m: "%" + m.group(1).upper(), text)


def _normalize_host(host: str | None) -> str | None:
    if host is None:
        return None
    host = host.lower()
    try:
        return ipaddress.IPv6Address(host).compressed
    except ValueError:
        return host


def normalize(url) -> URL:
    """规范化，幂等：normalize(normalize(u)) == normalize(u)。"""
    u = parse(url) if isinstance(url, str) else url
    scheme = u.scheme.lower() if u.scheme is not None else None
    port = u.port
    if scheme is not None and port is not None and DEFAULT_PORTS.get(scheme) == port:
        port = None
    return URL(
        scheme=scheme,
        userinfo=_upper_pct(u.userinfo),
        host=_normalize_host(u.host),
        port=port,
        path=_upper_pct(remove_dot_segments(u.path)),
        query=_upper_pct(u.query),
        fragment=_upper_pct(u.fragment),
        has_authority=u.has_authority,
    )


def _merge(base: URL, ref_path: str) -> str:
    if base.has_authority and base.path == "":
        return "/" + ref_path
    i = base.path.rfind("/")
    return base.path[: i + 1] + ref_path


def resolve(base, ref) -> URL:
    """RFC 3986 5.2.2 严格模式相对引用解析。参数可为 str 或 URL。"""
    b = parse(base) if isinstance(base, str) else base
    r = parse(ref) if isinstance(ref, str) else ref

    if r.scheme is not None:
        t_scheme, t_userinfo, t_host, t_port, t_auth = (
            r.scheme, r.userinfo, r.host, r.port, r.has_authority,
        )
        t_path = remove_dot_segments(r.path)
        t_query = r.query
    else:
        if r.has_authority:
            t_userinfo, t_host, t_port, t_auth = (
                r.userinfo, r.host, r.port, True,
            )
            t_path = remove_dot_segments(r.path)
            t_query = r.query
        else:
            if r.path == "":
                t_path = b.path
                t_query = r.query if r.query is not None else b.query
            else:
                if r.path.startswith("/"):
                    t_path = remove_dot_segments(r.path)
                else:
                    t_path = remove_dot_segments(_merge(b, r.path))
                t_query = r.query
            t_userinfo, t_host, t_port, t_auth = (
                b.userinfo, b.host, b.port, b.has_authority,
            )
        t_scheme = b.scheme

    return URL(
        scheme=t_scheme,
        userinfo=t_userinfo,
        host=t_host,
        port=t_port,
        path=t_path,
        query=t_query,
        fragment=r.fragment,
        has_authority=t_auth,
    )


def resolve_safe(base, ref) -> URL:
    """受限解析：结果必须留在基准目录允许范围内，否则抛 EscapesBaseError。

    规则：
    - 不允许跨 scheme（如基准 http，引用 https:...）；
    - 不允许跨授权（host/port/userinfo 必须一致，'//other/x' 会被拒绝）；
    - 规范化后的结果路径必须位于基准路径所在目录（含）之下。
    返回规范化后的 URL。
    """
    b = normalize(base if isinstance(base, str) else serialize(base))
    r = parse(ref) if isinstance(ref, str) else ref

    if r.scheme is not None and r.scheme.lower() != (b.scheme or ""):
        raise EscapesBaseError(
            "cross-scheme reference %r not allowed (base scheme %r)"
            % (r.scheme, b.scheme)
        )

    result = normalize(resolve(b, r))

    if (result.host, result.port, result.userinfo) != (b.host, b.port, b.userinfo):
        raise EscapesBaseError(
            "reference escapes base authority %r" % (b.host,)
        )

    i = b.path.rfind("/")
    base_dir = b.path[: i + 1] if i != -1 else ""
    if not result.path.startswith(base_dir):
        raise EscapesBaseError(
            "resolved path %r escapes base directory %r" % (result.path, base_dir)
        )
    return result
