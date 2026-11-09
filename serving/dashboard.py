import logging
import os
import subprocess
import tkinter as tk
from tkinter import ttk
from typing import List, Tuple
from html import escape

import matplotlib

matplotlib.use("Agg")
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


def _write_html(output_dir: str, chart_data: dict) -> None:
    failed = chart_data["failed_attempts_by_country"]
    successful = chart_data["successful_attempts_by_user"]
    invalid = chart_data["failed_invalid_users_by_user"]
    failed_total = sum(value for _, value in failed)
    successful_total = sum(value for _, value in successful)
    invalid_total = sum(value for _, value in invalid)
    html = f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Log Analyser | Dashboard</title>
  <style>
    :root {{ --bg:#f4f7fb; --ink:#172033; --muted:#6b7280; --card:#fff;
      --blue:#2563eb; --red:#dc2626; --green:#059669; --orange:#ea580c; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--ink);
      font:15px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
    header {{ background:linear-gradient(120deg,#172554,#2563eb); color:white;
      padding:34px max(24px,calc((100% - 1180px)/2)); }}
    header h1 {{ margin:0 0 8px; font-size:30px; }}
    header p {{ margin:0; opacity:.82; }}
    main {{ max-width:1180px; margin:28px auto; padding:0 24px; }}
    .cards {{ display:grid; grid-template-columns:repeat(3,1fr); gap:18px; }}
    .card,.panel {{ background:var(--card); border-radius:14px; padding:22px;
      box-shadow:0 5px 18px #17255412; }}
    .card {{ border-left:5px solid var(--blue); }}
    .card.red {{ border-color:var(--red); }} .card.green {{ border-color:var(--green); }}
    .card.orange {{ border-color:var(--orange); }}
    .label {{ color:var(--muted); font-size:13px; text-transform:uppercase;
      letter-spacing:.06em; }} .value {{ margin-top:8px; font-size:32px; font-weight:700; }}
    .grid {{ display:grid; grid-template-columns:repeat(2,1fr); gap:18px; margin-top:18px; }}
    .panel h2 {{ margin:0 0 15px; font-size:19px; }}
    .chart {{ width:100%; border-radius:8px; background:#fafafa; }}
    table {{ width:100%; border-collapse:collapse; }}
    th,td {{ padding:11px 8px; text-align:left; border-bottom:1px solid #e8edf5; }}
    th:last-child,td:last-child {{ text-align:right; }} th {{ color:var(--muted); font-size:12px;
      text-transform:uppercase; }} .empty {{ text-align:center!important; color:var(--muted); }}
    footer {{ color:var(--muted); text-align:center; padding:20px; font-size:13px; }}
    @media(max-width:760px) {{ .cards,.grid {{ grid-template-columns:1fr; }} main {{ padding:0 14px; }} }}
  </style>
</head>
<body>
  <header><h1>Log Analyser</h1><p>Dashboard de surveillance des authentifications SSH</p></header>
  <main>
    <section class="cards">
      <div class="card red"><div class="label">Tentatives échouées</div><div class="value">{failed_total:,}</div></div>
      <div class="card green"><div class="label">Connexions réussies</div><div class="value">{successful_total:,}</div></div>
      <div class="card orange"><div class="label">Utilisateurs invalides</div><div class="value">{invalid_total:,}</div></div>
    </section>
    <section class="grid">
      <article class="panel"><h2>Échecs par pays</h2>
        <img class="chart" src="failed_attempts_by_country.png" alt="Échecs par pays">
        <table><thead><tr><th>Pays</th><th>Nombre</th></tr></thead>
          <tbody>{_table_rows(failed)}</tbody></table>
      </article>
      <article class="panel"><h2>Connexions réussies par utilisateur</h2>
        <img class="chart" src="successful_attempts_by_user.png" alt="Connexions réussies">
        <table><thead><tr><th>Utilisateur</th><th>Nombre</th></tr></thead>
          <tbody>{_table_rows(successful)}</tbody></table>
      </article>
      <article class="panel"><h2>Utilisateurs invalides</h2>
        <img class="chart" src="failed_invalid_users_by_user.png" alt="Utilisateurs invalides">
        <table><thead><tr><th>Utilisateur</th><th>Nombre</th></tr></thead>
          <tbody>{_table_rows(invalid)}</tbody></table>
      </article>
    </section>
  </main>
  <footer>Généré automatiquement par le projet Log Analyser</footer>
</body>
</html>
"""
    with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as file:
        file.write(html)


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
        data_by_title = dict(values)
        for title, (view, x_label, y_label) in zip(
            ("Tentatives échouées par pays", "Tentatives réussies par utilisateur",
             "Tentatives avec utilisateur invalide"),
            (
                ("failed_attempts_by_country", "Pays", "Tentatives"),
                ("successful_attempts_by_user", "Utilisateur", "Tentatives"),
                ("failed_invalid_users_by_user", "Utilisateur", "Tentatives"),
            ),
        ):
            data = data_by_title[title]
            _create_chart(output_dir, view, title, x_label, y_label, data)
        _show_native_dashboard(values, output_dir)
    except (OSError, subprocess.CalledProcessError, ValueError):
        LOGGER.exception("Cannot open dashboard application")
        raise


def _show_native_dashboard(
    values: List[Tuple[str, List[Tuple[str, int]]]], output_dir: str
) -> None:
    root = tk.Tk()
    root.title("Log Analyser - Dashboard")
    root.geometry("1180x760")
    root.minsize(900, 600)
    root.configure(background="#262833")
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TFrame", background="#262833")
    style.configure("TLabel", background="#262833", foreground="#f4f4f5")
    style.configure(
        "Title.TLabel", background="#262833", foreground="#ffffff",
        font=("Helvetica", 22, "bold")
    )
    style.configure(
        "Kpi.TLabel", background="#ffffff", foreground="#172033",
        font=("Helvetica", 20, "bold")
    )
    style.configure("KpiName.TLabel", background="#262833", foreground="#d1d5db")
    style.configure("TLabelframe", background="#ffffff", bordercolor="#9ca3af")
    style.configure("TLabelframe.Label", background="#ffffff", foreground="#172033")
    style.configure("TNotebook", background="#262833", borderwidth=0)
    style.configure(
        "TNotebook.Tab", background="#d1d5db", foreground="#172033",
        padding=(12, 6)
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", "#ffffff")],
        foreground=[("selected", "#172033")],
    )
    style.configure(
        "Treeview", background="#ffffff", fieldbackground="#ffffff",
        foreground="#172033", rowheight=24
    )
    style.configure(
        "Treeview.Heading", background="#e5e7eb", foreground="#172033"
    )

    ttk.Label(root, text="Log Analyser", style="Title.TLabel").pack(
        anchor="w", padx=24, pady=(20, 2)
    )
    ttk.Label(
        root, text="Surveillance des authentifications SSH",
        style="KpiName.TLabel"
    ).pack(anchor="w", padx=24, pady=(0, 18))
    cards = ttk.Frame(root)
    cards.pack(fill="x", padx=24, pady=(0, 18))
    for column, (title, rows) in enumerate(values):
        card = ttk.LabelFrame(cards, text=title)
        card.grid(row=0, column=column, sticky="ew", padx=5)
        cards.columnconfigure(column, weight=1)
        ttk.Label(
            card, text=f"{sum(count for _, count in rows):,}",
            style="Kpi.TLabel"
        ).pack(padx=18, pady=14)

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=24, pady=(0, 24))
    chart_views = (
        "failed_attempts_by_country",
        "successful_attempts_by_user",
        "failed_invalid_users_by_user",
    )
    for (title, rows), view in zip(values, chart_views):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text=title)
        image = tk.PhotoImage(file=os.path.join(output_dir, f"{view}.png"))
        image = image.subsample(max(1, image.width() // 900))
        tab.chart_image = image
        ttk.Label(tab, image=image, background="#ffffff").pack(
            fill="both", expand=True, padx=12, pady=12
        )
        table = ttk.Treeview(
            tab, columns=("name", "count"), show="headings", height=5
        )
        table.heading("name", text="Nom")
        table.heading("count", text="Nombre")
        table.column("name", width=260)
        table.column("count", width=120, anchor="e")
        for label, count in rows:
            table.insert("", "end", values=(label, count))
        table.pack(fill="x", padx=12, pady=(0, 12))
    root.mainloop()
