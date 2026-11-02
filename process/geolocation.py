"""IP geolocation through the Ipinfo HTTP API."""

from __future__ import annotations

import ipaddress
import json
import logging
import os
from functools import lru_cache
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

LOGGER = logging.getLogger(__name__)


@lru_cache(maxsize=256)
def get_location(ip: str) -> dict[str, Any]:
    """Return Ipinfo data for one public IP, or an explicit unavailable result."""
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return {"ip": ip, "country_name": "IP invalide"}
    if not address.is_global:
        return {"ip": ip, "country_name": "Réseau local"}

    token = os.getenv("IPINFO_TOKEN")
    url = f"https://ipinfo.io/{quote(ip, safe='')}/json"
    if token:
        url += f"?token={quote(token, safe='')}"
    request = Request(url, headers={"User-Agent": "projet-log-analyser/1.0"})
    try:
        with urlopen(request, timeout=3) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        LOGGER.warning("Impossible de géolocaliser %s via Ipinfo: %s", ip, exc)
        return {"ip": ip, "country_name": "Indisponible"}
    data["country_name"] = data.get("country_name") or data.get("country") or "Inconnu"
    return data


def locations_for_ips(ips: list[str]) -> dict[str, dict[str, Any]]:
    """Resolve a bounded list of IPs; duplicate lookups use the local cache."""
    return {ip: get_location(ip) for ip in ips}


if __name__ == "__main__":
    print(get_location("8.8.8.8"))
