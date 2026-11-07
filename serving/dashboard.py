import logging
import os
import subprocess
from typing import List, Tuple

import matplotlib.pyplot as plt

LOGGER = logging.getLogger(__name__)


def _query(sql: str) -> List[Tuple[str, int]]:
    database = os.environ.get("POSTGRES_DB", "log_analyser")
    result = subprocess.run(
        ["psql", "--dbname", database, "--tuples-only", "--no-align", "--field-separator", "\t", "--command", sql],
        capture_output=True,
        text=True,
        check=True,
    )
    return [
        (parts[0], int(parts[1]))
        for line in result.stdout.splitlines()
        if (parts := line.split("\t")) and len(parts) == 2
    ]


def create_dashboard(output_dir: str = "dashboard") -> None:
    os.makedirs(output_dir, exist_ok=True)
    charts = [
        ("failed_attempts_by_country", "Tentatives échouées par pays", "Pays", "Tentatives"),
        ("successful_attempts_by_user", "Tentatives réussies par utilisateur", "Utilisateur", "Tentatives"),
        ("failed_invalid_users_by_user", "Tentatives avec utilisateur invalide", "Utilisateur", "Tentatives"),
    ]
    for view, title, x_label, y_label in charts:
        try:
            data = _query(f"SELECT * FROM {view};")
            labels = [row[0] for row in data]
            values = [row[1] for row in data]
            figure, axis = plt.subplots(figsize=(10, 5))
            axis.bar(labels, values)
            axis.set(title=title, xlabel=x_label, ylabel=y_label)
            axis.tick_params(axis="x", rotation=45)
            figure.tight_layout()
            figure.savefig(os.path.join(output_dir, f"{view}.png"))
            plt.close(figure)
        except (OSError, subprocess.CalledProcessError, ValueError):
            LOGGER.exception("Cannot create chart for %s", view)
            raise
