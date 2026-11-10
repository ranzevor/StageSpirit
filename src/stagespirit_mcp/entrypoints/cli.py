import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from stagespirit_mcp import __version__
from stagespirit_mcp.bootstrap.application import open_runtime
from stagespirit_mcp.entrypoints.mcp import create_server
from stagespirit_mcp.infrastructure.standard_streams import configure_standard_streams
from stagespirit_mcp.runtime.errors import StartupError


def main(arguments: Sequence[str] | None = None) -> int:
    configure_standard_streams()
    parser = argparse.ArgumentParser(prog="stagespirit", description="StageSpirit 虚拟主播集成服务")
    parser.add_argument("--version", action="version", version=f"StageSpirit {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="启动 stdio MCP 服务")
    serve.add_argument("--profile", default="default", help="运行配置 ID，默认为 default")
    serve.add_argument(
        "--data-dir", type=Path, default=None, help="应用数据根目录，默认使用用户数据目录"
    )
    args = parser.parse_args(arguments)
    try:
        with open_runtime(args.profile, args.data_dir) as runtime:
            create_server(runtime).run(transport="stdio")
    except (StartupError, OSError) as error:
        logging.getLogger("stagespirit").error("%s", error)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0
