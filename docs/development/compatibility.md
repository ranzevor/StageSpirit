# 版本与兼容

本文面向使用者、集成开发者和维护者，定义当前支持范围、版本含义和更新规则。

## 当前支持范围

| 对象 | 当前范围 |
| --- | --- |
| StageSpirit | `0.1.0.dev0` 开发版本，源码位于本仓库 |
| 操作系统 | Windows x64 |
| Python | CPython 3.12，构建与 CI 使用 3.12.3 |
| MCP | stdio，协议 `2025-11-25`，Python SDK 2.3.0 |
| 公开入口 | `stagespirit`、`python -m stagespirit_mcp`；runtime_status、settings_get、settings_save、settings_apply、operation_get |
| 持久状态 | `control.json` 格式 1；`state.sqlite3` 模式版本 1，保存 runtime 配置、修订和配置应用操作 |
| 开发工具 | uv 0.8.2；Node.js 22.15.0 用于文档和提交检查 |

后续平台、提供方与协议支持在各自模块交付时进入本表，并关联对应验收。完整首版目标见产品范围。

[首版范围](../product/scope.md) · [开发与检查](engineering.md)

## 版本规则

软件版本唯一来源为 `src/stagespirit_mcp/__init__.py`，包元数据、CLI 和 MCP 初始化使用同一值。Python 分发遵循 PEP 440，开发构建使用 `.devN`，预发行使用 `aN`、`bN` 或 `rcN`。

稳定发行使用 `MAJOR.MINOR.PATCH`。兼容新增递增 MINOR，兼容修复递增 PATCH，破坏既有公开契约递增 MAJOR。1.0.0 前的破坏性变更递增 MINOR，并明确列出迁移方法。开发版本按对应提交识别，已经发布的版本与标签保持原内容。

公共契约包含命令参数和退出码、MCP 输入输出与错误、持久数据格式及支持环境。内部 Python 模块随实现调整。文档随所属代码版本维护，首版设计的交付阶段由实施计划说明。

## 更新与数据兼容

更新前读取目标版本的发行说明，停止正在使用该源码目录的客户端连接，然后按目标版本源码运行 `uv sync --frozen --no-dev`。重连后核对程序版本和运行配置。

普通重启沿用 `control.json` 中的数据代际。同一配置目录只能由一个活动进程使用。维护状态无法解析、格式版本不支持或配置身份不匹配时，启动失败并保留原文件；根据该版本的迁移步骤恢复后重试。

只有 `control.json` 的现有 profile 首次启动会创建配置数据库，并沿用原数据代际。数据库模式版本 1 使用 WAL 和 FULL 同步；初始化与递增迁移在事务中执行，迁移失败回滚。高于当前支持版本的数据库返回 `MIGRATION_REQUIRED`，数据库与维护状态的 profile 或数据代际不一致时拒绝启动。

数据格式升级必须提供旧数据输入、升级结果和失败恢复的验证。发生不可逆迁移时，发行说明给出对应前置和恢复来源。源码、程序和数据的恢复分别核对兼容性。

## 维护与问题处理

开发阶段的功能修复维护在 `main`，问题报告提供发生问题的版本或提交及复现方式。安全问题通过私密渠道处理。调整支持环境或弃用接口时，发行说明列出受影响对象、生效版本和替代步骤，支持表同步更新。

[问题报告](https://github.com/ranzevor/StageSpirit/issues) · [安全报告](../../SECURITY.md) · [发行流程](releasing.md)
