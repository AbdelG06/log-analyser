import csv
import io
import logging
import os
import subprocess
from typing import Dict, Iterable, List

import requests

LOGGER = logging.getLogger(__name__)
API_URL = "http://ip-api.com/batch"
REQUEST_TIMEOUT = 15
BATCH_SIZE = 100


def _query_ips(database: str) -> Iterable[str]:
    result = subprocess.run(
        [
            "psql",
            "--dbname",
            database,
            "--tuples-only",
            "--no-align",
            "--command",
            """
            SELECT DISTINCT host(source_ip)
            FROM auth_events
            WHERE source_ip IS NOT NULL
              AND source_ip NOT IN (SELECT source_ip FROM ip_country);
            """,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return (line.strip() for line in result.stdout.splitlines() if line.strip())


def _get_locations(ips: List[str]) -> Dict[str, str]:
    try:
        response = requests.post(
            API_URL,
            json=[{"query": ip} for ip in ips],
            params={"fields": "status,message,query,country"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        results = response.json()
    except (OSError, requests.RequestException, ValueError) as exc:
        LOGGER.warning("Geolocation batch request failed: %s", exc)
        return {}

    locations = {}
    if not isinstance(results, list):
        LOGGER.warning("Geolocation API returned an invalid batch response")
        return locations
    for result in results:
        if (
            isinstance(result, dict)
            and result.get("status") == "success"
            and isinstance(result.get("query"), str)
            and isinstance(result.get("country"), str)
        ):
            locations[result["query"]] = result["country"]
    return locations


def _save_locations(database: str, locations: Dict[str, str]) -> None:
    if not locations:
        return
    payload = io.StringIO()
    writer = csv.writer(payload, delimiter="\t", lineterminator="\n")
    writer.writerows(locations.items())
    subprocess.run(
        [
            "psql",
            "--dbname",
            database,
            "--command",
            r"\copy ip_country(source_ip, country) FROM STDIN WITH (FORMAT text, DELIMITER E'\t')",
        ],
        input=payload.getvalue(),
        text=True,
        check=True,
    )


def enrich_database() -> None:
    """Geolocate new source IPs in batches and update event countries."""
    database = os.environ.get("POSTGRES_DB", "log_analyser")
    locations = {}
    ips = list(_query_ips(database))
    LOGGER.info("Geolocating %d new source IPs", len(ips))
    for start in range(0, len(ips), BATCH_SIZE):
        batch = ips[start : start + BATCH_SIZE]
        locations.update(_get_locations(batch))
        LOGGER.info(
            "Geolocation progress: %d/%d IPs",
            min(start + BATCH_SIZE, len(ips)),
            len(ips),
        )
    _save_locations(database, locations)
    subprocess.run(
        [
            "psql",
            "--dbname",
            database,
            "--command",
            """
            UPDATE auth_events AS event
            SET country = country_map.country
            FROM ip_country AS country_map
            WHERE event.source_ip = country_map.source_ip
              AND event.country IS NULL;
            """,
        ],
        check=True,
    )
    LOGGER.info("Updated country data for %d source IPs", len(locations))


if __name__ == "__main__":
    print(get_location("109.199.110.135"))
