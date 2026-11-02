"""Spacious multi-page Matplotlib dashboard for authentication logs."""

from __future__ import annotations

from collections import Counter
from typing import Sequence

import matplotlib

if not matplotlib.get_backend().lower().startswith("macosx"):
    matplotlib.use("MacOSX", force=True)

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.widgets import Button

from process.extract_transforme import LogRecord
from process.geolocation import locations_for_ips

NAVY = "#0f172a"
SLATE = "#475569"
MUTED = "#64748b"
GRID = "#e2e8f0"
PANEL = "#ffffff"
BACKGROUND = "#f1f5f9"
BLUE = "#2563eb"
RED = "#dc2626"
GREEN = "#16a34a"
PURPLE = "#7c3aed"
ORANGE = "#ea580c"


class Dashboard:
    """Display three spacious pages with native previous/next navigation."""

    def __init__(self, records: Sequence[LogRecord]) -> None:
        self.records = records
        self.page = 0
        self.figure = plt.figure(
            figsize=(16, 10),
            facecolor=BACKGROUND,
            num="Log Analyzer | Security Dashboard",
        )
        self.events = Counter(record.event_type for record in records)
        self.ips = Counter(record.ip_address for record in records if record.ip_address)
        self.users = Counter(record.username for record in records if record.username)
        candidate_ips = [ip for ip, _ in self.ips.most_common(50)]
        self.locations = locations_for_ips(candidate_ips)
        self.public_ips = [
            ip for ip in candidate_ips
            if self.locations[ip].get("country_name") not in {"Réseau local", "IP invalide"}
        ][:10]
        self.country_counts = Counter(
            self.locations[ip].get("country_name", "Inconnu")
            for ip in self.public_ips
            for _ in range(self.ips[ip])
        )
        self._draw()

    @staticmethod
    def _panel(axis, title: str, subtitle: str = "") -> None:
        axis.set_facecolor(PANEL)
        axis.set_title(title, loc="left", pad=14, fontsize=12,
                       fontweight="bold", color=NAVY)
        if subtitle:
            axis.text(0, 1.01, subtitle, transform=axis.transAxes,
                      fontsize=8, color=MUTED, va="bottom")
        axis.grid(axis="y", color=GRID, linewidth=0.8)
        axis.set_axisbelow(True)
        for spine in axis.spines.values():
            spine.set_color(GRID)

    def _card(self, area, label: str, value: int, color: str) -> None:
        axis = self.figure.add_subplot(area)
        axis.set_facecolor(PANEL)
        axis.axis("off")
        axis.add_patch(plt.Rectangle((0, 0), 0.025, 1, transform=axis.transAxes,
                                     color=color, clip_on=False))
        axis.text(0.10, 0.66, label, transform=axis.transAxes,
                  fontsize=9, color=MUTED, fontweight="bold")
        axis.text(0.10, 0.18, f"{value:,}", transform=axis.transAxes,
                  fontsize=25, color=NAVY, fontweight="bold")

    def _header(self, title: str, page_name: str) -> None:
        self.figure.text(0.045, 0.965, "SECURITY LOG ANALYZER",
                         fontsize=10, color=BLUE, fontweight="bold")
        self.figure.text(0.045, 0.925, title, fontsize=23,
                         color=NAVY, fontweight="bold")
        self.figure.text(0.975, 0.935, page_name, ha="right",
                         fontsize=10, color=MUTED)

    def _draw(self) -> None:
        self.figure.clear()
        if self.page == 0:
            self._overview()
        elif self.page == 1:
            self._security()
        else:
            self._users()
        self._navigation()
        self.figure.canvas.draw_idle()

    def _overview(self) -> None:
        self._header("Vue générale", "Page 1 sur 3")
        grid = GridSpec(10, 12, figure=self.figure, left=.055, right=.965,
                        top=.86, bottom=.12, hspace=2.2, wspace=1.4)
        failed = self.events["failed_login"] + self.events["invalid_user"]
        self._card(grid[0:2, 0:3], "TOTAL ÉVÉNEMENTS", len(self.records), BLUE)
        self._card(grid[0:2, 3:6], "ÉCHECS", failed, RED)
        self._card(grid[0:2, 6:9], "SUCCÈS", self.events["successful_login"], GREEN)
        self._card(grid[0:2, 9:12], "IP UNIQUES", len(self.ips), PURPLE)

        axis = self.figure.add_subplot(grid[3:9, 0:6])
        self._panel(axis, "Types d'événements", "Activité détectée dans les journaux")
        labels, values = zip(*self.events.most_common()) if self.events else ([], [])
        axis.bar(labels, values, color=BLUE, width=.62)
        axis.tick_params(axis="x", rotation=28, labelsize=9, colors=SLATE)
        axis.tick_params(axis="y", labelsize=9, colors=SLATE)
        axis.set_ylabel("Nombre d'événements", color=SLATE)

        axis = self.figure.add_subplot(grid[3:9, 6:12])
        self._panel(axis, "Résumé", "Indicateurs clés de la collecte")
        axis.axis("off")
        summary = [
            ("Événements analysés", f"{len(self.records):,}"),
            ("Types différents", str(len(self.events))),
            ("Utilisateurs détectés", str(len(self.users))),
            ("IP publiques candidates", str(len(self.public_ips))),
        ]
        for index, (label, value) in enumerate(summary):
            y = .82 - index * .19
            axis.text(.08, y, label, transform=axis.transAxes, color=MUTED, fontsize=11)
            axis.text(.92, y, value, transform=axis.transAxes, color=NAVY,
                      fontsize=14, fontweight="bold", ha="right")
            axis.plot([.08, .92], [y - .07, y - .07], color=GRID,
                      transform=axis.transAxes)

    def _security(self) -> None:
        self._header("Sécurité et géolocalisation", "Page 2 sur 3")
        grid = GridSpec(10, 12, figure=self.figure, left=.055, right=.965,
                        top=.86, bottom=.12, hspace=2.3, wspace=1.5)
        axis = self.figure.add_subplot(grid[0:5, 0:6])
        self._panel(axis, "Top adresses IP", "Sources les plus fréquentes")
        top = self.ips.most_common(10)
        axis.barh([ip for ip, _ in top][::-1], [n for _, n in top][::-1],
                  color=RED, height=.55)
        axis.tick_params(axis="both", labelsize=9, colors=SLATE)
        axis.set_xlabel("Événements", color=SLATE)

        axis = self.figure.add_subplot(grid[0:5, 6:12])
        self._panel(axis, "Pays détectés", "IP publiques via Ipinfo")
        countries, values = zip(*self.country_counts.most_common(8)) if self.country_counts else ([], [])
        if countries:
            axis.barh(list(countries)[::-1], list(values)[::-1],
                      color=ORANGE, height=.55)
            axis.tick_params(axis="both", labelsize=9, colors=SLATE)
        else:
            axis.text(.5, .5, "Aucune IP publique disponible",
                      ha="center", va="center", color=MUTED)
            axis.axis("off")

        axis = self.figure.add_subplot(grid[6:10, :])
        axis.set_facecolor(PANEL)
        axis.axis("off")
        axis.set_title("Détails des IP publiques", loc="left", pad=10,
                       fontsize=12, fontweight="bold", color=NAVY)
        rows = [[ip, f"{self.ips[ip]:,}", self.locations[ip].get("country_name", "Inconnu")]
                for ip in self.public_ips]
        if rows:
            table = axis.table(cellText=rows,
                               colLabels=["ADRESSE IP", "ÉVÉNEMENTS", "PAYS"],
                               cellLoc="left", colLoc="left", loc="center",
                               colWidths=[.35, .22, .30])
            table.auto_set_font_size(False)
            table.set_fontsize(10)
            table.scale(1, 1.65)
            for (row, column), cell in table.get_celld().items():
                cell.set_edgecolor(GRID)
                cell.set_facecolor(NAVY if row == 0 else ("#f8fafc" if row % 2 else PANEL))
                cell.set_text_props(color="white" if row == 0 else SLATE,
                                    weight="bold" if row == 0 else "normal")
        else:
            axis.text(.5, .5, "Aucune adresse IP publique détectée",
                      ha="center", va="center", color=MUTED)

    def _users(self) -> None:
        self._header("Utilisateurs et événements", "Page 3 sur 3")
        grid = GridSpec(10, 12, figure=self.figure, left=.055, right=.965,
                        top=.86, bottom=.12, hspace=2.3, wspace=1.5)
        axis = self.figure.add_subplot(grid[0:7, 0:7])
        self._panel(axis, "Top utilisateurs", "Identifiants extraits des messages")
        top = self.users.most_common(15)
        if top:
            axis.barh([user for user, _ in top][::-1], [n for _, n in top][::-1],
                      color=PURPLE, height=.55)
            axis.tick_params(axis="both", labelsize=9, colors=SLATE)
            axis.set_xlabel("Événements", color=SLATE)
        else:
            axis.text(.5, .5, "Aucun utilisateur détecté", ha="center", va="center", color=MUTED)
            axis.axis("off")

        axis = self.figure.add_subplot(grid[0:7, 7:12])
        self._panel(axis, "Types d'événements", "Vue détaillée")
        top_events = self.events.most_common()
        axis.pie([n for _, n in top_events], labels=[name for name, _ in top_events],
                 autopct="%1.0f%%", startangle=90, colors=[BLUE, RED, GREEN, ORANGE, PURPLE])
        axis.set_aspect("equal")

        axis = self.figure.add_subplot(grid[8:10, :])
        axis.set_facecolor(PANEL)
        axis.axis("off")
        axis.text(.02, .72, "Navigation", color=NAVY, fontsize=11, fontweight="bold")
        axis.text(.02, .28, "Utilisez les boutons en bas pour parcourir les pages du dashboard.",
                  color=MUTED, fontsize=10)

    def _navigation(self) -> None:
        previous = self.figure.add_axes([.39, .025, .10, .045])
        next_page = self.figure.add_axes([.51, .025, .10, .045])
        previous_button = Button(previous, "← Précédent", color="#e2e8f0", hovercolor="#cbd5e1")
        next_button = Button(next_page, "Suivant →", color=BLUE, hovercolor="#1d4ed8")
        previous_button.label.set_color(NAVY)
        next_button.label.set_color("white")
        previous_button.on_clicked(self._previous_page)
        next_button.on_clicked(self._next_page)
        self._buttons = (previous_button, next_button)

    def _previous_page(self, _event) -> None:
        self.page = (self.page - 1) % 3
        self._draw()

    def _next_page(self, _event) -> None:
        self.page = (self.page + 1) % 3
        self._draw()

    def run(self) -> None:
        plt.show(block=True)
