"""MariaDB/MySQL persistence for parsed authentication events."""

from __future__ import annotations

import os
from typing import Iterable

from process.extract_transforme import LogRecord


class MySQLStorage:
    """Create the schema and persist records using parameterized queries."""

    def __init__(self, **config: str) -> None:
        try:
            import pymysql
        except ImportError as exc:
            raise RuntimeError(
                "PyMySQL est requis pour la connexion MariaDB/MySQL."
            ) from exc
        self._mysql = pymysql
        self.config = {
            "host": config.get("host") or os.getenv("MYSQL_HOST", "localhost"),
            "port": int(config.get("port") or os.getenv("MYSQL_PORT", "3306")),
            "user": config.get("user") or os.getenv("MYSQL_USER", "root"),
            "password": config.get("password") or os.getenv("MYSQL_PASSWORD", ""),
            "database": config.get("database") or os.getenv("MYSQL_DATABASE", "db_loganalyse"),
        }

    def connect(self):
        return self._mysql.Connection(**self.config)

    def initialize(self) -> None:
        database = self.config["database"]
        server_config = {key: value for key, value in self.config.items() if key != "database"}
        connection = self._mysql.Connection(**server_config, autocommit=False)
        try:
            cursor = connection.cursor()
            escaped_database = database.replace("`", "``")
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{escaped_database}`")
            connection.commit()
        finally:
            connection.close()
        connection = self._mysql.Connection(**self.config, autocommit=False)
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_events (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    event_time DATETIME NOT NULL,
                    host VARCHAR(255) NOT NULL,
                    process VARCHAR(255) NOT NULL,
                    pid INT NULL,
                    message TEXT NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    ip_address VARCHAR(45) NULL,
                    username VARCHAR(255) NULL,
                    UNIQUE KEY event_identity (event_time, host, process, message(180)),
                    INDEX idx_event_type (event_type),
                    INDEX idx_event_time (event_time)
                )
                """
            )
            connection.commit()
        finally:
            connection.close()

    def insert_records(self, records: Iterable[LogRecord]) -> int:
        rows = [
            (
                record.timestamp,
                record.host,
                record.process,
                record.pid,
                record.message,
                record.event_type,
                record.ip_address,
                record.username,
            )
            for record in records
        ]
        if not rows:
            return 0
        connection = self.connect()
        try:
            cursor = connection.cursor()
            cursor.executemany(
                """
                INSERT IGNORE INTO auth_events
                (event_time, host, process, pid, message, event_type, ip_address, username)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                rows,
            )
            connection.commit()
            return cursor.rowcount
        finally:
            connection.close()
