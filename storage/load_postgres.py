import csv
import io
import logging
import os
import subprocess
from typing import Iterable, Mapping

from ingestion.logging_config import configure_logging

LOGGER = logging.getLogger(__name__)


def _copy_rows(rows: Iterable[Mapping[str, object]]) -> str:
    output = io.StringIO()
    writer = csv.writer(output, delimiter="\t", lineterminator="\n")
    for row in rows:
        writer.writerow(
            [
                row["event_time"] or "\\N",
                row["host"],
                row["service"],
                row["pid"] if row["pid"] is not None else "\\N",
                row["event_type"],
                row["username"] or "\\N",
                row["source_ip"] or "\\N",
                row["message"],
                row["source_file"],
            ]
        )
    return output.getvalue()


def load(rows: Iterable[Mapping[str, object]]) -> None:
    """Load parsed events using the PostgreSQL CLI, not a Python driver."""
    database = os.environ.get("POSTGRES_DB", "log_analyser")
    command = ["psql", "--dbname", database, "--command",
               r"\copy auth_events(event_time,host,service,pid,event_type,username,source_ip,message,source_file) FROM STDIN WITH (FORMAT text, DELIMITER E'\t', NULL '\N')"]
    try:
        subprocess.run(command, input=_copy_rows(rows), text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        LOGGER.exception("PostgreSQL load failed")
        raise


if __name__ == "__main__":
    configure_logging()
    LOGGER.info("Use ingestion.run_pipeline to parse and load logs.")
