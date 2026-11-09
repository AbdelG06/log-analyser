import gzip
import logging
import os
from typing import Dict, Iterator

from storage.load_postgres import load
from ingestion.logging_config import configure_logging
from process.geolocation import enrich_database
from process.parser import parse_line

LOGGER = logging.getLogger(__name__)


def _rows(path: str) -> Iterator[Dict[str, object]]:
    opener = gzip.open if path.endswith(".gz") else open
    try:
        with opener(path, mode="rt", encoding="utf-8", errors="replace") as stream:
            for line in stream:
                parsed = parse_line(line, path)
                if parsed is not None:
                    yield parsed
    except OSError:
        LOGGER.exception("Cannot read %s", path)
        raise


def run(data_dir: str = "data") -> None:
    paths = [
        os.path.join(data_dir, name)
        for name in sorted(os.listdir(data_dir))
        if name.startswith("auth.log.")
    ]
    LOGGER.info("Loading %d log files", len(paths))
    load(row for path in paths for row in _rows(path))
    enrich_database()


if __name__ == "__main__":
    configure_logging()
    run()
