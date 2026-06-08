import os
import json
import time
import gspread
from google.oauth2.service_account import Credentials

from utils_config import _fuzzy_match_name_local

ROLES_CACHE_FILE = "cache_roles.json"

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file("green_credentials.json", scopes=scopes)
client = gspread.authorize(creds)

planilha = client.open("TESTE")
pagina_roles = planilha.worksheet("Role Stats")

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


def _col_values_trimmed(dados: list, col_a1: str, row_start: int, row_end: int) -> list[str]:
    """Pega nomes de uma coluna entre duas linhas, remove vazios e labels."""
    col_str = ""
    for ch in col_a1:
        if ch.isalpha():
            col_str += ch
        else:
            break
    col_idx = 0
    for ch in col_str.upper():
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
# Mapeamento de cada role → células na sheet "Role Stats"
# Gerado automaticamente a partir do índice do bloco (BLOCK_SIZE = 22 linhas)
# Evil roles: colunas A-G | Good roles: colunas I-O
# Edite apenas april_fools e oops_all_pen se um role específico tiver ou não
# ==============================================================================

ROLE_MAP = {

    # ==========================================================================
    # EVIL ROLES
    # ==========================================================================

    "Assassin": {
        # bloco linha 1–22 | col A-G
        "how_many_played":  "A3",
        "duo_games":        "A8",
        "april_fools":      "A10",
        "games_won":        "D3",
        "games_lost":       "E3",
        "gawain_loss":      "F3",
        "nimue_tie_loss":   "G3",
        "killed_how_many":  "A12",
        "oops_all_pen":     None,
        "player_most_col":  ("B", 3, 6),
        "player_least_col": ("C", 3, 6),
    },

    "Bertilak": {
        # bloco linha 23–44 | col A-G
        "how_many_played":  "A25",
        "duo_games":        "A30",
        "april_fools":      None,
        "games_won":        "D25",
        "games_lost":       "E25",
        "gawain_loss":      "F25",
        "nimue_tie_loss":   "G25",
        "killed_how_many":  "A34",
        "oops_all_pen":     None,
        "player_most_col":  ("B", 25, 28),
        "player_least_col": ("C", 25, 28),
    },

    "Dagonet": {
        # bloco linha 45–66 | col A-G
        "how_many_played":  "A47",
        "duo_games":        "A52",
        "april_fools":      "A54",
        "games_won":        "D47",
        "games_lost":       "E47",
        "gawain_loss":      "F47",
        "nimue_tie_loss":   "G47",
        "killed_how_many":  "A56",
        "oops_all_pen":     None,
        "player_most_col":  ("B", 47, 50),
        "player_least_col": ("C", 47, 50),
    },

    "Lucius": {
        # bloco linha 67–88 | col A-G
        "how_many_played":  "A69",
        "duo_games":        "A74",
        "april_fools":      None,
        "games_won":        "D69",
        "games_lost":       "E69",
        "gawain_loss":      "F69",
        "nimue_tie_loss":   "G69",
        "killed_how_many":  "A78",
        "oops_all_pen":     None,
        "player_most_col":  ("B", 69, 72),
        "player_least_col": ("C", 69, 72),
    },

    "Maduc": {
        # bloco linha 89–110 | col A-G
        "how_many_played":  "A91",
        "duo_games":        "A96",
        "april_fools":      None,
        "games_won":        "D91",
        "games_lost":       "E91",
        "gawain_loss":      "F91",
        "nimue_tie_loss":   "G91",
        "killed_how_many":  "A100",
        "oops_all_pen":     None,
        "player_most_col":  ("B", 91, 94),
        "player_least_col": ("C", 91, 94),
    },

    "Mark": {
        # bloco linha 111–132 | col A-G
        "how_many_played":  "A113",
        "duo_games":        "A118",
        "april_fools":      None,
        "games_won":        "D113",
        "games_lost":       "E113",
        "gawain_loss":      "F113",
        "nimue_tie_loss":   "G113",
        "killed_how_many":  "A122",
        "oops_all_pen":     None,
        "player_most_col":  ("B", 113, 116),
        "player_least_col": ("C", 113, 116),
    },

    "Meleagant": {
        # bloco linha 133–154 | col A-G
        "how_many_played":  "A135",
        "duo_games":        "A140",
        "april_fools":      None,
        "games_won":        "D135",
        "games_lost":       "E135",
        "gawain_loss":      "F135",
        "nimue_tie_loss":   "G135",
        "killed_how_many":  "A144",
        "oops_all_pen":     None,
        "player_most_col":  ("B", 135, 138),
        "player_least_col": ("C", 135, 138),
    },

    "Mordred": {
        # bloco linha 155–176 | col A-G
        "how_many_played":  "A157",
        "duo_games":        "A162",
        "april_fools":      None,
        "games_won":        "D157",
        "games_lost":       "E157",
        "gawain_loss":      "F157",
        "nimue_tie_loss":   "G157",
        "killed_how_many":  "A166",
        "oops_all_pen":     None,
        "player_most_col":  ("B", 157, 160),
        "player_least_col": ("C", 157, 160),
    },

    "Morgana": {
        # bloco linha 177–198 | col A-G
        "how_many_played":  "A179",
        "duo_games":        "A184",
        "april_fools":      None,
        "games_won":        "D179",
        "games_lost":       "E179",
        "gawain_loss":      "F179",
        "nimue_tie_loss":   "G179",
        "killed_how_many":  "A188",
        "oops_all_pen":     None,
        "player_most_col":  ("B", 179, 182),
        "player_least_col": ("C", 179, 182),
    },

    "Oberon": {
        # bloco linha 199–220 | col A-G
        "how_many_played":  "A201",
        "duo_games":        "A206",
        "april_fools":      None,
        "games_won":        "D201",
        "games_lost":       "E201",
        "gawain_loss":      "F201",
        "nimue_tie_loss":   "G201",
        "killed_how_many":  "A210",
        "oops_all_pen":     None,
        "player_most_col":  ("B", 201, 204),
        "player_least_col": ("C", 201, 204),
    },

    "Puck": {
        # bloco linha 221–242 | col A-G
        "how_many_played":  "A223",
        "duo_games":        "A228",
        "april_fools":      None,
        "games_won":        "D223",
        "games_lost":       "E223",
        "gawain_loss":      "F223",
        "nimue_tie_loss":   "G223",
        "killed_how_many":  "A232",
        "oops_all_pen":     None,
        "player_most_col":  ("B", 223, 226),
        "player_least_col": ("C", 223, 226),
    },

    "Queen Mab": {
        # bloco linha 243–264 | col A-G
        "how_many_played":  "A245",
        "duo_games":        "A250",
        "april_fools":      None,
        "games_won":        "D245",
        "games_lost":       "E245",
        "gawain_loss":      "F245",
        "nimue_tie_loss":   "G245",
        "killed_how_many":  "A254",
        "oops_all_pen":     None,
        "player_most_col":  ("B", 245, 248),
        "player_least_col": ("C", 245, 248),
    },

    "Vortigern": {
        # bloco linha 265–286 | col A-G
        "how_many_played":  "A267",
        "duo_games":        "A272",
        "april_fools":      None,
        "games_won":        "D267",
        "games_lost":       "E267",
        "gawain_loss":      "F267",
        "nimue_tie_loss":   "G267",
        "killed_how_many":  "A276",
        "oops_all_pen":     None,
        "player_most_col":  ("B", 267, 270),
        "player_least_col": ("C", 267, 270),
    },

    "Minion": {
        # bloco linha 287–308 | col A-G
        "how_many_played":  "A289",
        "duo_games":        "A294",
        "april_fools":      None,
        "games_won":        "D289",
        "games_lost":       "E289",
        "gawain_loss":      "F289",
        "nimue_tie_loss":   "G289",
        "killed_how_many":  "A298",
        "oops_all_pen":     None,
        "player_most_col":  ("B", 289, 292),
        "player_least_col": ("C", 289, 292),
    },

    "Bad Lancelot": {
        # bloco linha 309–330 | col A-G
        "how_many_played":  "A311",
        "duo_games":        "A316",
        "april_fools":      None,
        "games_won":        "D311",
        "games_lost":       "E311",
        "gawain_loss":      "F311",
        "nimue_tie_loss":   "G311",
        "killed_how_many":  "A320",
        "oops_all_pen":     None,
        "player_most_col":  ("B", 311, 314),
        "player_least_col": ("C", 311, 314),
    },

    "Nimue (E)": {
        # bloco linha 331–352 | col A-G
        "how_many_played":  "A333",
        "duo_games":        "A338",
        "april_fools":      None,
        "games_won":        "D333",
        "games_lost":       "E333",
        "gawain_loss":      "F333",
        "nimue_tie_loss":   "G333",
        "killed_how_many":  "A342",
        "oops_all_pen":     None,
        "player_most_col":  ("B", 333, 336),
        "player_least_col": ("C", 333, 336),
    },

    "The Witch of Caerlloyw": {
        # bloco linha 353–374 | col A-G
        "how_many_played":  "A355",
        "duo_games":        "A360",
        "april_fools":      None,
        "games_won":        "D355",
        "games_lost":       "E355",
        "gawain_loss":      "F355",
        "nimue_tie_loss":   "G355",
        "killed_how_many":  "A364",
        "oops_all_pen":     None,
        "player_most_col":  ("B", 355, 358),
        "player_least_col": ("C", 355, 358),
    },

    # ==========================================================================
    # GOOD ROLES
    # ==========================================================================

    "Merlin": {
        # bloco linha 1–22 | col I-O
        "how_many_played":  "I3",
        "duo_games":        "I8",
        "april_fools":      None,
        "games_won":        "L3",
        "games_lost":       "M3",
        "gawain_loss":      "N3",
        "nimue_tie_loss":   "O3",
        "killed_how_many":  "I12",
        "oops_all_pen":     "I14",
        "player_most_col":  ("J", 3, 6),
        "player_least_col": ("K", 3, 6),
    },

    "Apprentice": {
        # bloco linha 23–44 | col I-O
        "how_many_played":  "I25",
        "duo_games":        "I30",
        "april_fools":      None,
        "games_won":        "L25",
        "games_lost":       "M25",
        "gawain_loss":      "N25",
        "nimue_tie_loss":   "O25",
        "killed_how_many":  "I34",
        "oops_all_pen":     None,
        "player_most_col":  ("J", 25, 28),
        "player_least_col": ("K", 25, 28),
    },

    "Caelia": {
        # bloco linha 45–66 | col I-O
        "how_many_played":  "I47",
        "duo_games":        "I52",
        "april_fools":      None,
        "games_won":        "L47",
        "games_lost":       "M47",
        "gawain_loss":      "N47",
        "nimue_tie_loss":   "O47",
        "killed_how_many":  "I56",
        "oops_all_pen":     None,
        "player_most_col":  ("J", 47, 50),
        "player_least_col": ("K", 47, 50),
    },

    "Elaine": {
        # bloco linha 67–88 | col I-O
        "how_many_played":  "I69",
        "duo_games":        "I74",
        "april_fools":      None,
        "games_won":        "L69",
        "games_lost":       "M69",
        "gawain_loss":      "N69",
        "nimue_tie_loss":   "O69",
        "killed_how_many":  "I78",
        "oops_all_pen":     None,
        "player_most_col":  ("J", 69, 72),
        "player_least_col": ("K", 69, 72),
    },

    "Galahad": {
        # bloco linha 89–110 | col I-O
        "how_many_played":  "I91",
        "duo_games":        "I96",
        "april_fools":      None,
        "games_won":        "L91",
        "games_lost":       "M91",
        "gawain_loss":      "N91",
        "nimue_tie_loss":   "O91",
        "killed_how_many":  "I100",
        "oops_all_pen":     None,
        "player_most_col":  ("J", 91, 94),
        "player_least_col": ("K", 91, 94),
    },

    "Gawain": {
        # bloco linha 111–132 | col I-O
        "how_many_played":  "I113",
        "duo_games":        "I118",
        "april_fools":      None,
        "games_won":        "L113",
        "games_lost":       "M113",
        "gawain_loss":      "N113",
        "nimue_tie_loss":   "O113",
        "killed_how_many":  "I122",
        "oops_all_pen":     None,
        "player_most_col":  ("J", 113, 116),
        "player_least_col": ("K", 113, 116),
    },

    "Guinevere": {
        # bloco linha 133–154 | col I-O
        "how_many_played":  "I135",
        "duo_games":        "I140",
        "april_fools":      None,
        "games_won":        "L135",
        "games_lost":       "M135",
        "gawain_loss":      "N135",
        "nimue_tie_loss":   "O135",
        "killed_how_many":  "I144",
        "oops_all_pen":     None,
        "player_most_col":  ("J", 135, 138),
        "player_least_col": ("K", 135, 138),
    },

    "King Arthur": {
        # bloco linha 155–176 | col I-O
        "how_many_played":  "I157",
        "duo_games":        "I162",
        "april_fools":      None,
        "games_won":        "L157",
        "games_lost":       "M157",
        "gawain_loss":      "N157",
        "nimue_tie_loss":   "O157",
        "killed_how_many":  "I166",
        "oops_all_pen":     None,
        "player_most_col":  ("J", 157, 160),
        "player_least_col": ("K", 157, 160),
    },

    "Palamedes": {
        # bloco linha 177–198 | col I-O
        "how_many_played":  "I179",
        "duo_games":        "I184",
        "april_fools":      None,
        "games_won":        "L179",
        "games_lost":       "M179",
        "gawain_loss":      "N179",
        "nimue_tie_loss":   "O179",
        "killed_how_many":  "I188",
        "oops_all_pen":     None,
        "player_most_col":  ("J", 179, 182),
        "player_least_col": ("K", 179, 182),
    },

    "Percival": {
        # bloco linha 199–220 | col I-O
        "how_many_played":  "I201",
        "duo_games":        "I206",
        "april_fools":      None,
        "games_won":        "L201",
        "games_lost":       "M201",
        "gawain_loss":      "N201",
        "nimue_tie_loss":   "O201",
        "killed_how_many":  "I210",
        "oops_all_pen":     None,
        "player_most_col":  ("J", 201, 204),
        "player_least_col": ("K", 201, 204),
    },

    "Sir Kay": {
        # bloco linha 221–242 | col I-O
        "how_many_played":  "I223",
        "duo_games":        "I228",
        "april_fools":      None,
        "games_won":        "L223",
        "games_lost":       "M223",
        "gawain_loss":      "N223",
        "nimue_tie_loss":   "O223",
        "killed_how_many":  "I232",
        "oops_all_pen":     None,
        "player_most_col":  ("J", 223, 226),
        "player_least_col": ("K", 223, 226),
    },

    "Loyal Servant": {
        # bloco linha 243–264 | col I-O
        "how_many_played":  "I245",
        "duo_games":        "I250",
        "april_fools":      None,
        "games_won":        "L245",
        "games_lost":       "M245",
        "gawain_loss":      "N245",
        "nimue_tie_loss":   "O245",
        "killed_how_many":  "I254",
        "oops_all_pen":     None,
        "player_most_col":  ("J", 245, 248),
        "player_least_col": ("K", 245, 248),
    },

    "Tristan": {
        # bloco linha 265–286 | col I-O
        "how_many_played":  "I267",
        "duo_games":        "I272",
        "april_fools":      None,
        "games_won":        "L267",
        "games_lost":       "M267",
        "gawain_loss":      "N267",
        "nimue_tie_loss":   "O267",
        "killed_how_many":  "I276",
        "oops_all_pen":     None,
        "player_most_col":  ("J", 267, 270),
        "player_least_col": ("K", 267, 270),
    },

    "Iseult": {
        # bloco linha 287–308 | col I-O
        "how_many_played":  "I289",
        "duo_games":        "I294",
        "april_fools":      None,
        "games_won":        "L289",
        "games_lost":       "M289",
        "gawain_loss":      "N289",
        "nimue_tie_loss":   "O289",
        "killed_how_many":  "I298",
        "oops_all_pen":     None,
        "player_most_col":  ("J", 289, 292),
        "player_least_col": ("K", 289, 292),
    },

    "Lancelot": {
        # bloco linha 309–330 | col I-O
        "how_many_played":  "I311",
        "duo_games":        "I316",
        "april_fools":      None,
        "games_won":        "L311",
        "games_lost":       "M311",
        "gawain_loss":      "N311",
        "nimue_tie_loss":   "O311",
        "killed_how_many":  "I320",
        "oops_all_pen":     None,
        "player_most_col":  ("J", 311, 314),
        "player_least_col": ("K", 311, 314),
    },

    "Nimue (G)": {
        # bloco linha 331–352 | col I-O
        "how_many_played":  "I333",
        "duo_games":        "I338",
        "april_fools":      None,
        "games_won":        "L333",
        "games_lost":       "M333",
        "gawain_loss":      "N333",
        "nimue_tie_loss":   "O333",
        "killed_how_many":  "I342",
        "oops_all_pen":     None,
        "player_most_col":  ("J", 333, 336),
        "player_least_col": ("K", 333, 336),
    },

    "Penpingion": {
        # bloco linha 353–374 | col I-O
        "how_many_played":  "I355",
        "duo_games":        "I360",
        "april_fools":      None,
        "games_won":        "L355",
        "games_lost":       "M355",
        "gawain_loss":      "N355",
        "nimue_tie_loss":   "O355",
        "killed_how_many":  "I364",
        "oops_all_pen":     None,
        "player_most_col":  ("J", 355, 358),
        "player_least_col": ("K", 355, 358),
    },
}


# ==============================================================================
# Leitura de um role — usa get_all_values() uma vez só
# ==============================================================================

def _fetch_role_stats(role_name: str, dados: list) -> dict:
    m = ROLE_MAP[role_name]

    player_most_col, pm_start, pm_end   = m["player_most_col"]
    player_least_col, pl_start, pl_end  = m["player_least_col"]

    stats = {
        "how_many_played":  _safe_int(_cell(dados, m["how_many_played"])),
        "duo_games":        _safe_int(_cell(dados, m["duo_games"])),
        "april_fools":      _safe_int(_cell(dados, m["april_fools"])) if m["april_fools"] else 0,
        "games_won":        _safe_int(_cell(dados, m["games_won"])),
        "games_lost":       _safe_int(_cell(dados, m["games_lost"])),
        "gawain_loss":      _safe_int(_cell(dados, m["gawain_loss"])),
        "nimue_tie_loss":   _safe_int(_cell(dados, m["nimue_tie_loss"])),
        "killed_how_many":  _safe_int(_cell(dados, m["killed_how_many"])),
        "oops_all_pen":     _safe_int(_cell(dados, m["oops_all_pen"])) if m["oops_all_pen"] else 0,
        "player_most":      _col_values_trimmed(dados, player_most_col, pm_start, pm_end),
        "player_least":     _col_values_trimmed(dados, player_least_col, pl_start, pl_end),
    }

    return stats


# ==============================================================================
# Cache
# ==============================================================================

def _save_roles_cache():
    with open(ROLES_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(roles_cache, f, indent=4, ensure_ascii=False)
    print("[roles] Cache salvo em cache_roles.json")


def _load_roles_cache_from_file() -> bool:
    if not os.path.exists(ROLES_CACHE_FILE):
        return False
    with open(ROLES_CACHE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    roles_cache.update(data)
    print(f"[roles] Cache carregado do arquivo ({len(data)} roles)")
    return True


def load_all_roles(force: bool = False):
    if not force and _load_roles_cache_from_file():
        return

    print("[roles] Buscando todos os roles no Sheets...")
    dados = pagina_roles.get_all_values()  # uma única requisição

    for role_name in ROLE_MAP:
        print(f"[roles] → {role_name}")
        roles_cache[role_name.lower()] = _fetch_role_stats(role_name, dados)

    _save_roles_cache()
    print("[roles] Cache completo!")


def get_role_stats(role_name: str) -> dict | None:
    return roles_cache.get(role_name.lower())


def refresh_role(role_name: str) -> dict:
    dados = pagina_roles.get_all_values()
    stats = _fetch_role_stats(role_name, dados)
    roles_cache[role_name.lower()] = stats
    _save_roles_cache()
    return stats