# Codex Context Handoff

一个轻量的 Codex Skill：把对话、分析结论或任务状态安全交给全新线程。既支持“长对话原地换窗”，也支持“外部研究完成后，定向交到指定项目、分支或现有 worktree”。

> A lightweight Codex skill for handing conversation state or research results to a verified fresh thread, including an explicitly directed project, branch, or existing worktree.

## 两个独立、可直接调用的技能

下面两个 Skill 是并列入口。需要哪种交接结果，直接调用对应的完整技能名即可；不需要先调用另一个，也不是“一个技能加一个参数”。

```text
$context-handoff
```

完成交接后等待你继续讨论。

```text
$context-handoff-goal
```

目标工作区核验通过后，直接创建并启动一个明确 Goal。

请直接使用 `$context-handoff` 或 `$context-handoff-goal`。`$context-handoff goal` 不是技能指令。

## 支持的交接场景

- 对话过长、变慢或频繁重连后换到新窗口。
- 讨论或规划完成后进入下一阶段。
- 分析 GitHub/开源项目后，把结论交给正式产品项目实施。
- 定向进入指定本地分支或已经存在的 Git worktree。
- 原任务异常中断后，根据已核验状态恢复。
- 纯讨论交接，不强行绑定一个随手打开的目录。

两个指令只决定“交接后等待”还是“交接后执行”。Skill 会独立判断为什么交接、真正应该交到哪里。

## 目标选择原则

目的地优先采用用户明确给出的精确路径、项目和本地分支。如果一个项目存在多个可能的 worktree，Skill 会只问一个关键问题，不会根据最后访问目录、项目昵称或裸 `main` 猜测。

外部开源仓库可以是分析来源，正式产品 worktree 可以是执行目标。交接包会分别记录来源和目的地，不再假设二者相同。

## 交接内容

- 源对话 ID 与目标对话 ID（运行环境可提供时）。
- 稳定的 `handoff_id` 和每次重试独立的 `attempt_id`。
- 来源工作区和目标工作区的独立快照。
- 真实目录、仓库、Git/worktree 身份、本地分支、HEAD 和 dirty 内容指纹。
- 当前目标、关键决策、被排除方案、剩余事项、约束和验收条件。
- 外部来源的 URL、版本/commit、许可证或 clean-room 边界（相关时）。

不会复制完整对话，也不会上传会话内容。

## 安全边界

默认只交接上下文：

- 不自动 push 或 cherry-pick。
- 不复制文件。
- 不自动 commit、stash、reset、clean 或 checkout。
- 不自动创建、切换或删除 worktree。
- 不把提示词 fallback 冒充成已经完成的线程交接或原生 Goal。

目标线程开始前会二次核验目录、仓库、worktree、本地分支、HEAD、dirty 内容、Git 操作/冲突和锁。关键 Git 探针失败时按“未知且不安全”处理，不会误报为 clean。

## 安装

```bash
git clone https://github.com/guozhixin88/codex-context-handoff.git \
  "$HOME/.agents/skills/context-handoff"
ln -s "$HOME/.agents/skills/context-handoff/context-handoff-goal" \
  "$HOME/.agents/skills/context-handoff-goal"
```

重新打开一个 Codex 对话后，两个技能都会独立出现在 `$` 技能菜单中。已有安装执行 `git pull`；如果 Goal 技能尚未单独出现，再补上面的软链接。

## 可选：轻量自动提醒

仓库包含一个可选 `UserPromptSubmit` Hook，按 transcript 文件大小分级提醒：

- 50 MB：软信号。
- 100 MB：强提醒。
- 200 MB：高优先级。
- 500 MB：临界提醒。

将 [`hooks/hooks.example.json`](hooks/hooks.example.json) 的 `UserPromptSubmit` 项合并到自己的 `~/.codex/hooks.json`。不要覆盖已有 Hook；如果安装在其他目录，先调整示例里的脚本路径。首次启用或脚本变化后，按 Codex 提示审核。

正常路径只读取一次 transcript 文件元数据。它不会启动 daemon、轮询、联网、调用模型或扫描 transcript/全局日志正文。目标解析也只在实际调用交接技能时按需运行。

`Reconnecting 5/5` 只有在该文本进入 Hook 输入或用户主动报告时才能触发；Hook 不会为了捕获 UI 传输错误而持续扫描日志。

## 能力边界

- 自动创建/验证新线程依赖当前 Codex 运行环境是否提供线程工具。
- 如果线程工具不可用，Skill 会生成可直接粘贴到新窗口的完整提示词，并明确标记尚未自动完成。
- 对话 ID 不可读取时写 `null`，绝不猜测。
- Skill 不能迁移浏览器登录态、运行进程、端口或未持久化工具状态。
- 原生 Goal 只有在目标线程能够启动并回读验证时才会标记为成功。

## 测试

```bash
python3 -m unittest discover -s tests -v
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py context-handoff-goal
```

## License

MIT
