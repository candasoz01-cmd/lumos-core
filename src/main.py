"""Lumos core CLI: lock, presence, alias, durum."""
from cli.cli_router import run_cli_loop
from core.lumos_runtime import create_runtime


def main(sandbox_mode: bool | None = None) -> None:
    runtime = create_runtime(sandbox_mode)
    if runtime.ui_consumed:
        return
    assert runtime.router_ctx is not None
    run_cli_loop(runtime.router_ctx)


if __name__ == "__main__":
    main()
