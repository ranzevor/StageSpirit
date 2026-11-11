# 快速开始

本文面向安装和连接 StageSpirit 的使用者，适用于当前 `0.1.0.dev0` 源码版本。

## 准备环境

当前支持 Windows x64 与 CPython 3.12，构建输入使用 Python 3.12.3 和 uv 0.8.2。先安装 uv，再取得本仓库源码，以下命令均从仓库根目录执行。首次安装需要访问 Python 包源，依赖版本及下载校验信息由 `uv.lock` 固定。

[uv 安装说明](https://docs.astral.sh/uv/getting-started/installation/) · [源码入口](https://github.com/ranzevor/StageSpirit) · [版本与支持范围](../development/compatibility.md)

## 安装

```shell
uv sync --frozen --no-dev
uv run --frozen --no-dev stagespirit --version
```

版本命令应输出 `StageSpirit 0.1.0.dev0`。可执行文件位于 `.venv\Scripts\stagespirit.exe`。

## 连接 MCP 客户端

在支持 `mcpServers` 配置的客户端中加入下列内容。将 `command` 改为实际源码目录内可执行文件的绝对路径。

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

启动连接后，客户端应发现 `runtime_status`、`settings_get`、`settings_save`、`settings_apply` 和 `operation_get`。先以 `{}` 调用 `runtime_status`，读取当前运行配置、数据代际、实例身份及运行模块。

[Agent 调用指南](agent.md) · [返回字段](../reference/mcp.md#当前运行入口)

## 连接自检

也可通过随源码提供的 Python 示例启动独立进程，完成初始化、工具发现和状态查询。

```shell
uv run --frozen --no-dev python examples/mcp/runtime_status.py
```

成功时输出运行状态 JSON 并以退出码 0 结束。示例使用自动清理的临时数据目录，与日常客户端的 `default` 配置分开。

## 保存运行设置

通过 `settings_get` 读取 `section: "runtime"`，再将返回的 `saved_revision` 和运行状态中的 `data_generation` 传入 `settings_save`。当前可保存 `log_level`，可选 DEBUG、INFO、WARNING、ERROR、CRITICAL，默认 WARNING。保存后立即应用，重启自动恢复。

也可运行隔离示例，观察保存和重启后的活动值。

```shell
uv run --frozen --no-dev python examples/mcp/settings.py
```

[调用顺序与失败处理](agent.md#保存和应用配置) · [完整字段](../reference/mcp.md#配置范围与值)

## 运行配置和数据目录

`--profile` 默认值为 `default`。名称为 1 至 64 个小写字母、数字、连字符或下划线，以字母或数字开头，并避开 Windows 保留名称。每个配置同时运行一个服务进程，不同配置可分别连接不同客户端。

Windows 默认数据根目录为 `%LOCALAPPDATA%\StageSpirit`，配置维护状态位于 `profiles/<profile_id>/control.json`，运行配置和应用操作保存在同目录的 `state.sqlite3`。`data_generation` 在普通重启后保持，`instance_id` 每次启动更新。

使用 `--data-dir` 显式选择数据根目录，相对路径按服务启动时的工作目录解析，`~` 展开为用户目录。客户端配置建议使用绝对路径。

```json
{
  "mcpServers": {
    "stagespirit": {
      "command": "C:\\projects\\StageSpirit\\.venv\\Scripts\\stagespirit.exe",
      "args": ["serve", "--profile", "stream", "--data-dir", "D:\\StageSpiritData"]
    }
  }
}
```

## 启动与退出

手动运行服务的命令如下。

```shell
uv run --frozen --no-dev stagespirit serve --profile default
```

进程通过标准输入输出等待 MCP 请求，日志写入标准错误。客户端关闭连接后服务退出并释放实例锁，终端手动启动时可用 Ctrl+C 结束。

| 情况 | 处理 |
| --- | --- |
| 运行配置名称无效 | 按名称规则修改 `--profile` |
| 同一配置已有活动实例 | 连接现有实例所属客户端，或给另一个客户端选择独立配置 |
| 数据目录不可写 | 将 `--data-dir` 指向当前账户可写的位置 |
| 维护状态格式错误或版本不支持 | 根据错误检查目标目录和已安装版本，保留原文件并使用对应版本恢复 |
| 数据库版本不支持或数据身份不一致 | 使用支持该数据库格式、且与当前 profile 和维护状态对应的程序及数据 |

参数错误返回退出码 2，启动或存储错误返回 1，正常退出返回 0，Ctrl+C 返回 130。帮助和版本命令直接读取本地程序信息。

[兼容与更新](../development/compatibility.md) · [存储设计](../design/storage.md)
