import logging
import os
import subprocess
from typing import List, Tuple
from html import escape

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

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
    chart_data = {}
    for view, title, x_label, y_label in charts:
        try:
            data = _query(f"SELECT * FROM {view};")
            chart_data[view] = data
            _create_chart(output_dir, view, title, x_label, y_label, data)
        except (OSError, subprocess.CalledProcessError, ValueError):
            LOGGER.exception("Cannot create chart for %s", view)
            raise
    _write_html(output_dir, chart_data)


def _create_chart(
    output_dir: str,
    view: str,
    title: str,
    x_label: str,
    y_label: str,
    data: List[Tuple[str, int]],
) -> None:
    labels = [row[0] for row in data]
    values = [row[1] for row in data]
    figure, axis = plt.subplots(figsize=(10, 5))
    axis.bar(labels, values, color="#2563eb")
    axis.set(title=title, xlabel=x_label, ylabel=y_label)
    axis.tick_params(axis="x", rotation=45)
    figure.tight_layout()
    figure.savefig(os.path.join(output_dir, f"{view}.png"))
    plt.close(figure)


def _table_rows(data: List[Tuple[str, int]]) -> str:
    if not data:
        return '<tr><td colspan="2" class="empty">Aucune donnée</td></tr>'
    return "".join(
        f"<tr><td>{escape(label)}</td><td>{value:,}</td></tr>"
        for label, value in data
    )



def launch_dashboard_app() -> None:
    """Generate and display the dashboard in a native desktop window."""
    project_dir = os.path.dirname(os.path.dirname(__file__))
    output_dir = os.path.join(project_dir, "dashboard")
    datasets = [
        ("Échecs par pays", "failed_attempts_by_country"),
        ("Connexions réussies", "successful_attempts_by_user"),
        ("Utilisateurs invalides", "failed_invalid_users_by_user"),
    ]
    try:
        os.makedirs(output_dir, exist_ok=True)
        values = [(title, _query(f"SELECT * FROM {view};")) for title, view in datasets]
        chart_specs = (
            ("Échecs par pays", "failed_attempts_by_country", "Pays", "Tentatives"),
            (
                "Connexions réussies",
                "successful_attempts_by_user",
                "Utilisateur",
                "Tentatives",
            ),
            (
                "Utilisateurs invalides",
                "failed_invalid_users_by_user",
                "Utilisateur",
                "Tentatives",
            ),
        )
        data_by_title = dict(values)
        for title, view, x_label, y_label in chart_specs:
            data = data_by_title[title]
            _create_chart(output_dir, view, title, x_label, y_label, data)
        _show_matplotlib_dashboard(values)
    except (OSError, subprocess.CalledProcessError, ValueError):
        LOGGER.exception("Cannot open dashboard application")
        raise


def _show_matplotlib_dashboard(
    values: List[Tuple[str, List[Tuple[str, int]]]],
) -> None:
    figure = plt.figure(
        figsize=(16, 9),
        num="Log Analyser - Dashboard",
        facecolor="#f4f7fb",
    )
    figure.suptitle(
        "Log Analyser",
        x=0.06,
        y=0.96,
        ha="left",
        color="#172033",
        fontsize=24,
        fontweight="bold",
    )
    figure.text(
        0.06,
        0.92,
        "Surveillance des authentifications SSH",
        color="#667085",
        fontsize=12,
        ha="left",
    )

    card_colors = ("#dc2626", "#059669", "#ea580c")
    card_titles = ("Tentatives échouées", "Connexions réussies", "Utilisateurs invalides")
    for index, ((_, rows), title, color) in enumerate(
        zip(values, card_titles, card_colors)
    ):
        left = 0.06 + index * 0.30
        card = figure.add_axes((left, 0.76, 0.27, 0.10))
        card.set_axis_off()
        card.add_patch(
            FancyBboxPatch(
                (0, 0),
                1,
                1,
                boxstyle="round,pad=0.02,rounding_size=0.04",
                transform=card.transAxes,
                facecolor="white",
                edgecolor="#e4e7ec",
                linewidth=1,
            )
        )
        card.text(
            0.07,
            0.68,
            title.upper(),
            color="#667085",
            fontsize=9,
            fontweight="bold",
            va="center",
        )
        card.text(
            0.07,
            0.30,
            f"{sum(count for _, count in rows):,}",
            color=color,
            fontsize=22,
            fontweight="bold",
            va="center",
        )

    axes = (
        figure.add_axes((0.06, 0.13, 0.27, 0.54)),
        figure.add_axes((0.365, 0.13, 0.27, 0.54)),
        figure.add_axes((0.67, 0.13, 0.27, 0.54)),
    )
    for axis, (title, rows), color in zip(axes, values, card_colors):
        labels = [label for label, _ in rows[:15]]
        counts = [count for _, count in rows[:15]]
        axis.set_facecolor("white")
        axis.bar(labels, counts, color=color, width=0.72)
        axis.set_title(title, loc="left", color="#172033", fontsize=13, pad=14)
        axis.set_ylabel("Tentatives", color="#667085", fontsize=9)
        axis.tick_params(axis="x", rotation=45, labelsize=8, colors="#475467")
        axis.tick_params(axis="y", labelsize=8, colors="#475467")
        axis.grid(axis="y", alpha=0.25, color="#98a2b3")
        axis.set_axisbelow(True)
        for spine in axis.spines.values():
            spine.set_color("#e4e7ec")
        axis.margins(x=0.04)
    figure.text(
        0.06,
        0.06,
        "Source : journaux SSH analysés depuis PostgreSQL",
        color="#98a2b3",
        fontsize=9,
    )
    plt.show()
