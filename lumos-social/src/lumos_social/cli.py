"""CLI: status, run. Typer-based. python -m lumos_social status | run."""

import sys
import time

import typer

from lumos_social.config import load_config
from lumos_social.connectors.mock import MockConnector
from lumos_social.core.bus import EventBus
from lumos_social.core.events import Event
from lumos_social.service import SocialService

app = typer.Typer(help="Lumos social layer CLI")


@app.command()
def status() -> None:
    """Özet: env, mode, connector health (kilit/presence bilgisi yoksa sadece connector)."""
    config = load_config()
    connector = MockConnector()
    health = connector.health()
    print("lumos-social status")
    print(f"  env: {config.get('env', 'dev')}")
    print(f"  mode: {config.get('log_level', 'INFO')} (log_level)")
    print(f"  connector: {health.get('name', 'mock')}")
    print(f"  health: ok={health.get('ok', True)} fetch_count={health.get('fetch_count', 0)}")


@app.command()
def run() -> None:
    """Mock connector'ı çalıştırıp event'leri akıtır (Ctrl+C ile çık)."""
    connector = MockConnector()
    bus = EventBus()

    def on_event(event: Event) -> None:
        print(f"event {event.kind} source={event.source} payload={event.payload}")

    bus.subscribe(on_event)
    service = SocialService(connector, bus)
    print("lumos-social run (mock connector, event stream; Ctrl+C to stop)")
    try:
        while True:
            n = service.fetch_and_publish()
            if n > 0:
                pass  # handler already printed
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nstopped")
        sys.exit(0)


def main() -> None:
    """Entrypoint for lumos-social script and python -m lumos_social."""
    app()


if __name__ == "__main__":
    app()
