# 对拍报告

## 解析用例（18/18 通过）

| # | 输入 | 期望 | 实际 | 结果 |
|---|------|------|------|------|
| 1 | `http://user:pass@Example.COM:8080/a/b/../c?x=1#F` | `{"scheme": "http", "userinfo": "user:pass", "host": "Example.COM", "port": 8080, "path": "/a/b/../c", "query": "x=1", "fragment": "F", "has_authority": true}` | `{"scheme": "http", "userinfo": "user:pass", "host": "Example.COM", "port": 8080, "path": "/a/b/../c", "query": "x=1", "fragment": "F", "has_authority": true}` | PASS |
| 2 | `` | `{"scheme": null, "userinfo": null, "host": null, "port": null, "path": "", "query": null, "fragment": null, "has_authority": false}` | `{"scheme": null, "userinfo": null, "host": null, "port": null, "path": "", "query": null, "fragment": null, "has_authority": false}` | PASS |
| 3 | `#frag` | `{"scheme": null, "userinfo": null, "host": null, "port": null, "path": "", "query": null, "fragment": "frag", "has_authority": false}` | `{"scheme": null, "userinfo": null, "host": null, "port": null, "path": "", "query": null, "fragment": "frag", "has_authority": false}` | PASS |
| 4 | `?q=1` | `{"scheme": null, "userinfo": null, "host": null, "port": null, "path": "", "query": "q=1", "fragment": null, "has_authority": false}` | `{"scheme": null, "userinfo": null, "host": null, "port": null, "path": "", "query": "q=1", "fragment": null, "has_authority": false}` | PASS |
| 5 | `//host/path` | `{"scheme": null, "userinfo": null, "host": "host", "port": null, "path": "/path", "query": null, "fragment": null, "has_authority": true}` | `{"scheme": null, "userinfo": null, "host": "host", "port": null, "path": "/path", "query": null, "fragment": null, "has_authority": true}` | PASS |
| 6 | `http://[2001:db8::1]:8080/p` | `{"scheme": "http", "userinfo": null, "host": "2001:db8::1", "port": 8080, "path": "/p", "query": null, "fragment": null, "has_authority": true}` | `{"scheme": "http", "userinfo": null, "host": "2001:db8::1", "port": 8080, "path": "/p", "query": null, "fragment": null, "has_authority": true}` | PASS |
| 7 | `http://[vF.abc]/` | `{"scheme": "http", "userinfo": null, "host": "vF.abc", "port": null, "path": "/", "query": null, "fragment": null, "has_authority": true}` | `{"scheme": "http", "userinfo": null, "host": "vF.abc", "port": null, "path": "/", "query": null, "fragment": null, "has_authority": true}` | PASS |
| 8 | `mailto:user@example.com` | `{"scheme": "mailto", "userinfo": null, "host": null, "port": null, "path": "user@example.com", "query": null, "fragment": null, "has_authority": false}` | `{"scheme": "mailto", "userinfo": null, "host": null, "port": null, "path": "user@example.com", "query": null, "fragment": null, "has_authority": false}` | PASS |
| 9 | `http://host:80/` | `{"scheme": "http", "userinfo": null, "host": "host", "port": 80, "path": "/", "query": null, "fragment": null, "has_authority": true}` | `{"scheme": "http", "userinfo": null, "host": "host", "port": 80, "path": "/", "query": null, "fragment": null, "has_authority": true}` | PASS |
| 10 | `http://host/` | `{"scheme": "http", "userinfo": null, "host": "host", "port": null, "path": "/", "query": null, "fragment": null, "has_authority": true}` | `{"scheme": "http", "userinfo": null, "host": "host", "port": null, "path": "/", "query": null, "fragment": null, "has_authority": true}` | PASS |
| 11 | `file:///etc/passwd` | `{"scheme": "file", "userinfo": null, "host": "", "port": null, "path": "/etc/passwd", "query": null, "fragment": null, "has_authority": true}` | `{"scheme": "file", "userinfo": null, "host": "", "port": null, "path": "/etc/passwd", "query": null, "fragment": null, "has_authority": true}` | PASS |
| 12 | `http://a/%zz` | `{"error": "invalid percent-encoding", "position": 9}` | `{"error": "invalid percent-encoding '%zz' (position 9)"}` | PASS |
| 13 | `http://a/%2` | `{"error": "invalid percent-encoding", "position": 9}` | `{"error": "invalid percent-encoding '%2' (position 9)"}` | PASS |
| 14 | `http://a b/` | `{"error": "illegal control/whitespace character", "position": 8}` | `{"error": "illegal control/whitespace character U+0020 (position 8)"}` | PASS |
| 15 | `http://[2001:db8::1` | `{"error": "unterminated '['", "position": null}` | `{"error": "unterminated '[' in IP literal"}` | PASS |
| 16 | `http://a:99999/` | `{"error": "port out of range", "position": null}` | `{"error": "port out of range (0-65535): 99999"}` | PASS |
| 17 | `http://a:xx/` | `{"error": "port must be digits", "position": null}` | `{"error": "port must be digits, got 'xx'"}` | PASS |
| 18 | `http://2001:db8::1/` | `{"error": "IPv6 literal must be enclosed", "position": null}` | `{"error": "IPv6 literal must be enclosed in '[' and ']'"}` | PASS |

## 规范化用例（7/7 通过）

| # | 输入 | 期望 | 实际 | 结果 |
|---|------|------|------|------|
| 1 | `HTTP://Example.COM:80/a/./b/../c/%2f%ab` | `"http://example.com/a/c/%2F%AB"` | `"http://example.com/a/c/%2F%AB"` | PASS |
| 2 | `http://a/../../g` | `"http://a/g"` | `"http://a/g"` | PASS |
| 3 | `HTTPS://ExAmple.com:443/` | `"https://example.com/"` | `"https://example.com/"` | PASS |
| 4 | `http://[2001:0DB8:0000:0000:0000:0000:0000:0001]/p` | `"http://[2001:db8::1]/p"` | `"http://[2001:db8::1]/p"` | PASS |
| 5 | `http://a/b/c/%7euser?Q=%2f#%Ab` | `"http://a/b/c/%7Euser?Q=%2F#%AB"` | `"http://a/b/c/%7Euser?Q=%2F#%AB"` | PASS |
| 6 | `http://a:8080/` | `"http://a:8080/"` | `"http://a:8080/"` | PASS |
| 7 | `//EXAMPLE.com/./a` | `"//example.com/a"` | `"//example.com/a"` | PASS |

## 相对引用解析用例 (base=http://a/b/c/d;p?q)（39/39 通过）

| # | 输入 | 期望 | 实际 | 结果 |
|---|------|------|------|------|
| 1 | `base='http://a/b/c/d;p?q' ref='g:h'` | `"g:h"` | `"g:h"` | PASS |
| 2 | `base='http://a/b/c/d;p?q' ref='g'` | `"http://a/b/c/g"` | `"http://a/b/c/g"` | PASS |
| 3 | `base='http://a/b/c/d;p?q' ref='./g'` | `"http://a/b/c/g"` | `"http://a/b/c/g"` | PASS |
| 4 | `base='http://a/b/c/d;p?q' ref='g/'` | `"http://a/b/c/g/"` | `"http://a/b/c/g/"` | PASS |
| 5 | `base='http://a/b/c/d;p?q' ref='/g'` | `"http://a/g"` | `"http://a/g"` | PASS |
| 6 | `base='http://a/b/c/d;p?q' ref='//g'` | `"http://g/"` | `"http://g"` | PASS |
| 7 | `base='http://a/b/c/d;p?q' ref='?y'` | `"http://a/b/c/d;p?y"` | `"http://a/b/c/d;p?y"` | PASS |
| 8 | `base='http://a/b/c/d;p?q' ref='g?y'` | `"http://a/b/c/g?y"` | `"http://a/b/c/g?y"` | PASS |
| 9 | `base='http://a/b/c/d;p?q' ref='#s'` | `"http://a/b/c/d;p?q#s"` | `"http://a/b/c/d;p?q#s"` | PASS |
| 10 | `base='http://a/b/c/d;p?q' ref='g#s'` | `"http://a/b/c/g#s"` | `"http://a/b/c/g#s"` | PASS |
| 11 | `base='http://a/b/c/d;p?q' ref='g?y#s'` | `"http://a/b/c/g?y#s"` | `"http://a/b/c/g?y#s"` | PASS |
| 12 | `base='http://a/b/c/d;p?q' ref=';x'` | `"http://a/b/c/;x"` | `"http://a/b/c/;x"` | PASS |
| 13 | `base='http://a/b/c/d;p?q' ref='g;x'` | `"http://a/b/c/g;x"` | `"http://a/b/c/g;x"` | PASS |
| 14 | `base='http://a/b/c/d;p?q' ref='g;x?y#s'` | `"http://a/b/c/g;x?y#s"` | `"http://a/b/c/g;x?y#s"` | PASS |
| 15 | `base='http://a/b/c/d;p?q' ref=''` | `"http://a/b/c/d;p?q"` | `"http://a/b/c/d;p?q"` | PASS |
| 16 | `base='http://a/b/c/d;p?q' ref='.'` | `"http://a/b/c/"` | `"http://a/b/c/"` | PASS |
| 17 | `base='http://a/b/c/d;p?q' ref='./'` | `"http://a/b/c/"` | `"http://a/b/c/"` | PASS |
| 18 | `base='http://a/b/c/d;p?q' ref='..'` | `"http://a/b/"` | `"http://a/b/"` | PASS |
| 19 | `base='http://a/b/c/d;p?q' ref='../'` | `"http://a/b/"` | `"http://a/b/"` | PASS |
| 20 | `base='http://a/b/c/d;p?q' ref='../g'` | `"http://a/b/g"` | `"http://a/b/g"` | PASS |
| 21 | `base='http://a/b/c/d;p?q' ref='../..'` | `"http://a/"` | `"http://a/"` | PASS |
| 22 | `base='http://a/b/c/d;p?q' ref='../../'` | `"http://a/"` | `"http://a/"` | PASS |
| 23 | `base='http://a/b/c/d;p?q' ref='../../g'` | `"http://a/g"` | `"http://a/g"` | PASS |
| 24 | `base='http://a/b/c/d;p?q' ref='../../../g'` | `"http://a/g"` | `"http://a/g"` | PASS |
| 25 | `base='http://a/b/c/d;p?q' ref='../../../../g'` | `"http://a/g"` | `"http://a/g"` | PASS |
| 26 | `base='http://a/b/c/d;p?q' ref='/./g'` | `"http://a/g"` | `"http://a/g"` | PASS |
| 27 | `base='http://a/b/c/d;p?q' ref='/../g'` | `"http://a/g"` | `"http://a/g"` | PASS |
| 28 | `base='http://a/b/c/d;p?q' ref='g.'` | `"http://a/b/c/g."` | `"http://a/b/c/g."` | PASS |
| 29 | `base='http://a/b/c/d;p?q' ref='.g'` | `"http://a/b/c/.g"` | `"http://a/b/c/.g"` | PASS |
| 30 | `base='http://a/b/c/d;p?q' ref='g..'` | `"http://a/b/c/g.."` | `"http://a/b/c/g.."` | PASS |
| 31 | `base='http://a/b/c/d;p?q' ref='..g'` | `"http://a/b/c/..g"` | `"http://a/b/c/..g"` | PASS |
| 32 | `base='http://a/b/c/d;p?q' ref='./../g'` | `"http://a/b/g"` | `"http://a/b/g"` | PASS |
| 33 | `base='http://a/b/c/d;p?q' ref='./g/.'` | `"http://a/b/c/g/"` | `"http://a/b/c/g/"` | PASS |
| 34 | `base='http://a/b/c/d;p?q' ref='g/./h'` | `"http://a/b/c/g/h"` | `"http://a/b/c/g/h"` | PASS |
| 35 | `base='http://a/b/c/d;p?q' ref='g/../h'` | `"http://a/b/c/h"` | `"http://a/b/c/h"` | PASS |
| 36 | `base='http://a/b/c/d;p?q' ref='g;x=1/./y'` | `"http://a/b/c/g;x=1/y"` | `"http://a/b/c/g;x=1/y"` | PASS |
| 37 | `base='http://a/b/c/d;p?q' ref='g;x=1/../y'` | `"http://a/b/c/y"` | `"http://a/b/c/y"` | PASS |
| 38 | `base='http://a/b/c/d;p?q' ref='http:g'` | `"http:g"` | `"http:g"` | PASS |
| 39 | `base='http://a/b/c/d;p?q' ref='http://a/b/c/%2e%2e/g'` | `"http://a/b/c/%2e%2e/g"` | `"http://a/b/c/%2e%2e/g"` | PASS |

## 受限解析用例（越权检测）（8/8 通过）

| # | 输入 | 期望 | 实际 | 结果 |
|---|------|------|------|------|
| 1 | `base='http://a/b/c/d' ref='g'` | `"http://a/b/c/g"` | `"http://a/b/c/g"` | PASS |
| 2 | `base='http://a/b/c/d' ref='x/../g'` | `"http://a/b/c/g"` | `"http://a/b/c/g"` | PASS |
| 3 | `base='http://a/b/c/d' ref='../g'` | `"error: escapes base directory"` | `"resolved path '/b/g' escapes base directory '/b/c/'"` | PASS |
| 4 | `base='http://a/b/c/d' ref='/b/c/g'` | `"http://a/b/c/g"` | `"http://a/b/c/g"` | PASS |
| 5 | `base='http://a/b/c/d' ref='%2e%2e/g'` | `"http://a/b/c/%2E%2E/g"` | `"http://a/b/c/%2E%2E/g"` | PASS |
| 6 | `base='http://a/b/c/d' ref='../../g'` | `"error: escapes base directory"` | `"resolved path '/g' escapes base directory '/b/c/'"` | PASS |
| 7 | `base='http://a/b/c/d' ref='//evil.com/x'` | `"error: escapes base authority"` | `"reference escapes base authority 'a'"` | PASS |
| 8 | `base='http://a/b/c/d' ref='https://a/b/c/g'` | `"error: cross-scheme"` | `"cross-scheme reference 'https' not allowed (base scheme 'http')"` | PASS |

## 生成的边界用例（3/3 通过）

| # | 输入 | 期望 | 实际 | 结果 |
|---|------|------|------|------|
| 1 | `base='http://a/d/' ref=<5000 段相对路径, 长 39999>` | `"http://a/d/seg0000/seg0001/seg0002/seg0003/seg0004/seg0005/s..."` | `"http://a/d/seg0000/seg0001/seg0002/seg0003/seg0004/seg0005/s..."` | PASS |
| 2 | `base='http://a/b/c/d' ref='../'*10000+'g'` | `"http://a/g"` | `"http://a/g"` | PASS |
| 3 | `<超长绝对路径, 长 100508>` | `"幂等"` | `"幂等"` | PASS |

## 差异清单

无差异：全部 75 条用例与期望一致。
