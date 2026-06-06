# utils_sheets.py

import os
import json
import time
import gspread
from google.oauth2.service_account import Credentials

from utils_config import _fuzzy_match_name_local
from utils_graphs import GOOD_ROLES, EVIL_ROLES

CACHE_FILE = "stats_cache.json"

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file("green_credentials.json", scopes=scopes)
client = gspread.authorize(creds)

planilha = client.open("TESTE")
pagina = planilha.get_worksheet(0)
pagina_nomes = planilha.get_worksheet(6)

nomes = pagina_nomes.col_values(1)
nomes = [n for n in nomes if n not in ("Name", "Null", "")]

stats_cache: dict = {}


# ==============================================================================
# Helpers
# ==============================================================================

def _cell(dados: list, a1: str):
    col_str = ""
    row_str = ""
    for ch in a1:
        if ch.isalpha():
            col_str += ch
        else:
            row_str += ch
    col = 0
    for ch in col_str.upper():
        col = col * 26 + (ord(ch) - ord('A') + 1)
    col -= 1
    row = int(row_str) - 1
    try:
        value = dados[row][col]
        return value if value != "" else None
    except IndexError:
        return None


def _safe_int(value) -> int:
    try:
        return int(value) if value else 0
    except (ValueError, TypeError):
        return 0


def _clean_role(role_str: str) -> str:
    """Remove espaços e aspas que podem vir da planilha (ex: '\"Percival\"')."""
    return role_str.strip().strip('"').strip("'").strip()


# ==============================================================================
# Estatísticas de morte (separadas: Single vs Duo)
# ==============================================================================

def _update_death_dict(death_dict: dict, player: str, who_wins: str, role_died: str):
    # Limpa aspas e espaços que podem vir da planilha
    role_died = _clean_role(role_died)

    if not role_died:
        return

    if player not in death_dict:
        death_dict[player] = {
            "was_killed_correctly": 0,
            "was_killed_incorrectly": 0,
            "died_for_good": 0,
            "died_for_evil": 0,
            "died_as_nimue" : 0,
            "died_as_gawain" : 0,
            "tricker_good_role": 0,
            "tricker_evil_role": 0,
            "roles_that_died_with": {}
        }

    d = death_dict[player]
    role_lower = role_died.lower()

    # Listas normalizadas (lowercase) para comparação
    good_roles_lower = [r.strip().lower() for r in GOOD_ROLES]
    evil_roles_lower = [r.strip().lower() for r in EVIL_ROLES]

    is_gawain_role = role_lower == 'gawain'
    is_nimue_role = role_lower == 'nimue'
    is_good_role = role_lower in good_roles_lower
    is_evil_role = role_lower in evil_roles_lower

    if not is_good_role and not is_evil_role and not is_nimue_role:
        print(f"[DEATH STATS] Role não reconhecido: '{role_died}' (player: {player})")

    who_wins_lower = who_wins.strip().lower()

    if is_good_role:
        
        if not is_gawain_role :
            d["died_for_good"] += 1
            if who_wins_lower == "evil":
                d["was_killed_correctly"] += 1

        elif is_gawain_role:
            if who_wins_lower == "gawain":
                d["died_as_gawain"] += 1
                d["was_killed_incorrectly"] += 1
            else:
                d["was_killed_incorrectly"] += 1
                d["tricker_good_role"] += 1

        else:
            d["was_killed_incorrectly"] += 1
            d["tricker_good_role"] += 1

    elif is_evil_role:
        d["died_for_evil"] += 1
        if who_wins_lower == "good":
            d["was_killed_correctly"] += 1
        else:
            d["was_killed_incorrectly"] += 1
            d["tricker_evil_role"] += 1

    elif is_nimue_role:
        d["died_as_nimue"] += 1
        d["was_killed_incorrectly"] += 1



    roles_dict = d["roles_that_died_with"]
    roles_dict[role_died] = roles_dict.get(role_died, 0) + 1


def compute_death_stats():
    
    deaths_ws = planilha.worksheet('Death Log')
    data = deaths_ws.get_all_values()[1:]  # ignora cabeçalho

    all_death_stats = {}
    duo_death_stats = {}

    for row in data:
        gm_type   = row[2].strip().lower() if len(row) > 2 else ""
        game_type = row[3].strip().lower() if len(row) > 3 else ""
        who_wins  = row[4].strip().lower() if len(row) > 4 else ""
        who_died  = row[5].strip()         if len(row) > 5 else ""
        role_died = row[7].strip()         if len(row) > 7 else ""

        if not who_died or who_died.lower() == "no one":
            continue

        if not role_died or role_died.lower() in ("no role", ""):
            continue

        names = [n.strip() for n in who_died.split(",") if n.strip()]

        
        is_duo = len(names) >= 2

        for name in names:
            player = _fuzzy_match_name_local(name, nomes)
            if not player:
                print(f"[DEATH STATS] Nome não encontrado na Death Log: '{name}'")
                continue

            if is_duo:
                _update_death_dict(duo_death_stats, player, who_wins, role_died)
            else:
                _update_death_dict(all_death_stats, player, who_wins, role_died)

    return all_death_stats, duo_death_stats


# ==============================================================================
# Leitura de um jogador — 3 requisições (update + range principal + roles)
# ==============================================================================

def _fetch_player_stats(nome: str) -> dict:
    pagina.update_acell("A2", nome)
    time.sleep(2)

    dados = pagina.get("A1:J47")

    dados_roles = pagina.get("A19:AJ20")
    roles_played = {}
    if len(dados_roles) >= 2:
        nomes_roles = dados_roles[0]
        qtds_roles  = dados_roles[1]
        roles_played = {
            nome_role: _safe_int(qtd)
            for nome_role, qtd in zip(nomes_roles, qtds_roles)
            if nome_role and nome_role.strip() and nome_role != "-"
        }

    stats = {
        # --- GENERAL STATS ---
        "good_games_won":           _cell(dados, "D2"),
        "evil_games_won":           _cell(dados, "D3"),
        "good_games_lost":          _cell(dados, "D4"),
        "evil_games_lost":          _cell(dados, "D5"),

        "gawain_games_won":         _cell(dados, "F2"),
        "nimue_games_won":          _cell(dados, "F3"),
        "gawain_games_lost":        _cell(dados, "F4"),
        "nimue_games_lost":         _cell(dados, "F5"),

        "total_games_played":       _cell(dados, "F6"),

        "good_role_won_most":       _cell(dados, "H2"),
        "evil_role_won_most":       _cell(dados, "H3"),
        "good_role_lost_most":      _cell(dados, "H4"),
        "evil_role_lost_most":      _cell(dados, "H5"),

        # --- DUO STATS ---
        "duo_good_games_won":       _cell(dados, "D9"),
        "duo_evil_games_won":       _cell(dados, "D10"),
        "duo_good_games_lost":      _cell(dados, "D11"),
        "duo_evil_games_lost":      _cell(dados, "D12"),

        "duo_gawain_games_won":     _cell(dados, "F9"),
        "duo_nimue_games_won":      _cell(dados, "F10"),
        "duo_gawain_games_lost":    _cell(dados, "F11"),
        "duo_nimue_games_lost":     _cell(dados, "F12"),

        "duo_good_role_won_most":   _cell(dados, "H9"),
        "duo_evil_role_won_most":   _cell(dados, "H10"),
        "duo_good_role_lost_most":  _cell(dados, "H11"),
        "duo_evil_role_lost_most":  _cell(dados, "H12"),

        "duo_good_win_ratio":       _cell(dados, "J9"),
        "duo_evil_win_ratio":       _cell(dados, "J10"),
        "duo_good_loss_ratio":      _cell(dados, "J11"),
        "duo_evil_loss_ratio":      _cell(dados, "J12"),

        # --- GM STATS ---
        "gm_single":                _cell(dados, "C16"),
        "gm_duo":                   _cell(dados, "D16"),
        "gm_triple":                _cell(dados, "E16"),
        "gm_solo":                  _cell(dados, "F16"),
        "gm_pairs":                 _cell(dados, "G16"),
        "gm_mixed":                 _cell(dados, "H16"),
        "total_games_gmed":         _cell(dados, "I16"),

        # --- VOTES ---
        "death_toll":               _cell(dados, "C23"),
        "correct_vote_ratio":       _cell(dados, "E23"),
        "incorrect_vote_ratio":     _cell(dados, "G23"),
        "how_many_times_voted":     _cell(dados, "I23"),
        "correct_votes":            _cell(dados, "E26"),
        "incorrect_votes":          _cell(dados, "G26"),

        # --- DATES ---
        "date_started_playing":     _cell(dados, "C26"),
        "date_last_played":         _cell(dados, "I26"),
        "everyone_wins_games":      _cell(dados, "E29"),

        # --- ROLES ---
        "role_played_most":         _cell(dados, "C29"),
        "role_played_least":        _cell(dados, "C32"),
        "role_last_played":         _cell(dados, "I29"),
        "good_role_played_most":    _cell(dados, "C35"),
        "evil_role_played_most":    _cell(dados, "C38"),

        # --- STREAKS ---
        "last_date_evil":           _cell(dados, "C41"),
        "last_date_good":           _cell(dados, "C44"),
        "evil_streak":              _cell(dados, "E41"),
        "good_streak":              _cell(dados, "E44"),
        "last_evil_role":           _cell(dados, "G41"),
        "last_good_role":           _cell(dados, "G44"),
        "longest_evil_streak":      _cell(dados, "I41"),
        "longest_good_streak":      _cell(dados, "I44"),
        "longest_game_streak":      _cell(dados, "C47"),
        "current_game_streak":      _cell(dados, "E47"),

        # --- ROLES PLAYED ---
        "roles_played":             roles_played,
    }

    return stats


# ==============================================================================
# Cache — salvar e carregar do arquivo
# ==============================================================================

def _save_cache():
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(stats_cache, f, indent=4, ensure_ascii=False)
    print("[sheets] Cache salvo em stats_cache.json")


def _load_cache_from_file() -> bool:
    if not os.path.exists(CACHE_FILE):
        return False
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    stats_cache.update(data)
    print(f"[sheets] Cache carregado do arquivo ({len(data)} jogadores)")
    return True


def load_all_players(force: bool = False):
    if not force and _load_cache_from_file():
        return

    print(f"[sheets] Buscando {len(nomes)} jogadores no Sheets...")
    for nome in nomes:
        print(f"[sheets] → {nome}")
        stats_cache[nome.lower()] = _fetch_player_stats(nome)
        time.sleep(1)

    # Integra estatísticas de morte separadas
    all_death, duo_death = compute_death_stats()

    # Single / outros → sem prefixo
    for player_name, death_dict in all_death.items():
        key = player_name.lower()
        if key in stats_cache:
            stats_cache[key].update(death_dict)
        else:
            stats_cache[key] = death_dict

    # Duo → adiciona com prefixo duo_
    for player_name, duo_dict in duo_death.items():
        key = player_name.lower()
        if key in stats_cache:
            for k, v in duo_dict.items():
                stats_cache[key][f"duo_{k}"] = v
        else:
            stats_cache[key] = {f"duo_{k}": v for k, v in duo_dict.items()}

    _save_cache()
    print("[sheets] Cache completo (com mortes separadas)!")


def get_player_stats(nome: str) -> dict | None:
    return stats_cache.get(nome.lower())


def refresh_player(nome: str) -> dict:
    stats = _fetch_player_stats(nome)

    all_death, duo_death = compute_death_stats()
    key = nome.lower()

    if key in all_death:
        stats.update(all_death[key])
    if key in duo_death:
        for k, v in duo_death[key].items():
            stats[f"duo_{k}"] = v

    stats_cache[key] = stats
    _save_cache()
    return stats