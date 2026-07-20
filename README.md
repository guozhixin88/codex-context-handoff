# Codex Context Handoff

一个轻量的 Codex Skill：把对话、分析结论或任务状态安全交给全新任务，同时保证目标目录正确、后续只有一个执行者。

> A lightweight Codex skill for handing minimal task state to one verified owner in the exact target workspace.

## 两个独立、可直接调用的技能

下面两个 Skill 都可以直接调用，按需要选择即可。

```text
$context-handoff
```

完成交接后等待你继续讨论。

```text
$context-handoff-goal
```

目标工作区核验通过后，直接创建并启动一个明确 Goal。

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

交接包围绕五个问题：

- 当前正在做什么。
- 已经完成了什么，以及验证证据。
- 卡在哪里或还有什么不确定。
- 下一步做什么。
- 哪些坑、错误路线或约束不能再踩。

除此之外只增加安全恢复必需的信息：源/目标对话 ID、精确目录、仓库、worktree、本地分支、HEAD、dirty 状态和一个稳定的 `handoff_id`。

不会复制完整对话，也不会上传会话内容。

## 文档整理与 Hand-off Markdown

每次交接都会先生成一份五点式 Markdown 交接稿，但不代表每次都要在仓库里新增文件。

- 普通换窗、纯讨论：交接稿直接放进目标任务提示词，目标收到后等待或执行。
- 项目阶段收尾、文档可能过期：如果环境里已经安装 `neat-freak`，先用它对齐项目知识；没安装时，只检查本次任务相关的 README、规则和 docs，不要求额外安装。
- 复杂或长期任务、人工打开指定 worktree、旧 Goal 需要手动释放：优先把交接稿保存到项目已有的 handoff 位置；没有约定时使用 `docs/handoffs/YYYY-MM-DD-<topic>.md`。
- 紧急卡顿、重连失败、纯只读研究：跳过重型文档整理，直接交接，避免为了收尾继续拖慢旧对话。

文档整理、Hand-off MD 写入和最终工作区快照按这个顺序执行，保证交接记录反映的就是整理后的真实目录和 Git 状态。公开版不依赖 `neat-freak`，它只是可选增强。

## 安全边界

默认只交接上下文：

- 不自动 push 或 cherry-pick。
- 不复制文件。
- 不自动 commit、stash、reset、clean 或 checkout。
- 不自动创建、切换或删除 worktree。
- 不为了交接自动安装其他 Skill。
- 不把提示词 fallback 冒充成已经完成的线程交接或原生 Goal。

目标任务开始前会二次核验其真正登记的目录、仓库、worktree、本地分支、HEAD、dirty 内容、Git 操作/冲突和锁。仅仅让一条命令临时进入正确目录，不算任务已经绑定到该目录。

交接完成后，旧任务不再监控、测试、复核、提交、推送或替新任务宣布完成。

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
- 当前任务创建接口不一定能绑定任意一个已经存在的 linked worktree。目标 worktree 没有被 Codex 单独登记时，Skill 会停止自动创建，并生成应粘贴到该精确目录新任务中的提示词；不会退回父项目主目录冒充成功。
- 当前 Goal 接口不一定提供暂停或转移旧 Goal 的能力。旧 Goal 仍 active 时，Skill 不会启动第二个 Goal；目标只完成预检并等待旧 Goal 被释放。
- 如果线程工具不可用或真实绑定无法验证，Skill 会生成可直接粘贴到新窗口的完整提示词，并明确标记尚未自动完成。
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
