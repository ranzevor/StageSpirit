<p align="center">
  <img src="docs/assets/stagespirit.svg" width="112" height="112" alt="StageSpirit 灵幕图标，聚光灯下的舞台与星光">
</p>

# StageSpirit 灵幕

[![Version 0.1.0.dev0](https://img.shields.io/badge/Version-0.1.0.dev0-blue)](docs/development/compatibility.md#版本规则) [![Status development](https://img.shields.io/badge/Status-development-blue)](docs/development/delivery.md#当前交付) [![CI main](https://img.shields.io/github/actions/workflow/status/ranzevor/StageSpirit/ci.yml?branch=main&label=CI)](https://github.com/ranzevor/StageSpirit/actions/workflows/ci.yml?query=branch%3Amain) [![License Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-green)](LICENSE)

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](docs/development/compatibility.md#当前支持范围) [![Platform Windows x64](https://img.shields.io/badge/Platform-Windows%20x64-0078D4)](docs/development/compatibility.md#当前支持范围) [![MCP 2025-11-25](https://img.shields.io/badge/MCP-2025--11--25-5A45FF)](docs/reference/mcp.md#连接与发现) [![Transport stdio](https://img.shields.io/badge/Transport-stdio-5A45FF)](docs/reference/mcp.md#连接与发现)

[![Distribution wheel + sdist](https://img.shields.io/badge/Distribution-wheel%20%2B%20sdist-6E59A5)](docs/development/releasing.md#构建与安装) [![Documents Markdown](https://img.shields.io/badge/Documents-Markdown-000000)](docs/README.md) [![Contracts JSON Schema](https://img.shields.io/badge/Contracts-JSON%20Schema-blue)](contracts/README.md) [![Standards 0.2.0](https://img.shields.io/badge/Standards-0.2.0-6E59A5)](docs/standards/README.md)

让声音、表情和直播画面共同参与表达。

StageSpirit 是面向 Agent 的虚拟主播集成服务，将直播消息、语音、VTube Studio 和 OBS 连接起来，集中管理服务连接、表达规则和展台配置。调用方 Agent 负责回复和任务决策，StageSpirit 负责执行、状态与恢复。

## 当前版本

当前开发版本为 `0.1.0.dev0`，提供可安装的 Python 包、独立 stdio MCP 入口、运行配置隔离、状态查询及配置保存与应用。`runtime.log_level` 即时生效并在重启后恢复，保存修订、活动修订和应用操作可分别查询。语音、形象、直播事件和展台按交付计划逐批实现。

[当前接口](docs/reference/mcp.md) · [版本与支持范围](docs/development/compatibility.md) · [交付计划](docs/development/delivery.md)

## 安装与启动

准备 CPython 3.12 和 uv 0.8.2，取得本仓库源码后，在仓库根目录执行。

```shell
uv sync --frozen --no-dev
uv run --frozen --no-dev stagespirit --version
```

将安装后的 `stagespirit` 可执行文件接入 MCP 客户端，以 `serve --profile default` 启动。完整配置、连接自检、数据目录和启动错误处理见快速开始。

[快速开始](docs/guides/quickstart.md) · [Agent 调用指南](docs/guides/agent.md)

## 按任务阅读

| 任务 | 入口 |
| --- | --- |
| 了解产品目标和首版范围 | [产品定位](docs/product/overview.md)、[范围与边界](docs/product/scope.md) |
| 安装、连接和管理运行配置 | [快速开始](docs/guides/quickstart.md)、[当前 MCP 接口](docs/reference/mcp.md) |
| 接入后续业务能力 | [Agent 工作流设计](docs/design/agent-workflows.md)、[MCP 契约设计](docs/design/mcp-contract.md) |
| 理解需求、模块与数据归属 | [需求规格](docs/requirements/README.md)、[总体架构](docs/architecture/README.md) |
| 开发、测试与维护 | [开发文档](docs/development/README.md)、[测试设计](docs/testing/README.md) |
| 查阅全部文档 | [文档导航](docs/README.md) |

源码位于 `src/stagespirit_mcp/`，公共数据契约位于 `contracts/`，示例与测试分别位于 `examples/` 和 `tests/`。目录职责见仓库结构。

[仓库结构](docs/development/repository.md)

## 参与项目

通过仓库 Issues 报告问题、提出需求和讨论设计，按贡献指南提交变更。安全问题使用私密报告入口。

[项目仓库](https://github.com/ranzevor/StageSpirit) · [问题与设计讨论](https://github.com/ranzevor/StageSpirit/issues) · [贡献指南](CONTRIBUTING.md) · [安全报告](SECURITY.md)

## 许可

本仓库自有源码、文档、图标、Schema 和示例采用 Apache License 2.0。第三方材料在各自位置保留来源、版权和适用许可。

[Apache License 2.0](LICENSE) · [第三方脚本许可](.github/scripts/NOTICE.md)
