"""
utils_graphs.py
Gera gráficos para os embeds do bot como imagens em memória (BytesIO).
"""

import io
import colorsys
import textwrap 
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec


# ==============================================================================
# Helpers
# ==============================================================================

def _safe_int(value) -> int:
    try:
        return int(value) if value else 0
    except (ValueError, TypeError):
        return 0


def _buf(fig) -> io.BytesIO:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150, transparent=True)
    buf.seek(0)
    plt.close(fig)
    return buf


# ==============================================================================
# Paleta e Listas de Roles
# ==============================================================================

BG             = "#1a1a1a"
LIGHT_GREEN    = "#90ee90"  
LIGHT_PINK     = "#ffb6c1"  
EVIL_COLOR     = "#c0392b"
GOOD_COLOR     = "#2980b9"
TEXT_COLOR     = "#f0f0f0"
DIM_COLOR      = "#aaaaaa"

# Nova paleta pastel para o gráfico de votos (Azul e Roxo Pastel)
PASTEL_BLUE    = "#aec6cf"  
PASTEL_PURPLE  = "#d7bde2"  


GOOD_ROLES = [
    'Merlin', 'Apprentice', 'Caelia', 'Elaine', 'Galahad', 'Gawain',
    'Guinevere', 'King Arthur', 'Palamedes', 'Percival', 'Sir Kay',
    'Tristan', 'Iseult', 'Loyal Servant', 'Penpingion', 'Lancelot',
    'Nimue (G)'
]

EVIL_ROLES = [
    'Assassin', 'Bertilak', 'Dagonet', 'Lucius', 'Maduc', 'Mark',
    'Meleagant', 'Mordred', 'Morgana', 'Oberon', 'Puck', 'Queen Mab',
    'Vortigern', 'The Witch of Caerlloyw', 'Minion', 'Bad Lance',
    'Nimue (E)'
]
# ==============================================================================
# Página 1 — donut win/lose % + barras evil/good + texto lateral
# ==============================================================================


def first_role(role_str):
    if isinstance(role_str, str) and "," in role_str:
        return role_str.split(",")[0].strip()
    return role_str

def make_page1_graph(stats: dict) -> io.BytesIO:
    wins     =    (_safe_int(stats.get("good_games_won"))
                 + _safe_int(stats.get("evil_games_won"))
                 + _safe_int(stats.get("gawain_games_won"))
                 + _safe_int(stats.get("nimue_games_won"))
                 
                 )

    losses   =    (_safe_int(stats.get("good_games_lost"))
                 + _safe_int(stats.get("evil_games_lost"))
                 + _safe_int(stats.get("gawain_games_lost"))
                 + _safe_int(stats.get("nimue_games_lost"))
                 )

    evil_total =  (_safe_int(stats.get("evil_games_won"))
                 + _safe_int(stats.get("evil_games_lost"))
                 + _safe_int(stats.get("gawain_evil_lost"))
                 + _safe_int(stats.get("nimue_evil_lost"))
                 + _safe_int(stats.get("nimue_win_evil"))

                )
    
    good_total =  (_safe_int(stats.get("good_games_won"))
                 + _safe_int(stats.get("good_games_lost"))
                 + _safe_int(stats.get("gawain_good_lost"))
                 + _safe_int(stats.get("gawain_games_won"))
                 + _safe_int(stats.get("nimue_win_good"))
                 + _safe_int(stats.get("nimue_good_lost"))
                )

    total    = wins + losses
    win_pct  = f"{round(wins   / total * 100)}%" if total > 0 else "—"
    loss_pct = f"{round(losses / total * 100)}%" if total > 0 else "—"

    most_played    = first_role(stats.get("role_played_most"))      or "—"
    evil_role_most = first_role(stats.get("evil_role_played_most")) or "—"
    good_role_most = first_role(stats.get("good_role_played_most")) or "—"
    last_game      = stats.get("date_last_played")                  or "—"

    fig = plt.figure(figsize=(7, 7.5), facecolor=BG)
    gs = GridSpec(
        3, 3, figure=fig,
        height_ratios=[1.3, 1.0, 0.75],
        width_ratios=[1, 1.1, 1],
        left=0.06, right=0.96,
        top=0.96, bottom=0.05,
        wspace=0.25, hspace=0.38,
    )

    ax_tl = fig.add_subplot(gs[0, 0])
    ax_tl.set_facecolor(BG)
    ax_tl.axis("off")
    ax_tl.text(0.5, 0.80, "Games Played", ha="center", va="center",
               color=DIM_COLOR, fontsize=13)
    ax_tl.text(0.5, 0.30, str(total), ha="center", va="center",
               color=TEXT_COLOR, fontsize=52, fontweight="bold")

    ax_tm = fig.add_subplot(gs[0, 1:3])
    ax_tm.set_facecolor(BG)
    donut_vals = [wins, losses] if total > 0 else [1, 0]
    
    ax_tm.pie(donut_vals, colors=[LIGHT_GREEN, LIGHT_PINK], startangle=90,
              wedgeprops={"width": 0.42, "edgecolor": BG, "linewidth": 2})

    win_patch  = mpatches.Patch(color=LIGHT_GREEN, label=f"Win  {win_pct}")
    loss_patch = mpatches.Patch(color=LIGHT_PINK,  label=f"Lose {loss_pct}")
    ax_tm.legend(handles=[win_patch, loss_patch],
                 loc="lower center", bbox_to_anchor=(0.5, -0.08),
                 fontsize=10, frameon=False, labelcolor=TEXT_COLOR, ncol=2,
                 handlelength=1.2, handleheight=1.2)

    ax_mid = fig.add_subplot(gs[1, 0:3])
    ax_mid.set_facecolor(BG)
    x       = [0.30, 0.70]
    bar_max = max(evil_total, good_total, 1)
    bars    = ax_mid.bar(x, [evil_total, good_total],
                         color=[EVIL_COLOR, GOOD_COLOR],
                         width=0.25, edgecolor=BG)
    for bar, val in zip(bars, [evil_total, good_total]):
        ax_mid.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + bar_max * 0.05,
                    str(val), ha="center", va="bottom", fontsize=13, color=TEXT_COLOR)
    ax_mid.set_xticks(x)
    ax_mid.set_xticklabels(["Evil", "Good"], color=TEXT_COLOR, fontsize=13)
    ax_mid.set_xlim(0, 1)
    ax_mid.set_ylim(0, bar_max * 1.32)
    ax_mid.spines[["top", "right", "left"]].set_visible(False)
    ax_mid.spines["bottom"].set_color("#444444")
    ax_mid.yaxis.set_visible(False)
    ax_mid.tick_params(bottom=False, colors=TEXT_COLOR)

    ax_bl = fig.add_subplot(gs[2, 0:2])
    ax_bl.axis("off")
    ax_bl.set_facecolor(BG)
    entries = [
        ("most played as:", most_played),
        ("played most evil as:",  evil_role_most),
        ("played most good as:",  good_role_most),
    ]
    x_pos = [0.02, 0.37, 0.70]
    for (label, value), xp in zip(entries, x_pos):
        ax_bl.text(xp, 0.85, label, fontsize=9,   color=DIM_COLOR,  va="top")
        ax_bl.text(xp, 0.40, value, fontsize=10.5, color=TEXT_COLOR, va="top",
                   fontweight="bold")

    ax_br = fig.add_subplot(gs[2, 2])
    ax_br.axis("off")
    ax_br.set_facecolor(BG)
    ax_br.text(0.5, 0.85, "last game played", ha="center", va="top",
               fontsize=9, color=DIM_COLOR)
    ax_br.text(0.5, 0.40, last_game, ha="center", va="top",
               fontsize=10, color=TEXT_COLOR, fontweight="bold")

    return _buf(fig)


# ==============================================================================
# Página 2 — donut votos (menor, cores pastel azul e roxo)
# ==============================================================================

def make_votes_graph(stats: dict) -> io.BytesIO:
    correct   = _safe_int(stats.get("correct_votes"))
    incorrect = _safe_int(stats.get("incorrect_votes"))
    total     = correct + incorrect

    fig, ax = plt.subplots(figsize=(2.6, 2.2), facecolor=BG)
    ax.set_facecolor(BG)

    vals = [correct, incorrect] if total > 0 else [1, 0]
    
    # Atualizado com cores pastéis solicitadas (PASTEL_BLUE e PASTEL_PURPLE)
    ax.pie(vals, colors=[PASTEL_BLUE, PASTEL_PURPLE], startangle=90,
           wedgeprops={"width": 0.45, "edgecolor": BG, "linewidth": 1.5})

    if total > 0:
        ratio = f"{round(correct / total * 100)}%"
        ax.text(0, 0, ratio, ha="center", va="center",
                fontsize=14, fontweight="bold", color=TEXT_COLOR)

    correct_patch   = mpatches.Patch(color=PASTEL_BLUE, label=f"Correct  {correct}")
    incorrect_patch = mpatches.Patch(color=PASTEL_PURPLE, label=f"Wrong  {incorrect}")
    
    ax.legend(handles=[correct_patch, incorrect_patch],
              loc="lower center", bbox_to_anchor=(0.5, -0.15),
              fontsize=8.5, frameon=False, labelcolor=TEXT_COLOR, ncol=2)

    return _buf(fig)


# ==============================================================================
# Página 3 — GM
# ==============================================================================

def make_gm_graphs(stats: dict) -> tuple[io.BytesIO, io.BytesIO]:
    def _hbar(labels, values, colors, title: str, subtitle: str = "") -> io.BytesIO:
        fig, ax = plt.subplots(figsize=(5, 2.6), facecolor=BG)
        ax.set_facecolor(BG)

        max_val = max(values, default=1)
        bars = ax.barh(labels, values, color=colors, edgecolor=BG, height=0.42)
        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + max_val * 0.03,
                    bar.get_y() + bar.get_height() / 2,
                    str(val), va="center", fontsize=10, color=TEXT_COLOR)

        ax.set_xlim(0, max_val * 1.35)
        ax.tick_params(colors=TEXT_COLOR, labelsize=10)
        ax.spines[["top", "right", "bottom"]].set_visible(False)
        ax.spines["left"].set_color("#444444")
        ax.xaxis.set_visible(False)
        ax.invert_yaxis()
        for lbl in ax.get_yticklabels():
            lbl.set_color(TEXT_COLOR)

        fig.text(0.5, 0.97, title, ha="center", va="top",
                 fontsize=11, fontweight="bold", color=TEXT_COLOR)
        if subtitle:
            fig.text(0.5, 0.90, subtitle, ha="center", va="top",
                     fontsize=9, color=DIM_COLOR)

        fig.tight_layout(pad=0.6, rect=[0, 0, 1, 0.88])
        return _buf(fig)

    total_gmed = _safe_int(stats.get("total_games_gmed"))

    gm_labels  = ["Single", "Duo", "Triple"]
    gm_keys    = ["gm_single", "gm_duo", "gm_triple"]
    gm_values  = [_safe_int(stats.get(k)) for k in gm_keys]
    gm_colors  = ["#e74c3c", "#e67e22", "#f1c40f"]

    buf1 = _hbar(gm_labels, gm_values, gm_colors,
                 title="GM Stats  —  Single / Duo / Triple",
                 subtitle=f"Total games GM'd: {total_gmed}")

    pl_labels  = ["Solo", "Pairs", "Mixed"]
    pl_keys    = ["gm_solo", "gm_pairs", "gm_mixed"]
    pl_values  = [_safe_int(stats.get(k)) for k in pl_keys]
    pl_colors  = ["#2ecc71", "#3498db", "#9b59b6"]

    buf2 = _hbar(pl_labels, pl_values, pl_colors,
                 title="Players  —  Solo / Pairs / Mixed")

    return buf1, buf2


# ==============================================================================
# Páginas 6 e 7 — Barras de Roles
# ==============================================================================

def _make_filtered_roles_graph(stats: dict, valid_roles: list, bar_color: str, empty_msg: str) -> io.BytesIO:
    roles_played: dict = stats.get("roles_played") or {}
    
    valid_roles_clean = [r.strip().lower() for r in valid_roles]
    
    filtered_roles = {}
    for role, qty in roles_played.items():
        if role.strip().lower() in valid_roles_clean and qty > 0:
            filtered_roles[role] = qty
            
    roles_sorted = sorted(filtered_roles.items(), key=lambda x: x[1], reverse=True)

    if not roles_sorted:
        fig, ax = plt.subplots(figsize=(5, 2), facecolor=BG)
        ax.axis("off")
        ax.text(0.5, 0.5, empty_msg, ha="center", va="center",
                color=TEXT_COLOR, fontsize=12, transform=ax.transAxes)
        return _buf(fig)

    labels = [textwrap.fill(r[0], width=14) for r in roles_sorted]
    values = [r[1] for r in roles_sorted]
    n      = len(labels)

    fig_h    = min(8.0, max(2.5, n * 0.45))
    bar_h    = max(0.25, min(0.55, 5.0 / n))
    font_sz  = max(7, min(9, int(80 / n)))

    fig, ax = plt.subplots(figsize=(6, fig_h), facecolor=BG)
    ax.set_facecolor(BG)

    bars = ax.barh(labels, values, color=bar_color, edgecolor=BG, height=bar_h)
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + max(values) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=font_sz, color=TEXT_COLOR)

    ax.set_xlim(0, max(values) * 1.22)
    ax.tick_params(colors=TEXT_COLOR, labelsize=font_sz)
    ax.spines[["top", "right", "bottom"]].set_visible(False)
    ax.spines["left"].set_color("#444444")
    ax.xaxis.set_visible(False)
    ax.invert_yaxis()
    
    for lbl in ax.get_yticklabels():
        lbl.set_color(TEXT_COLOR)

    fig.tight_layout(pad=0.5)
    return _buf(fig)


def make_good_roles_graph(stats: dict) -> io.BytesIO:
    return _make_filtered_roles_graph(stats, GOOD_ROLES, "#1abc9c", "No good roles played yet")

def make_evil_roles_graph(stats: dict) -> io.BytesIO:
    return _make_filtered_roles_graph(stats, EVIL_ROLES, "#e74c3c", "No evil roles played yet")