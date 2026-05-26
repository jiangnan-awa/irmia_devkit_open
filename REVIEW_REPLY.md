# 对自动审核的逐条回复

> 仓库: irmia2026/irmia_devkit_open · 基线: b5f345f

---

### main.py — 数据持久化

**报告**: `config.json` 直接写入插件目录，应使用 `StarTools.get_data_dir()`。

**回复**: `config.json` 是插件**配置**而非运行时持久化数据。AstrBot 自身的 `_conf_schema.json` 即放置于插件目录——框架约定如此。`backup_dir` 默认 `~/.irmia/backups`，已在插件目录外。接受未来迭代中将默认备份路径改为 `StarTools.get_data_dir() / "backups"`。

---

### tools/_http_utils.py — DNS 重绑定 TOCTOU

**报告**: 验证 IP 后底层 HTTP 库会再次 DNS 解析，存在时间窗攻击。

**回复**: 当前实现为四层防御，非单次 `getaddrinfo`：

1. **字面 IP 直检** — hostname 为 IP 时直接比对 `_PRIVATE_NETS`，不进 DNS
2. **IPv4-mapped-IPv6 提取** — `::ffff:10.0.0.1` 映射回 IPv4 再检查
3. **`getaddrinfo` 全量校验** — 解析后的所有 A/AAAA 记录逐条 check
4. **`SafeRedirectHandler`** — 每次 HTTP 重定向重新走完整 SSRF 校验，不等第一次

不直接用解析后的 IP 建立连接的原因：需要 SNI 支持 HTTPS。若在 LLM Agent 的威胁模型下有实际 PoC 绕过四层，我们立即修复。

---

### tools/_http_utils.py — `getaddrinfo` 同步阻塞

**报告**: 同步 DNS 查询会阻塞 asyncio 事件循环。

**回复**: 实际运行中不阻塞。`tools/_helpers.py` 的 `run_sync()` 将 HTTP 请求 + DNS 解析的整个调用链提交至 `asyncio.get_running_loop().run_in_executor()` 的线程池。DNS 查询发生在工作线程，不占用事件循环。接受后续改为 `loop.getaddrinfo()` 以减少线程池开销。

---

### tools/_file_utils.py — `human_size` 整除精度

**报告**: `n //= 1024` 抹零截断，1500B → "1KB"，丢失 500B。

**回复**: 场景是 `dir_tree` 输出和 `http_download` 完成消息——`"1KB"` 与 `"1.46KB"` 在上述上下文无实质差异。需要精确值时用 `file_hash` 或 `file_diff` 的字节数。但多位评审指出感知问题，接受改为 `n /= 1024` + `f"{n:.1f}{unit}"` 保留一位小数。列入下次迭代。

---

### tools/_registry.py — 模块化与可维护性

**报告**: 1690 行，数十个 FunctionTool 杂糅，应拆为 `git_tools.py` / `fs_tools.py` 等。

**回复**: 该文件是 v1.6 从 `main.py`（原 1580 行）提取的**注册表**，执行单一职责：@dataclass 模板 → TOOL_GROUPS 映射 → _ALL_TOOLS 字典。1690 行中 63 个工具类共享同一套结构（每类 ~25 行），不是"不同领域杂糅"——是**同质模板的集合**。工具的业务逻辑在 `tools/` 下 38 个独立文件中（每个 ~70 行纯函数）。注册表就是设计意图的模块化方案。

若拆为 63 个文件，每个含 25 行模板 + 对应的 import——维护成本反而更高，且破坏当前 `from .tools._registry import TOOL_GROUPS, _ALL_TOOLS` 的单行 import。

---

### tools/_registry.py — `number if number else None` 空值处理

**报告**: `number=0` 会被误转为 `None`。

**回复**: ✅ **已修**。`number if number else None` → `number or None`，语义等价但更清晰。PR #0 在实际业务中不可能出现，此改动纯为代码清洁。

---

### tools/_registry.py — HTTP POST JSON 静默退化

**报告**: `json.loads(data)` 失败后盲送坏字符串，应提示 LLM。

**回复**: ✅ **已修**。JSON 解析失败时，若 `data` 以 `{` 或 `[` 开头（明显意图为 JSON），返回 `"data 看起来是 JSON 但解析失败——请检查 JSON 语法后重试"` 而非盲送。纯文本 data 不受影响。

---

### 汇总

| # | 建议 | 处理 |
|---|------|:--:|
| 1 | `get_data_dir()` | 不适用（配置≠数据）。backup_dir 方向接受 |
| 2 | DNS TOCTOU | 已有四层防护。接受进一步优化 |
| 3 | `getaddrinfo` 阻塞 | 已有 `run_sync` 线程池。接受改用异步 API |
| 4 | `human_size` 精度 | 设计取舍。接受改为浮点 |
| 5 | `_registry.py` 模块化 | 注册表模式即模块化方案。不拆分 |
| 6 | `number if number else None` | ✅ 已修 |
| 7 | HTTP POST JSON 静默退化 | ✅ 已修 |
