import csv
import io
import logging
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Iterable, Optional

import requests

LOGGER = logging.getLogger(__name__)
API_URL = "https://ipinfo.io/{ip}/json"
REQUEST_TIMEOUT = 4
MAX_WORKERS = 20


def get_location(ip: str) -> Optional[str]:
    """Return the country code reported by ipinfo.io for an IP address."""
    try:
        response = requests.get(API_URL.format(ip=ip), timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        country = response.json().get("country")
    except (OSError, requests.RequestException, ValueError) as exc:
        LOGGER.warning("Geolocation request failed for %s: %s", ip, exc)
        return None

    if not isinstance(country, str) or not country:
        LOGGER.warning("Geolocation API returned no country for %s", ip)
        return None
    return country


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
            SELECT DISTINCT source_ip::text
            FROM auth_events
            WHERE source_ip IS NOT NULL
              AND source_ip::text NOT IN (SELECT source_ip::text FROM ip_country);
            """,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return (line.strip() for line in result.stdout.splitlines() if line.strip())


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
    """Geolocate new source IPs and update the event countries."""
    database = os.environ.get("POSTGRES_DB", "log_analyser")
    locations = {}
    ips = list(_query_ips(database))
    LOGGER.info("Geolocating %d new source IPs", len(ips))
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        requests_by_ip = {executor.submit(get_location, ip): ip for ip in ips}
        for completed, future in enumerate(as_completed(requests_by_ip), start=1):
            ip = requests_by_ip[future]
            country = future.result()
            if country is not None:
                locations[ip] = country
            if completed % 100 == 0 or completed == len(ips):
                LOGGER.info("Geolocation progress: %d/%d", completed, len(ips))
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
