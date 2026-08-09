# Quota Handoff

一个面向 Codex 与其他软件的开源 Skill：当外部额度适配器确认某个用量窗口的剩余额度低于阈值（默认 5%）时，生成一份基于项目当前证据的交接文档，帮助下一次任务继续工作。

## 能力边界

本项目不猜测额度，也不读取或保存账号密码。它只处理外部适配器提供的 JSON 快照：

- 支持 `remaining_percent`；
- 或支持 `remaining` + `limit`、`used` + `limit`、`used_percent`；
- 缺少可验证数据时返回 `unknown`，不会触发交接文档；
- 默认写入 `HANDOFF.md`，不会覆盖项目已有的 `README.md`。

Codex 的个人周额度是否可被程序读取，取决于当前客户端和账号是否提供机器可读入口。若没有公开 API、CLI 或导出，不能声称 Skill 已经实时读取 Codex 余额；可以传入用户提供的快照，或自行实现受控的浏览器/导出适配器。

## 安装为 Codex Skill

把 `quota-handoff` 文件夹复制到 `$CODEX_HOME/skills/`；Windows 未设置 `CODEX_HOME` 时可放到 `%USERPROFILE%\\.codex\\skills\\`。安装后重新打开 Codex，或在新任务中使用 `$quota-handoff`。

## 使用

创建 `usage.json`：

```json
{
  "provider": "example-tool",
  "window": "weekly",
  "remaining_percent": 4.2,
  "captured_at": "2026-08-09T11:00:00Z",
  "source": "provider-cli"
}
```

检查阈值：

```powershell
python quota-handoff/scripts/check_usage.py --input usage.json --threshold 5
```

低于阈值时同时生成交接文档：

```powershell
python quota-handoff/scripts/check_usage.py `
  --input usage.json --threshold 5 `
  --project-root . --handoff-output HANDOFF.md
```

也可以直接生成不带额度证据的项目状态基线：

```powershell
python quota-handoff/scripts/generate_handoff.py --project-root . --output HANDOFF.md
```

把检查命令交给 Windows Task Scheduler、cron、CI 或其他支持的自动化工具定期执行即可。调度器负责获取各软件额度并写出 JSON；本项目负责统一判断和交接文档生成。

## 验证

项目只依赖 Python 标准库：

```powershell
python -m unittest discover -s tests -v
```

## 开源许可

MIT License，见 [LICENSE](LICENSE)。
