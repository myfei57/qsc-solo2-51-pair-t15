"""Command line entry point: ``python -m desalplant``."""

from .app import build_application
from .config import parse_args
from .console.server import serve


def main(argv: list[str] | None = None) -> int:
    """Build the service and serve the console until interrupted."""
    config = parse_args(argv)
    application = build_application(config)
    print(f"control console listening on http://{config.host}:{config.port}", flush=True)
    print(
        f"committed keys {application.store.count()} at tick {application.clock.tick}",
        flush=True,
    )
    serve(config, application.console)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
