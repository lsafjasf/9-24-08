# urlnorm — URL 解析与规范化库（纯标准库）

Python 3 实现，不调用任何运行时 URL 解析能力（不使用 `urllib.parse`）。
`ipaddress` 仅用于 IPv6 字面量的校验与规范化。

## 文件

- `urlnorm.py` — 库：解析 / 序列化 / 规范化 / 相对引用解析 / 受限解析
- `fixtures/cases.json` — 标准样例集（含 RFC 3986 §5.4.1/5.4.2 全部相对解析样例）
- `compare.py` — 对拍脚本，生成 `REPORT.md`（对拍报告 + 差异清单）
- `test_urlnorm.py` — 自测（unittest）
- `REPORT.md` — 对拍报告（由 compare.py 生成）

## 运行

```sh
python3 -m unittest test_urlnorm -v   # 自测
python3 compare.py                    # 对拍，生成 REPORT.md；有差异时退出码为 1
```

## API

- `parse(str) -> URL`：解析出 scheme / userinfo / host / port / path / query / fragment。
  `port=None` 表示省略，与显式默认端口（`port_is_explicit_default`）可区分。
- `serialize(URL) -> str`
- `normalize(str|URL) -> URL`：scheme/host 小写、IPv6 压缩、省略默认端口、
  点段消解（不越根）、百分号编码统一大写。幂等。
- `resolve(base, ref) -> URL`：RFC 3986 §5.2.2 严格模式相对引用解析，
  支持跨协议写法（`//host/path`）与任意长度相对路径。
- `resolve_safe(base, ref) -> URL`：结果必须落在基准目录允许范围内
  （同 scheme、同授权、路径不越出基准目录），否则抛 `EscapesBaseError`。

## 错误处理规则

- 非法百分号编码：抛 `URLParseError`，`position` 为在原串中的下标，绝不默默修正。
- 空格 / 控制字符（`<=0x20`、`0x7F`）：拒绝并报位置。
- 端口非数字或 >65535：拒绝。`:` 后为空视为省略。
- IPv6/IPvFuture 字面量必须括在 `[]` 中；裸主机含多个 `:` 视为非法。
- `%2e%2e` 不会被解码成 `..`，因此在受限解析中不构成越权（编码语义保持原样）。
