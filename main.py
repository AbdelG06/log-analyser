"""Command-line entry point for the log analyzer."""

from __future__ import annotations

import argparse
from pathlib import Path

from ingestion.raw import to_rows
from process.extract_transforme import parse_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyseur de journaux Linux avec dashboard Matplotlib")
    parser.add_argument("path", nargs="?", default="data", help="fichier ou dossier de logs")
    parser.add_argument("--gui", action="store_true", help="ouvrir le dashboard Matplotlib")
    parser.add_argument("--mysql", action="store_true", help="initialiser MySQL et importer les événements")
    args = parser.parse_args()
    records = parse_rows(to_rows(Path(args.path)))
    print(f"{len(records)} lignes analysées.")
    if args.mysql:
        from storage.mysql import MySQLStorage
        storage = MySQLStorage()
        storage.initialize()
        print(f"{storage.insert_records(records)} nouveaux événements enregistrés dans MySQL.")
    if args.gui:
        from serving.dashboard import Dashboard
        Dashboard(records).run()


if __name__ == "__main__":
    main()