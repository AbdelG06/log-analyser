import datetime
import ipaddress
import logging
import re
from typing import Dict, Iterator, Optional

LOGGER = logging.getLogger(__name__)
HEADER = re.compile(
    r"^(?P<month>\w{3})\s+(?P<day>\d{1,2})\s+(?P<clock>\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>\S+)\s+(?P<service>\w+)(?:\[(?P<pid>\d+)\])?:\s+(?P<body>.*)$"
)
ACCEPTED = re.compile(r"Accepted \S+ for (?P<user>\S+) from (?P<ip>\S+)")
FAILED = re.compile(
    r"Failed password for (?:(?:invalid user )?(?P<user>\S+)) from (?P<ip>\S+)"
)
INVALID = re.compile(r"Invalid user (?P<user>\S+) from (?P<ip>\S+)")


def _ip(value: str) -> Optional[str]:
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return None


def parse_line(line: str, source_file: str) -> Optional[Dict[str, object]]:
    match = HEADER.match(line.rstrip("\n"))
    if not match:
        LOGGER.warning("Unrecognised log line in %s", source_file)
        return None

    body = match.group("body")
    event_type = "other"
    username = None
    source_ip = None
    for candidate, kind in ((ACCEPTED, "successful_login"), (INVALID, "invalid_user"), (FAILED, "failed_password")):
        found = candidate.search(body)
        if found:
            event_type = kind
            username = found.group("user")
            source_ip = _ip(found.group("ip"))
            break

    try:
        event_time = datetime.datetime.strptime(
            f"{match.group('month')} {match.group('day')} {match.group('clock')}",
            "%b %d %H:%M:%S",
        ).replace(year=datetime.datetime.now().year)
    except ValueError:
        LOGGER.exception("Invalid date in %s", source_file)
        event_time = None

    return {
        "event_time": event_time,
        "host": match.group("host"),
        "service": match.group("service"),
        "pid": int(match.group("pid")) if match.group("pid") else None,
        "event_type": event_type,
        "username": username,
        "source_ip": source_ip,
        "message": body,
        "source_file": source_file,
    }


def parse_file(path: str) -> Iterator[Dict[str, object]]:
    try:
        with open(path, encoding="utf-8", errors="replace") as stream:
            for line in stream:
                parsed = parse_line(line, path)
                if parsed is not None:
                    yield parsed
    except OSError:
        LOGGER.exception("Cannot read %s", path)
        raise
