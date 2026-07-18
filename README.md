# Codex Context Handoff

一个轻量的 Codex Skill：把过长、变慢或频繁重连的对话安全交接到全新线程，同时保留源/目标对话 ID、真实工作目录、Git 分支、关键决策和下一步动作。

> A lightweight Codex skill for moving long conversations into verified fresh threads without copying the bloated transcript.

## 两个可搜索的技能

```text
$context-handoff
```

新窗口继续讨论，默认也是最安全的模式。

```text
$context-handoff-goal
```

新窗口通过目录/分支预检后，直接创建目标并开始执行。

Codex 的技能菜单只列出 `$skill-name`。因此 goal 模式使用独立名称 `$context-handoff-goal`，而不是不会作为第二个菜单项出现的 `$context-handoff goal`。

## 交接内容

- 源对话 ID 与目标对话 ID（运行环境可提供时）
- `handoff_id`
- 真实目录、仓库根目录、分支、HEAD、dirty 状态
- 当前目标、已完成状态、关键决策、剩余事项、约束与验收条件
- 目标线程的第一个动作

不会复制完整对话，也不会上传会话内容。

## 安装

```bash
git clone https://github.com/guozhixin88/codex-context-handoff.git \
  "$HOME/.agents/skills/context-handoff"
ln -s "$HOME/.agents/skills/context-handoff/context-handoff-goal" \
  "$HOME/.agents/skills/context-handoff-goal"
```

重新打开一个 Codex 对话后，两个技能都会独立出现在 `$` 技能菜单中。如果已用旧方式安装，在仓库内执行 `git pull`，再只补充上面的 `ln -s` 即可。

## 可选：轻量自动提醒

仓库包含一个可选 `UserPromptSubmit` Hook，按 transcript 文件大小分级提醒：

- 50 MB：软信号
- 100 MB：强提醒
- 200 MB：高优先级
- 500 MB：临界提醒

将 [`hooks/hooks.example.json`](hooks/hooks.example.json) 的 `UserPromptSubmit` 项合并到自己的 `~/.codex/hooks.json`。不要覆盖已有 Hook；首次启用或脚本变化后，按 Codex 提示运行 `/hooks` 审核。

正常路径只读取一次 transcript 文件元数据。它不会启动 daemon、轮询、联网、调用模型或扫描 transcript/全局日志正文。

`Reconnecting 5/5` 只有在该文本进入 Hook 输入或用户主动报告时才能触发；Hook 不会为了捕获 UI 传输错误而持续扫描日志。

## 能力边界

- 自动创建/验证新线程依赖当前 Codex 运行环境是否提供线程工具。
- 如果线程工具不可用，Skill 会生成可直接粘贴到新窗口的完整提示词，并明确标记尚未自动完成。
- 对话 ID 不可读取时写 `null`，绝不猜测。
- 不会自动 stash、commit、reset、clean、切换分支或删除旧线程。

## 测试

```bash
python3 -m unittest discover -s tests -v
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

## License

MIT
