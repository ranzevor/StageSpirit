# StageSpirit 灵幕

StageSpirit 将直播消息、声音、虚拟形象和播出画面连接起来，支持 Agent 参与直播互动，并集中管理服务连接、表达规则和展台配置。

项目当前处于设计阶段。现有内容包括产品范围、需求规格、架构与专题设计、接口契约、调用指南和验收设计。

## 从这里开始

1. 阅读产品定位，了解直播互动、角色表达和展台播出的使用场景。
2. 阅读产品范围与需求规格，确认首版能力及可观察结果。
3. 按文档导航进入架构、接口、调用流程或验收设计。

[产品定位](docs/product/overview.md) · [产品范围](docs/product/scope.md) · [需求规格](docs/requirements/README.md) · [文档导航](docs/README.md)

## 项目结构

| 目录 | 用途 |
| --- | --- |
| src/stagespirit_mcp/ | Python 后端源码，规划目录 |
| web/stage/ | 展台前端源码，规划目录 |
| docs/ | 产品、需求、架构、设计、参考、指南和测试文档 |
| contracts/ | MCP 工具定义和共享 Schema |
| examples/contracts/ | 接口请求与响应示例 |
| tests/ | 测试及测试数据 |
| scripts/ | 开发维护脚本，规划目录 |

项目目录的职责和文档维护方式见仓库结构。开发接入从工程约定和实施计划开始。

[仓库结构](docs/development/repository.md) · [工程约定](docs/development/engineering.md) · [实施计划](docs/development/delivery.md)

访问与资源边界在专题设计中维护，材料复用和许可事项由工程约定说明。

[访问与资源设计](docs/design/security.md) · [复用与许可](docs/development/engineering.md#复用与许可)

## 参与项目

通过仓库 Issues 报告问题、提出功能需求和讨论设计，按贡献指南提交文档、契约、示例及后续源码变更。安全问题使用私密报告入口。

[项目仓库](https://github.com/ranzevor/StageSpirit) · [问题与设计讨论](https://github.com/ranzevor/StageSpirit/issues) · [贡献指南](CONTRIBUTING.md) · [安全报告方式](SECURITY.md)

## 许可

本仓库自有源码、文档、Schema 和示例采用 Apache License 2.0。第三方材料在各自位置保留来源、版权和适用许可。

[Apache License 2.0](LICENSE)
