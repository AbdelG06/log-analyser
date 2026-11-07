import logging
import os


def configure_logging() -> None:
    """Configure one application log file without changing existing modules."""
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        filename="logs/application.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
