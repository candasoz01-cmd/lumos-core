"""CLI: status, run, context. Typer."""

import typer

from lumos_social.app.handlers import register_handlers
from lumos_social.app.runner import build_connector
from lumos_social.config import load_config
from lumos_social.connectors.mock import MockConnector
from lumos_social.context.engine import get_engine
from lumos_social.core.bus import EventBus

app = typer.Typer(help="Lumos social layer CLI")
context_app = typer.Typer(help="Context: ingest interactions, report stats")
app.add_typer(context_app, name="context")


@app.command()
def status() -> None:
    """Özet: env, log_level, connector (mevcut davranış)."""
    config = load_config()
    connector = MockConnector()
    health = connector.health()
    print("lumos-social status")
    print(f"  env: {config.env}")
    print(f"  log_level: {config.log_level}")
    print(f"  connector: {health.get('name', config.connector)}")
    print(f"  health: ok={health.get('ok', True)}")


@app.command()
def run(
    once: bool = typer.Option(False, "--once", help="Tek event üretip çık"),
    n: int | None = typer.Option(None, "--n", help="N adet event üretip çık"),
) -> None:
    """Config'ten connector seçer, bus'a event basar, handler'lar işler. --once veya --n ile çık."""
    cfg = load_config()
    bus = EventBus()
    register_handlers(bus)
    if n is None and not once:
        once = True
    connector = build_connector(cfg, once=once, n=n)
    print("connector başlatıldı")
    connector.start(bus)
    connector.stop()
    print("connector durduruldu")


@context_app.command("ingest")
def context_ingest(
    name: str = typer.Argument(..., help="Kişi adı"),
    message: str = typer.Argument(..., help="Mesaj metni"),
    ts: str = typer.Option(..., "--ts", help="ISO8601 timestamp (e.g. 2026-03-03T20:30:00Z)"),
) -> None:
    """Store one interaction for context engine."""
    engine = get_engine()
    engine.ingest(name, message, ts)
    print("OK")


@context_app.command("report")
def context_report(
    name: str = typer.Argument(..., help="Kişi adı"),
) -> None:
    """Report interactions, stats, importance score for a name."""
    engine = get_engine()
    r = engine.report(name)
    print(f"name: {r['name']}")
    print(f"interaction_count: {r['interaction_count']}")
    print(f"last_ts: {r['last_ts']}")
    print(f"importance_score: {r['importance_score']}")


def main() -> None:
    app()


if __name__ == "__main__":
    app()
