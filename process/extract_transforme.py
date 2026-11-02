"""Parse Linux auth.log lines into records suitable for analysis and storage."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Optional

LOG_PATTERN = re.compile(
    r"^(?P<month>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})\s+"
    r"(?P<time>\d{2}:\d{2}:\d{2})\s+(?P<host>\S+)\s+"
    r"(?P<process>[\w./-]+)(?:\[(?P<pid>\d+)\])?:\s*(?P<message>.*)$"
)
IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
USER_PATTERN = re.compile(r"(?:user|for|invalid user)\s+([A-Za-z0-9._-]+)", re.I)


@dataclass(frozen=True)
class LogRecord:
    timestamp: datetime
    host: str
    process: str
    pid: Optional[int]
    message: str
    event_type: str
    ip_address: Optional[str]
    username: Optional[str]

    def as_dict(self) -> dict:
        return asdict(self)


def _event_type(message: str) -> str:
    lowered = message.lower()
    if "failed password" in lowered or "authentication failure" in lowered:
        return "failed_login"
    if "accepted password" in lowered or "accepted publickey" in lowered:
        return "successful_login"
    if "invalid user" in lowered:
        return "invalid_user"
    if "session opened" in lowered:
        return "session_opened"
    if "session closed" in lowered:
        return "session_closed"
    if "connection closed" in lowered:
        return "connection_closed"
    return "other"


def parse_line(row: str, year: Optional[int] = None) -> Optional[LogRecord]:
    """Parse an auth.log row; return None for lines outside the supported format."""
    match = LOG_PATTERN.match(row.strip())
    if not match:
        return None
    values = match.groupdict()
    timestamp = datetime.strptime(
        f"{year or datetime.now().year} {values['month']} {values['day']} {values['time']}",
        "%Y %b %d %H:%M:%S",
    )
    message = values["message"]
    ip_match = IP_PATTERN.search(message)
    user_match = USER_PATTERN.search(message)
    return LogRecord(
        timestamp=timestamp,
        host=values["host"],
        process=values["process"],
        pid=int(values["pid"]) if values["pid"] else None,
        message=message,
        event_type=_event_type(message),
        ip_address=ip_match.group(0) if ip_match else None,
        username=user_match.group(1) if user_match else None,
    )


def parse_rows(rows: list[str], year: Optional[int] = None) -> list[LogRecord]:
    return [record for row in rows if (record := parse_line(row, year))]


def extract_from_row(row: str) -> Optional[dict]:
    """Backward-compatible structured replacement for the old print-only function."""
    record = parse_line(row)
    return record.as_dict() if record else None