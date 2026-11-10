# StageSpirit 灵幕

StageSpirit 将直播消息、声音、虚拟形象和播出画面连接起来，支持 Agent 参与直播互动，并集中管理服务连接、表达规则和展台配置。

当前提供 D1 首批运行基础，可安装 Python 包、启动 stdio MCP 服务，并通过 `runtime_status` 查询运行配置、持久数据代际和实例状态。完整功能按实施计划分批交付。

[产品定位](docs/product/overview.md) · [产品范围](docs/product/scope.md) · [实施计划](docs/development/delivery.md) · [文档导航](docs/README.md)

## 安装与启动

使用 Python 3.12 和 uv 0.8.2，在仓库根目录运行。

```shell
uv sync --frozen --no-dev
uv run --frozen --no-dev stagespirit --version
uv run --frozen --no-dev stagespirit serve --profile default
```

`serve` 通过标准输入输出等待 MCP 客户端请求。客户端关闭连接后，服务退出并释放实例锁。日志写入标准错误。安装与开发检查见工程约定。

[开发环境与检查](docs/development/engineering.md#开发环境与检查)

## MCP 客户端配置

以下配置适用于使用 `mcpServers` 的 stdio 客户端。将 `command` 改为实际安装目录下的 `.venv\Scripts\stagespirit.exe`。macOS 和 Linux 对应 `.venv/bin/stagespirit`。

```json
{
  "mcpServers": {
    "stagespirit": {
      "command": "C:\\projects\\StageSpirit\\.venv\\Scripts\\stagespirit.exe",
      "args": ["serve", "--profile", "default"]
    }
  }
}
```

连接后发现 `runtime_status`，以 `{}` 调用即可读取状态。`data_generation` 随当前运行配置持久保存，`instance_id` 在每次启动时更新。

使用 `--data-dir` 可选择应用数据根目录。默认使用系统用户数据目录，Windows 为 `%LOCALAPPDATA%\StageSpirit`。每个 profile 的状态位于 `profiles/<profile_id>/`，同一 profile 同时运行一个实例。

[运行状态字段](docs/reference/mcp.md#当前运行入口) · [存储布局](docs/design/storage.md#数据布局)

## 项目结构

| 目录 | 用途 |
| --- | --- |
| src/stagespirit_mcp/ | Python 后端源码 |
| web/stage/ | 展台前端的规划位置 |
| docs/ | 产品、需求、架构、设计、参考、指南和测试文档 |
| contracts/ | MCP 工具定义和共享 Schema |
| examples/contracts/ | 接口请求与响应示例 |
| tests/ | 测试及测试数据 |
| scripts/ | 开发维护脚本 |

[仓库结构](docs/development/repository.md) · [工程约定](docs/development/engineering.md) · [访问与资源设计](docs/design/security.md)

## 参与项目

通过仓库 Issues 报告问题、提出功能需求和讨论设计，按贡献指南提交变更。安全问题使用私密报告入口。

[项目仓库](https://github.com/ranzevor/StageSpirit) · [问题与设计讨论](https://github.com/ranzevor/StageSpirit/issues) · [贡献指南](CONTRIBUTING.md) · [安全报告方式](SECURITY.md)

## 许可

本仓库自有源码、文档、Schema 和示例采用 Apache License 2.0。第三方材料在各自位置保留来源、版权和适用许可。

[Apache License 2.0](LICENSE)
