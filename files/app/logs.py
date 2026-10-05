"""Logging setup shared by every entry point."""

import logging


def setup_logging(level: str) -> None:
    """Logs to stderr with timestamps; `level` comes from `LOG_LEVEL`."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )
