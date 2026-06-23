import os
import json
import gspread
from google.oauth2.service_account import Credentials

from utils_config import _fuzzy_match_name_local, SHEET_NAME

# nome do cache segue o mesmo padrão dev/prod
_MODE            = os.getenv("BOT_MODE", "prod").lower()
ROLES_CACHE_FILE = f"cache_roles_{_MODE}.json"

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

creds        = Credentials.from_service_account_file("green_credentials.json", scopes=scopes)
client       = gspread.authorize(creds)
planilha     = client.open(SHEET_NAME)
pagina_roles = planilha.worksheet("Role Stats")

ALL_ROLES = [
    # Evil
    "Assassin", "Bertilak", "Dagonet", "Lucius", "Maduc", "Mark",
    "Meleagant", "Mordred", "Morgana", "Oberon", "Puck", "Queen Mab",
    "Vortigern", "Minion", "Bad Lancelot", "Nimue (E)", "The Witch of Caerlloyw",
    # Good
    "Merlin", "Apprentice", "Caelia", "Elaine", "Galahad", "Gawain",
    "Guinevere", "King Arthur", "Palamedes", "Percival", "Sir Kay",
    "Loyal Servant", "Tristan", "Iseult", "Lancelot", "Nimue (G)", "Penpingion", "Untrustworthy Servant",
]

roles_cache: dict = {}


# ==============================================================================
# Helpers
# ==============================================================================

def _safe_int(value) -> int:
    try:
        return int(value) if value else 0
    except (ValueError, TypeError):
        return 0


def _cell(dados: list, a1: str):
    col_str, row_str = "", ""
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


def _col_values_trimmed(dados: list, col_letter: str, row_start: int, row_end: int) -> list[str]:
    col_idx = 0
    for ch in col_letter.upper():
        col_idx = col_idx * 26 + (ord(ch) - ord('A') + 1)
    col_idx -= 1

    skip = {
        "how many games played", "duo games", "april fools",
        "killed how many", "oops all pen", "everyone wins",
        "player most", "player least", "games won", "games lost",
        "gawain loss", "nimue tie/loss", "nimu tie/loss", ""
    }

    result = []
    for row_idx in range(row_start - 1, row_end):
        try:
            val = dados[row_idx][col_idx].strip()
            if val and val.lower() not in skip:
                result.append(val)
        except IndexError:
            pass
    return result


# ==============================================================================
# Cache
# ==============================================================================

def _save_roles_cache():
    with open(ROLES_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(roles_cache, f, indent=4, ensure_ascii=False)
    print(f"[roles] Cache salvo em {ROLES_CACHE_FILE}")


def _load_roles_cache_from_file() -> bool:
    if not os.path.exists(ROLES_CACHE_FILE):
        return False
    with open(ROLES_CACHE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    roles_cache.update(data)
    print(f"[roles] Cache carregado de {ROLES_CACHE_FILE} ({len(data)} roles)")
    return True


def get_role_stats(role_name: str) -> dict | None:
    return roles_cache.get(role_name.lower())


# ==============================================================================
# Carregamento explícito de cada role
# ==============================================================================

def load_all_roles(force: bool = False):
    if not force and _load_roles_cache_from_file():
        return

    print(f"[roles] Buscando todos os roles no Sheets ({SHEET_NAME})...")
    dados = pagina_roles.get_all_values()

    # ------------------------------------------------------------
    # 1. EVIL ROLES (blocos A-G)
    # ------------------------------------------------------------

    roles_cache["assassin"] = {
        "how_many_played":  _safe_int(_cell(dados, "A4")),
        "duo_games":        _safe_int(_cell(dados, "A7")),
        "april_fools":      _safe_int(_cell(dados, "A12")),
        "games_won":        _safe_int(_cell(dados, "D4")),
        "games_lost":       _safe_int(_cell(dados, "E4")),
        "gawain_loss":      _safe_int(_cell(dados, "F4")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "G4")),
        "killed_how_many":  _safe_int(_cell(dados, "A16")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "B", 3, 6),
        "player_least":     _col_values_trimmed(dados, "C", 3, 6),
    }

    roles_cache["bertilak"] = {
        "how_many_played":  _safe_int(_cell(dados, "A25")),
        "duo_games":        _safe_int(_cell(dados, "A28")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "D25")),
        "games_lost":       _safe_int(_cell(dados, "E25")),
        "gawain_loss":      _safe_int(_cell(dados, "F25")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "G25")),
        "killed_how_many":  _safe_int(_cell(dados, "A37")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "B", 25, 28),
        "player_least":     _col_values_trimmed(dados, "C", 25, 28),
    }

    roles_cache["dagonet"] = {
        "how_many_played":  _safe_int(_cell(dados, "A47")),
        "duo_games":        _safe_int(_cell(dados, "A50")),
        "april_fools":      _safe_int(_cell(dados, "A55")),
        "games_won":        _safe_int(_cell(dados, "D47")),
        "games_lost":       _safe_int(_cell(dados, "E47")),
        "gawain_loss":      _safe_int(_cell(dados, "F47")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "G47")),
        "killed_how_many":  _safe_int(_cell(dados, "A56")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "B", 47, 50),
        "player_least":     _col_values_trimmed(dados, "C", 47, 50),
    }

    roles_cache["lucius"] = {
        "how_many_played":  _safe_int(_cell(dados, "A69")),
        "duo_games":        _safe_int(_cell(dados, "A72")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "D69")),
        "games_lost":       _safe_int(_cell(dados, "E69")),
        "gawain_loss":      _safe_int(_cell(dados, "F69")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "G69")),
        "killed_how_many":  _safe_int(_cell(dados, "A81")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "B", 69, 72),
        "player_least":     _col_values_trimmed(dados, "C", 69, 72),
    }

    roles_cache["maduc"] = {
        "how_many_played":  _safe_int(_cell(dados, "A91")),
        "duo_games":        _safe_int(_cell(dados, "A93")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "D91")),
        "games_lost":       _safe_int(_cell(dados, "E91")),
        "gawain_loss":      _safe_int(_cell(dados, "F91")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "G91")),
        "killed_how_many":  _safe_int(_cell(dados, "A103")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "B", 91, 94),
        "player_least":     _col_values_trimmed(dados, "C", 91, 94),
    }

    roles_cache["mark"] = {
        "how_many_played":  _safe_int(_cell(dados, "A113")),
        "duo_games":        _safe_int(_cell(dados, "A116")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "D113")),
        "games_lost":       _safe_int(_cell(dados, "E113")),
        "gawain_loss":      _safe_int(_cell(dados, "F113")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "G113")),
        "killed_how_many":  _safe_int(_cell(dados, "A125")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "B", 113, 116),
        "player_least":     _col_values_trimmed(dados, "C", 113, 116),
    }

    roles_cache["meleagant"] = {
        "how_many_played":  _safe_int(_cell(dados, "A135")),
        "duo_games":        _safe_int(_cell(dados, "A138")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "D135")),
        "games_lost":       _safe_int(_cell(dados, "E135")),
        "gawain_loss":      _safe_int(_cell(dados, "F135")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "G135")),
        "killed_how_many":  _safe_int(_cell(dados, "A147")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "B", 135, 138),
        "player_least":     _col_values_trimmed(dados, "C", 135, 138),
    }

    roles_cache["mordred"] = {
        "how_many_played":  _safe_int(_cell(dados, "A157")),
        "duo_games":        _safe_int(_cell(dados, "A162")),
        "april_fools":      _safe_int(_cell(dados, "A165")),
        "games_won":        _safe_int(_cell(dados, "D157")),
        "games_lost":       _safe_int(_cell(dados, "E157")),
        "gawain_loss":      _safe_int(_cell(dados, "F157")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "G157")),
        "killed_how_many":  _safe_int(_cell(dados, "A169")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "B", 157, 160),
        "player_least":     _col_values_trimmed(dados, "C", 157, 160),
    }

    roles_cache["morgana"] = {
        "how_many_played":  _safe_int(_cell(dados, "A179")),
        "duo_games":        _safe_int(_cell(dados, "A182")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "D179")),
        "games_lost":       _safe_int(_cell(dados, "E179")),
        "gawain_loss":      _safe_int(_cell(dados, "F179")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "G179")),
        "killed_how_many":  _safe_int(_cell(dados, "A191")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "B", 179, 182),
        "player_least":     _col_values_trimmed(dados, "C", 179, 182),
    }

    roles_cache["oberon"] = {
        "how_many_played":  _safe_int(_cell(dados, "A201")),
        "duo_games":        _safe_int(_cell(dados, "A204")),
        "april_fools":      _safe_int(_cell(dados, "A207")),
        "games_won":        _safe_int(_cell(dados, "D201")),
        "games_lost":       _safe_int(_cell(dados, "E201")),
        "gawain_loss":      _safe_int(_cell(dados, "F201")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "G201")),
        "killed_how_many":  _safe_int(_cell(dados, "A213")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "B", 201, 204),
        "player_least":     _col_values_trimmed(dados, "C", 201, 204),
    }

    roles_cache["puck"] = {
        "how_many_played":  _safe_int(_cell(dados, "A223")),
        "duo_games":        _safe_int(_cell(dados, "A226")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "D223")),
        "games_lost":       _safe_int(_cell(dados, "E223")),
        "gawain_loss":      _safe_int(_cell(dados, "F223")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "G223")),
        "killed_how_many":  _safe_int(_cell(dados, "A235")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "B", 223, 226),
        "player_least":     _col_values_trimmed(dados, "C", 223, 226),
    }

    roles_cache["queen mab"] = {
        "how_many_played":  _safe_int(_cell(dados, "A245")),
        "duo_games":        _safe_int(_cell(dados, "A248")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "D245")),
        "games_lost":       _safe_int(_cell(dados, "E245")),
        "gawain_loss":      _safe_int(_cell(dados, "F245")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "G245")),
        "killed_how_many":  _safe_int(_cell(dados, "A257")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "B", 245, 248),
        "player_least":     _col_values_trimmed(dados, "C", 245, 248),
    }

    roles_cache["vortigern"] = {
        "how_many_played":  _safe_int(_cell(dados, "A267")),
        "duo_games":        _safe_int(_cell(dados, "A273")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "D267")),
        "games_lost":       _safe_int(_cell(dados, "E267")),
        "gawain_loss":      _safe_int(_cell(dados, "F267")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "G267")),
        "killed_how_many":  _safe_int(_cell(dados, "A281")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "B", 267, 270),
        "player_least":     _col_values_trimmed(dados, "C", 267, 270),
    }

    roles_cache["minion"] = {
        "how_many_played":  _safe_int(_cell(dados, "A289")),
        "duo_games":        _safe_int(_cell(dados, "A292")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "D289")),
        "games_lost":       _safe_int(_cell(dados, "E289")),
        "gawain_loss":      _safe_int(_cell(dados, "F289")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "G289")),
        "killed_how_many":  _safe_int(_cell(dados, "A301")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "B", 289, 292),
        "player_least":     _col_values_trimmed(dados, "C", 289, 292),
    }

    roles_cache["bad lancelot"] = {
        "how_many_played":  _safe_int(_cell(dados, "A311")),
        "duo_games":        _safe_int(_cell(dados, "A314")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "D311")),
        "games_lost":       _safe_int(_cell(dados, "E311")),
        "gawain_loss":      _safe_int(_cell(dados, "F311")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "G311")),
        "killed_how_many":  _safe_int(_cell(dados, "A323")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "B", 311, 314),
        "player_least":     _col_values_trimmed(dados, "C", 311, 314),
    }

    roles_cache["nimue (e)"] = {
        "how_many_played":  _safe_int(_cell(dados, "A333")),
        "duo_games":        _safe_int(_cell(dados, "A336")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "D333")),
        "games_lost":       _safe_int(_cell(dados, "E333")),
        "gawain_loss":      _safe_int(_cell(dados, "F333")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "G333")),
        "killed_how_many":  _safe_int(_cell(dados, "A345")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "B", 333, 336),
        "player_least":     _col_values_trimmed(dados, "C", 333, 336),
    }

    roles_cache["the witch of caerlloyw"] = {
        "how_many_played":  _safe_int(_cell(dados, "A355")),
        "duo_games":        _safe_int(_cell(dados, "A358")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "D355")),
        "games_lost":       _safe_int(_cell(dados, "E355")),
        "gawain_loss":      _safe_int(_cell(dados, "F355")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "G355")),
        "killed_how_many":  _safe_int(_cell(dados, "A364")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "B", 355, 358),
        "player_least":     _col_values_trimmed(dados, "C", 355, 358),
    }

    # ------------------------------------------------------------
    # 2. GOOD ROLES (blocos I-O)
    # ------------------------------------------------------------

    roles_cache["merlin"] = {
        "how_many_played":  _safe_int(_cell(dados, "I4")),
        "duo_games":        _safe_int(_cell(dados, "I7")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "L4")),
        "games_lost":       _safe_int(_cell(dados, "M4")),
        "gawain_loss":      _safe_int(_cell(dados, "N4")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "O4")),
        "killed_how_many":  _safe_int(_cell(dados, "I16")),
        "oops_all_pen":     _safe_int(_cell(dados, "I21")),
        "player_most":      _col_values_trimmed(dados, "J", 3, 6),
        "player_least":     _col_values_trimmed(dados, "K", 3, 6),
    }

    roles_cache["apprentice"] = {
        "how_many_played":  _safe_int(_cell(dados, "I25")),
        "duo_games":        _safe_int(_cell(dados, "I28")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "L25")),
        "games_lost":       _safe_int(_cell(dados, "M25")),
        "gawain_loss":      _safe_int(_cell(dados, "N25")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "O25")),
        "killed_how_many":  _safe_int(_cell(dados, "I37")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "J", 25, 28),
        "player_least":     _col_values_trimmed(dados, "K", 25, 28),
    }

    roles_cache["caelia"] = {
        "how_many_played":  _safe_int(_cell(dados, "I47")),
        "duo_games":        _safe_int(_cell(dados, "I50")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "L47")),
        "games_lost":       _safe_int(_cell(dados, "M47")),
        "gawain_loss":      _safe_int(_cell(dados, "N47")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "O47")),
        "killed_how_many":  _safe_int(_cell(dados, "I58")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "J", 47, 50),
        "player_least":     _col_values_trimmed(dados, "K", 47, 50),
    }

    roles_cache["elaine"] = {
        "how_many_played":  _safe_int(_cell(dados, "I69")),
        "duo_games":        _safe_int(_cell(dados, "I72")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "L69")),
        "games_lost":       _safe_int(_cell(dados, "M69")),
        "gawain_loss":      _safe_int(_cell(dados, "N69")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "O69")),
        "killed_how_many":  _safe_int(_cell(dados, "I81")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "J", 69, 72),
        "player_least":     _col_values_trimmed(dados, "K", 69, 72),
    }

    roles_cache["galahad"] = {
        "how_many_played":  _safe_int(_cell(dados, "I91")),
        "duo_games":        _safe_int(_cell(dados, "I94")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "L91")),
        "games_lost":       _safe_int(_cell(dados, "M91")),
        "gawain_loss":      _safe_int(_cell(dados, "N91")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "O91")),
        "killed_how_many":  _safe_int(_cell(dados, "I103")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "J", 91, 94),
        "player_least":     _col_values_trimmed(dados, "K", 91, 94),
    }

    roles_cache["gawain"] = {
        "how_many_played":  _safe_int(_cell(dados, "I113")),
        "duo_games":        _safe_int(_cell(dados, "I113")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "L113")),
        "games_lost":       _safe_int(_cell(dados, "M113")),
        "gawain_loss":      _safe_int(_cell(dados, "N113")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "O113")),
        "killed_how_many":  _safe_int(_cell(dados, "I126")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "J", 113, 116),
        "player_least":     _col_values_trimmed(dados, "K", 113, 116),
    }

    roles_cache["guinevere"] = {
        "how_many_played":  _safe_int(_cell(dados, "I135")),
        "duo_games":        _safe_int(_cell(dados, "I138")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "L135")),
        "games_lost":       _safe_int(_cell(dados, "M135")),
        "gawain_loss":      _safe_int(_cell(dados, "N135")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "O135")),
        "killed_how_many":  _safe_int(_cell(dados, "I146")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "J", 135, 138),
        "player_least":     _col_values_trimmed(dados, "K", 135, 138),
    }

    roles_cache["king arthur"] = {
        "how_many_played":  _safe_int(_cell(dados, "I157")),
        "duo_games":        _safe_int(_cell(dados, "I160")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "L157")),
        "games_lost":       _safe_int(_cell(dados, "M157")),
        "gawain_loss":      _safe_int(_cell(dados, "N157")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "O157")),
        "killed_how_many":  _safe_int(_cell(dados, "I169")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "J", 157, 160),
        "player_least":     _col_values_trimmed(dados, "K", 157, 160),
    }

    roles_cache["palamedes"] = {
        "how_many_played":  _safe_int(_cell(dados, "I179")),
        "duo_games":        _safe_int(_cell(dados, "I182")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "L179")),
        "games_lost":       _safe_int(_cell(dados, "M179")),
        "gawain_loss":      _safe_int(_cell(dados, "N179")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "O179")),
        "killed_how_many":  _safe_int(_cell(dados, "I191")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "J", 179, 182),
        "player_least":     _col_values_trimmed(dados, "K", 179, 182),
    }

    roles_cache["percival"] = {
        "how_many_played":  _safe_int(_cell(dados, "I201")),
        "duo_games":        _safe_int(_cell(dados, "I204")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "L201")),
        "games_lost":       _safe_int(_cell(dados, "M201")),
        "gawain_loss":      _safe_int(_cell(dados, "N201")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "O201")),
        "killed_how_many":  _safe_int(_cell(dados, "I213")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "J", 201, 204),
        "player_least":     _col_values_trimmed(dados, "K", 201, 204),
    }

    roles_cache["sir kay"] = {
        "how_many_played":  _safe_int(_cell(dados, "I223")),
        "duo_games":        _safe_int(_cell(dados, "I226")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "L223")),
        "games_lost":       _safe_int(_cell(dados, "M223")),
        "gawain_loss":      _safe_int(_cell(dados, "N223")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "O223")),
        "killed_how_many":  _safe_int(_cell(dados, "I235")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "J", 223, 226),
        "player_least":     _col_values_trimmed(dados, "K", 223, 226),
    }

    roles_cache["loyal servant"] = {
        "how_many_played":  _safe_int(_cell(dados, "I245")),
        "duo_games":        _safe_int(_cell(dados, "I248")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "L245")),
        "games_lost":       _safe_int(_cell(dados, "M245")),
        "gawain_loss":      _safe_int(_cell(dados, "N245")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "O245")),
        "killed_how_many":  _safe_int(_cell(dados, "I257")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "J", 245, 248),
        "player_least":     _col_values_trimmed(dados, "K", 245, 248),
    }

    roles_cache["tristan"] = {
        "how_many_played":  _safe_int(_cell(dados, "I267")),
        "duo_games":        _safe_int(_cell(dados, "I270")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "L267")),
        "games_lost":       _safe_int(_cell(dados, "M267")),
        "gawain_loss":      _safe_int(_cell(dados, "N267")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "O267")),
        "killed_how_many":  _safe_int(_cell(dados, "I281")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "J", 267, 270),
        "player_least":     _col_values_trimmed(dados, "K", 267, 270),
    }

    roles_cache["iseult"] = {
        "how_many_played":  _safe_int(_cell(dados, "I289")),
        "duo_games":        _safe_int(_cell(dados, "I294")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "L289")),
        "games_lost":       _safe_int(_cell(dados, "M289")),
        "gawain_loss":      _safe_int(_cell(dados, "N289")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "O289")),
        "killed_how_many":  _safe_int(_cell(dados, "I301")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "J", 289, 292),
        "player_least":     _col_values_trimmed(dados, "K", 289, 292),
    }

    roles_cache["lancelot"] = {
        "how_many_played":  _safe_int(_cell(dados, "I311")),
        "duo_games":        _safe_int(_cell(dados, "I314")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "L311")),
        "games_lost":       _safe_int(_cell(dados, "M311")),
        "gawain_loss":      _safe_int(_cell(dados, "N311")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "O311")),
        "killed_how_many":  _safe_int(_cell(dados, "I323")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "J", 311, 314),
        "player_least":     _col_values_trimmed(dados, "K", 311, 314),
    }

    roles_cache["nimue (g)"] = {
        "how_many_played":  _safe_int(_cell(dados, "I333")),
        "duo_games":        _safe_int(_cell(dados, "I333")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "L333")),
        "games_lost":       _safe_int(_cell(dados, "M333")),
        "gawain_loss":      _safe_int(_cell(dados, "N333")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "O333")),
        "killed_how_many":  _safe_int(_cell(dados, "I345")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "J", 333, 336),
        "player_least":     _col_values_trimmed(dados, "K", 333, 336),
    }

    
    roles_cache["penpingion"] = {
        "how_many_played":  _safe_int(_cell(dados, "I355")),
        "duo_games":        _safe_int(_cell(dados, "I358")),
        "april_fools":      0,
        "games_won":        _safe_int(_cell(dados, "L355")),
        "games_lost":       _safe_int(_cell(dados, "M355")),
        "gawain_loss":      _safe_int(_cell(dados, "N355")),
        "nimue_tie_loss":   _safe_int(_cell(dados, "O355")),
        "killed_how_many":  _safe_int(_cell(dados, "I364")),
        "oops_all_pen":     0,
        "player_most":      _col_values_trimmed(dados, "J", 355, 358),
        "player_least":     _col_values_trimmed(dados, "K", 355, 358),
    }
    
    roles_cache["untrustworthy servant"] = {
            "how_many_played":  _safe_int(_cell(dados, "I376")),
            "duo_games":        _safe_int(_cell(dados, "I358")),
            "april_fools":      0,
            "games_won":        _safe_int(_cell(dados, "L376")),
            "games_lost":       _safe_int(_cell(dados, "M376")),
            "gawain_loss":      _safe_int(_cell(dados, "N376")),
            "nimue_tie_loss":   _safe_int(_cell(dados, "O376")),
            "killed_how_many":  _safe_int(_cell(dados, "I390")),
            "oops_all_pen":     0,
            "player_most":      _col_values_trimmed(dados, "J", 377, 379),
            "player_least":     _col_values_trimmed(dados, "K", 377, 379),
        }
    _save_roles_cache()
    print(f"[roles] Cache completo ({len(roles_cache)} roles).")


# ==============================================================================
# Refresh de uma role específica
# ==============================================================================

def refresh_role(role_name: str) -> dict | None:
    """Recarrega uma role específica da planilha e atualiza o cache."""
    role_key = role_name.strip().lower()
    print(f"[roles] Refrescando '{role_key}'...")
    dados = pagina_roles.get_all_values()

    # Recarrega todas as roles do dados já lido e pega só a que interessa
    temp_cache = {}
    _roles_cache_backup = dict(roles_cache)

    load_all_roles(force=True)

    result = roles_cache.get(role_key)
    if result is None:
        print(f"[roles] Role '{role_key}' não encontrada.")
    return result