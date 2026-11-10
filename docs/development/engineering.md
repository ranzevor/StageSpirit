# 工程约定

本文面向项目开发和制品维护，说明 Python 与前端的技术选择、模块接入、验证、编码及安装交付约定。

StageSpirit 以独立 Python 包交付。使用 CPython 3.12 系列、pyproject.toml 和依赖锁建立可重建环境，Windows 为首个验收平台。前端采用 TypeScript 和 Vite，静态产物随包分发。Node.js、包管理器及前端依赖在前端构建输入中固定，构建在独立目录生成产物后纳入 wheel。

## 开发环境与检查

当前运行基础使用 Python 3.12.3、uv 0.8.2 和 MCP Python SDK 2.3.0，完整依赖版本由 uv.lock 固定。在仓库根目录执行以下命令。

```shell
uv sync --frozen
uv run --frozen ruff check src scripts tests
uv run --frozen ruff format --check src scripts tests
uv run --frozen pyright
uv run --frozen python scripts/export_contracts.py --check
uv run --frozen pytest tests/unit tests/integration tests/contract tests/e2e
```

`RuntimeSummary` 是运行状态输出的类型定义。变更后执行 `uv run --frozen python scripts/export_contracts.py` 更新对应 JSON Schema，再运行契约检查。

安装测试构建 wheel，在临时虚拟环境中安装锁定的运行依赖，通过安装后的命令执行 MCP 工具发现和调用。Windows PR 检查执行同一组命令。

## 提交与合并检查

提交检查使用 Node.js 22.15.0。进入仓库根目录，在审查过的分支中安装本地钩子。

```shell
node scripts/install_commit_hook.cjs
```

安装器将校验器及其依赖放入 Git 私有目录，激活 `commit-msg` 钩子。需要经过自定义 Git 执行入口时，使用 `--git-executable <原生客户端>` 和 `--git-wrapper <执行入口>`。既有钩子由安装器核对归属，独立的 `commit-msg` 需要先整合。

修改校验器后运行对应测试。

```shell
node --test tests/governance/*.test.cjs
```

合并前将拟采用的标题和正文写入仓库外的 UTF-8 文件，第一行为标题，空行后为正文。

```shell
node .github/scripts/commit_message.cjs message-file <消息文件>
```

通过校验的同一标题和正文分别作为 Squash 合并的 `commit_title` 和 `commit_message`，并用已审查的 PR HEAD 作为 `sha`。修改消息后重新校验。

`commit-message-tests` 检查新增校验逻辑。`governance-metadata` 从 PR 目标分支加载校验器，分页读取当前 PR 的实际提交，检查标题和提交消息。该工作流随校验器合入目标分支后启用，首次实际运行通过后加入主分支必需检查。

[提交消息规则](../../CONTRIBUTING.md#提交消息与-pr-标题) · [代码来源与许可](../../.github/scripts/NOTICE.md)

## 开发入口与职责

日常开发通过源码、CLI、测试、MCP 客户端、HTTP/WebSocket 和目标服务 API 完成。联调首先检查实际入口、配置和目标回执。开发 Agent 的工具权限放在专用[执行约束](../../AGENTS.md)，产品使用指南只说明产品操作。

新增能力先落实所属模块与公开端口，再实现适配器。所有 VTS 写入经过 avatar，所有 OBS 写入经过 broadcast，跨模块调用遵循[内部接口](../architecture/interfaces.md)。系统生命周期不承载各业务模块的内部状态。

## 依赖和制品

pyproject.toml 维护包、CLI、工具配置及可选依赖；锁文件固定解析输入和安装集合。测试与运行依赖分组，提供方 SDK 延迟加载，缺少单个可选依赖只影响对应适配器。

Python 包为 stagespirit_mcp，分发包为 stagespirit-mcp，CLI 为 stagespirit。制品只包含运行代码、必要配置模板、静态资源及合法许可材料。账号、用户媒体、数据库和凭据位于独立运行目录。

## 验证选择

Ruff、Pyright 和 Pytest 分别承担格式规则、类型和行为检查。单元验证规则，契约验证请求响应与协议适配，集成验证真实存储与模块协作，目标联调验证实际外部效果。

按本次差异确定影响范围与测试。通过且无相关回归改动的分支不重复执行；失败后修复对应原因，再运行受影响场景。使用受控事件验证并发和取消，避免只靠固定 sleep 判断完成。

文档修改维护必要的链接和接口说明。项目文件的历史由 Git 管理。

## 编码与日志

源码、配置、JSON 和日志统一 UTF-8。stdio 的标准输出只承载 MCP 协议，日志写标准错误或受限文件。编码检查覆盖中文路径、管道和安装后的 Windows 命令入口。

错误返回当前操作所需的信息。诊断日志保留目标、操作、代际和原因，脱敏鉴权材料；面向直播观众的画面不显示工程状态。

## 复用与许可

本仓库自有源码、文档、Schema 和示例采用 Apache License 2.0。引入代码、SDK、字体、图像和其他资源时，在依赖或材料所属位置保留来源、版权及适用许可。制品包含项目许可及实际材料所需的第三方通知，构建检查覆盖随包分发的材料。

[项目许可](../../LICENSE) · [贡献来源与许可](../../CONTRIBUTING.md#内容来源与许可)

## 交付

从构建后的 wheel 在干净环境安装，核对导入位置、命令、静态文件和可选依赖行为。提交说明描述实际行为、契约影响和本次检查结果，提交与对外发布按当前授权分别执行。

技术选择及取舍见[架构决策记录](../adr/README.md)，范围和顺序见[交付计划](delivery.md)。
