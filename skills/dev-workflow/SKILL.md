---
name: dev-workflow
description: >
  收到编码任务时强制走安全工作流。触发：写代码、改代码、修bug、重构、实现功能、修改文件。
  核心原则：先确认后执行、自动备份回滚、语法门禁。
  可用工具：safe_edit、git_*、syntax_check、lint_runner、file_diff、es_search、rg_search、gh_pr、gh_issue、dep_scan、code_index、code_explore。
---

# 开发工作流

## 核心原则

```
一边确认一边推进。
该停的时候停（方案阶段、计划阶段、审查后），
该走的时候走（小修改、已验证的步骤）。
不等用户催，也不用写死的路由表。
```

## 改代码之前

1. `git_status` — 确认工作区干净，无意外修改
2. `git_branch` — 确认在正确的分支上
3. `safe_backups` — 看一眼有没有旧备份可用
4. `es_search` / `rg_search` / `dir_tree` — 需要时先了解项目结构
5. `code_index` `code_explore` — 需要理解代码调用链时优先使用（'X 在哪' '从 A 到 B 怎么走'）

## 节奏感

- **需求模糊** → 先 brainstorming 探索方案，确认后再动
- **需求清晰但复杂** → 先 writing-plans 拆任务，确认后再执行
- **简单修改** → 直接 safe_edit
- **审完** → 问是否修 Critical/High，修完自动 commit push

不需要路由表，不需要流水线引擎。用判断力。

## safe_edit 铁律

- 改代码**必须**用 `safe_edit`，禁止 `file_write` 或裸 `file_patch`
- 改前 `git status`，改后 `git diff --staged`
- `safe_edit` 自动跑 `syntax_check`，语法错就分析根因重新改
- 语法失败自动回滚，不要手动恢复
- 回滚后工具返回 `proposal` 和 `options`——直接看提案，选一个选项，重试
- 代码改完后用 `lint_runner` 检查质量（ruff→pylint 自动 fallback）
- 想回到之前版本 → `safe_rollback`

## git 提交

- commit message 按 `fix:` / `feat:` / `refactor:` 规范
- `git diff --cached` 自查无敏感内容
- 大改动前备份到安全目录（如插件的 backups/ 目录）
- 推送后如需创建 PR → 用 `gh_pr`
