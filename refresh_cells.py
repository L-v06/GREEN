"""
refresh_cells.py
----------------
Atualiza células específicas do cache sem recarregar tudo.

MODOS DE USO:

1) Atualizar uma célula simples para todos os jogadores:
   python refresh_cells.py  → escolha modo 1

2) Atualizar uma role inteira para todos os jogadores (stats_cache):
   python refresh_cells.py  → escolha modo 2

3) Ver quais chaves uma célula mapeia:
   python refresh_cells.py  → escolha modo 3

4) Atualizar role_cache.json (parâmetros e/ou roles):
   python refresh_cells.py  → escolha modo 4

5) Atualizar death stats no stats_cache:
   python refresh_cells.py  → escolha modo 5

6) Atualizar GM games no games_cache:
   python refresh_cells.py  → escolha modo 6
"""

import json
import time
import os

import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

from utils_config import _fuzzy_match_name_local, CACHE_FILE, CACHE_ROLES_FILE, CACHE_GAMES_FILE, SHEET_NAME

# ==============================================================================
# Auth
# ==============================================================================

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds   = Credentials.from_service_account_file("green_credentials.json", scopes=scopes)
gclient = gspread.authorize(creds)

planilha = gclient.open(SHEET_NAME)

pagina_main  = planilha.get_worksheet(0)
pagina_roles = planilha.worksheet("Role Stats")
pagina_gm    = planilha.worksheet("GM Game Finder")

pagina_nomes = planilha.worksheet("Death Counter")
nomes = [n for n in pagina_nomes.col_values(1) if n not in ("Name", "Null", "Emma", "")]

ROLE_CACHE_FILE = CACHE_ROLES_FILE

# ==============================================================================
# Helpers
# ==============================================================================

def _safe_int(v):
    try:
        return int(v) if v else 0
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
        col = col * 26 + (ord(ch) - ord("A") + 1)
    col -= 1
    row = int(row_str) - 1
    try:
        value = dados[row][col]
        return value if value != "" else None
    except IndexError:
        return None


def _col_values_trimmed(dados: list, col_letter: str, row_start: int, row_end: int) -> list[str]:
    col = 0
    for ch in col_letter.upper():
        col = col * 26 + (ord(ch) - ord("A") + 1)
    col -= 1
    result = []
    for r in range(row_start - 1, row_end):
        try:
            val = dados[r][col]
            if val and val.strip() and val.strip() != "-":
                result.append(val.strip())
        except IndexError:
            pass
    return result


def _load_cache() -> dict:
    if not os.path.exists(CACHE_FILE):
        print(f"[refresh] Cache não encontrado: {CACHE_FILE}")
        return {}
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_cache(cache: dict):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=4, ensure_ascii=False)
    print(f"[refresh] Cache salvo em {CACHE_FILE}")


def _load_games_cache() -> dict:
    if not os.path.exists(CACHE_GAMES_FILE):
        print(f"[refresh] Games cache não encontrado: {CACHE_GAMES_FILE}")
        return {}
    with open(CACHE_GAMES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_games_cache(cache: dict):
    with open(CACHE_GAMES_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=4, ensure_ascii=False)
    print(f"[refresh] Games cache salvo em {CACHE_GAMES_FILE}")


# ==============================================================================
# Mapa célula → chave (worksheet 0, stats principais)
# ==============================================================================

CELL_MAP: dict[str, str] = {
    # GENERAL STATS
    "D2": "good_games_won",
    "D3": "evil_games_won",
    "D4": "good_games_lost",
    "D5": "evil_games_lost",
    "D6": "gawain_good_lost",
    "D7": "gawain_evil_lost",

    "F2": "gawain_games_won",
    "F3": "nimue_games_won",
    "F4": "gawain_games_lost",
    "F5": "nimue_games_lost",
    "F6": "nimue_good_lost",
    "F7": "nimue_evil_lost",
    "F8": "total_games_played",

    "H2": "good_role_won_most",
    "H3": "evil_role_won_most",
    "H4": "good_role_lost_most",
    "H5": "evil_role_lost_most",
    "H6": "nimue_win_good",
    "H7": "nimue_win_evil",

    # DUO STATS
    "D12": "duo_good_games_won",
    "D13": "duo_evil_games_won",
    "D14": "duo_good_games_lost",
    "D15": "duo_evil_games_lost",
    "D16": "duo_gawain_Good_lost",
    "D17": "duo_gawain_Evil_lost",

    "F12": "duo_gawain_games_won",
    "F13": "duo_nimue_games_won",
    "F14": "duo_gawain_games_lost",
    "F15": "duo_nimue_games_lost",
    "F16": "duo_nimue_Good_lost",
    "F17": "duo_nimue_Evil_lost",

    "H12": "duo_good_role_won_most",
    "H13": "duo_evil_role_won_most",
    "H14": "duo_good_role_lost_most",
    "H15": "duo_evil_role_lost_most",
    "H16": "duo_nimue Win_Good",
    "H17": "duo_nimue Win_Evil",

    "J12": "duo_good_win_ratio",
    "J13": "duo_evil_win_ratio",
    "J14": "duo_good_loss_ratio",
    "J15": "duo_evil_loss_ratio",

    # GM STATS
    "C21": "gm_single",
    "D21": "gm_duo",
    "E21": "gm_triple",
    "F21": "gm_solo",
    "G21": "gm_pairs",
    "H21": "gm_mixed",
    "I21": "total_games_gmed",

    # VOTES
    "C28": "death_toll",
    "E28": "correct_vote_ratio",
    "G28": "incorrect_vote_ratio",
    "I28": "how_many_times_voted",
    "E31": "correct_votes",
    "G31": "incorrect_votes",

    # DATES / EXTRA
    "C31": "date_started_playing",
    "I31": "date_last_played",
    "E34": "everyone_wins_games",
    "C34": "role_played_most",
    "C37": "role_played_least",
    "I34": "role_last_played",
    "C40": "good_role_played_most",
    "C43": "evil_role_played_most",

    # STREAKS
    "C46": "last_date_evil",
    "C49": "last_date_good",
    "E46": "evil_streak",
    "E49": "good_streak",
    "G46": "last_evil_role",
    "G49": "last_good_role",
    "I46": "longest_evil_streak",
    "I49": "longest_good_streak",
    "C52": "longest_game_streak",
    "E52": "current_game_streak",
}


# ==============================================================================
# Mapa de roles (worksheet "Role Stats")
# ==============================================================================

def _role_block(dados, col_played, col_duo, col_won, col_lost, col_gaw, col_nim,
                col_killed, row_base, col_most, col_least, row_most_start, row_most_end,
                col_april=None, row_april=None, col_oops=None, row_oops=None):
    return {
        "how_many_played": _safe_int(_cell(dados, f"{col_played}{row_base}")),
        "duo_games":       _safe_int(_cell(dados, f"{col_duo}{row_base + (3 if col_duo == col_played else 0)}")),
        "april_fools":     _safe_int(_cell(dados, f"{col_april}{row_april}")) if col_april and row_april else 0,
        "games_won":       _safe_int(_cell(dados, f"{col_won}{row_base}")),
        "games_lost":      _safe_int(_cell(dados, f"{col_lost}{row_base}")),
        "gawain_loss":     _safe_int(_cell(dados, f"{col_gaw}{row_base}")),
        "nimue_tie_loss":  _safe_int(_cell(dados, f"{col_nim}{row_base}")),
        "killed_how_many": _safe_int(_cell(dados, f"{col_killed}")),
        "oops_all_pen":    _safe_int(_cell(dados, f"{col_oops}{row_oops}")) if col_oops and row_oops else 0,
        "player_most":     _col_values_trimmed(dados, col_most, row_most_start, row_most_end),
        "player_least":    _col_values_trimmed(dados, col_least, row_most_start, row_most_end),
    }


def _fetch_roles_for_player(nome: str) -> dict:
    pagina_main.update_acell("A2", nome)
    time.sleep(2)
    dados = pagina_roles.get_all_values()
    time.sleep(1)

    roles_cache = {}

    # --- EVIL ROLES ---
    roles_cache["assassin"]               = _role_block(dados, "A","A", "D","E","F","G", "A16", 4,  "B","C", 3,6,  "A","11")
    roles_cache["bertilak"]               = _role_block(dados, "A","A", "D","E","F","G", "A37", 25, "B","C", 25,28)
    roles_cache["dagonet"]                = _role_block(dados, "A","A", "D","E","F","G", "A56", 47, "B","C", 47,50, "A","55")
    roles_cache["lucius"]                 = _role_block(dados, "A","A", "D","E","F","G", "A81", 69, "B","C", 69,72)
    roles_cache["maduc"]                  = _role_block(dados, "A","A", "D","E","F","G", "A103",91, "B","C", 91,94)
    roles_cache["mark"]                   = _role_block(dados, "A","A", "D","E","F","G", "A125",113,"B","C", 113,116)
    roles_cache["meleagant"]              = _role_block(dados, "A","A", "D","E","F","G", "A147",135,"B","C", 135,138)
    roles_cache["mordred"]                = _role_block(dados, "A","A", "D","E","F","G", "A169",157,"B","C", 157,160,"A","165")
    roles_cache["morgana"]                = _role_block(dados, "A","A", "D","E","F","G", "A191",179,"B","C", 179,182)
    roles_cache["oberon"]                 = _role_block(dados, "A","A", "D","E","F","G", "A213",201,"B","C", 201,204,"A","207")
    roles_cache["puck"]                   = _role_block(dados, "A","A", "D","E","F","G", "A235",223,"B","C", 223,226)
    roles_cache["queen mab"]              = _role_block(dados, "A","A", "D","E","F","G", "A257",245,"B","C", 245,248)
    roles_cache["vortigern"]              = _role_block(dados, "A","A", "D","E","F","G", "A281",267,"B","C", 267,270)
    roles_cache["minion"]                 = _role_block(dados, "A","A", "D","E","F","G", "A301",289,"B","C", 289,292)
    roles_cache["bad lancelot"]           = _role_block(dados, "A","A", "D","E","F","G", "A323",311,"B","C", 311,314)
    roles_cache["nimue (e)"]              = _role_block(dados, "A","A", "D","E","F","G", "A345",333,"B","C", 333,336)
    roles_cache["the witch of caerlloyw"] = _role_block(dados, "A","A", "D","E","F","G", "A364",355,"B","C", 355,358)

    # --- GOOD ROLES ---
    roles_cache["merlin"]          = _role_block(dados, "I","I", "L","M","N","O", "I16",  4,  "J","K", 3,6,   None,None, "I","21")
    roles_cache["apprentice"]      = _role_block(dados, "I","I", "L","M","N","O", "I37",  25, "J","K", 25,28)
    roles_cache["caelia"]          = _role_block(dados, "I","I", "L","M","N","O", "I58",  47, "J","K", 47,50)
    roles_cache["elaine"]          = _role_block(dados, "I","I", "L","M","N","O", "I81",  69, "J","K", 69,72)
    roles_cache["galahad"]         = _role_block(dados, "I","I", "L","M","N","O", "I103", 91, "J","K", 91,94)
    roles_cache["gawain"]          = _role_block(dados, "I","I", "L","M","N","O", "I126", 113,"J","K", 113,116)
    roles_cache["guinevere"]       = _role_block(dados, "I","I", "L","M","N","O", "I146", 135,"J","K", 135,138)
    roles_cache["king arthur"]     = _role_block(dados, "I","I", "L","M","N","O", "I169", 157,"J","K", 157,160)
    roles_cache["palamedes"]       = _role_block(dados, "I","I", "L","M","N","O", "I191", 179,"J","K", 179,182)
    roles_cache["percival"]        = _role_block(dados, "I","I", "L","M","N","O", "I213", 201,"J","K", 201,204)
    roles_cache["sir kay"]         = _role_block(dados, "I","I", "L","M","N","O", "I235", 223,"J","K", 223,226)
    roles_cache["loyal servant"]   = _role_block(dados, "I","I", "L","M","N","O", "I257", 245,"J","K", 245,248)
    roles_cache["tristan"]         = _role_block(dados, "I","I", "L","M","N","O", "I281", 267,"J","K", 267,270)
    roles_cache["iseult"]          = _role_block(dados, "I","I", "L","M","N","O", "I301", 289,"J","K", 289,292)
    roles_cache["lancelot"]        = _role_block(dados, "I","I", "L","M","N","O", "I323", 311,"J","K", 311,314)
    roles_cache["nimue (g)"]       = _role_block(dados, "I","I", "L","M","N","O", "I345", 333,"J","K", 333,336)
    roles_cache["penpingion"]      = _role_block(dados, "I","I", "L","M","N","O", "I364", 355,"J","K", 355,358)

    return roles_cache


# ==============================================================================
# Modo 1 — célula simples
# ==============================================================================

def refresh_cell(cell: str, player_filter: str | None = None):
    cell = cell.upper().strip()

    if cell not in CELL_MAP:
        print(f"[refresh] Célula '{cell}' não está no mapa. Use lookup para ver as disponíveis.")
        return

    chave = CELL_MAP[cell]
    cache = _load_cache()

    jogadores = nomes
    if player_filter:
        matched = _fuzzy_match_name_local(player_filter, nomes)
        if not matched:
            print(f"[refresh] Jogador '{player_filter}' não encontrado.")
            return
        jogadores = [matched]

    print(f"[refresh] Atualizando '{chave}' (célula {cell}) para {len(jogadores)} jogador(es)...")

    for nome in jogadores:
        key = nome.lower()
        if key not in cache:
            print(f"  → {nome}: não está no cache, pulando")
            continue

        print(f"  → {nome}...")
        pagina_main.update_acell("A2", nome)
        time.sleep(2)

        valor = pagina_main.acell(cell).value
        time.sleep(0.5)

        cache[key][chave] = valor if valor != "" else None
        print(f"     {chave} = {cache[key][chave]!r}")

    _save_cache(cache)
    print(f"[refresh] Pronto! '{chave}' atualizada para {len(jogadores)} jogador(es).")


# ==============================================================================
# Modo 2 — role no stats_cache por jogador
# ==============================================================================

def refresh_role(role_name: str, player_filter: str | None = None):
    role_key = role_name.strip().lower()
    cache    = _load_cache()

    jogadores = nomes
    if player_filter:
        matched = _fuzzy_match_name_local(player_filter, nomes)
        if not matched:
            print(f"[refresh] Jogador '{player_filter}' não encontrado.")
            return
        jogadores = [matched]

    print(f"[refresh] Atualizando role '{role_key}' no stats_cache para {len(jogadores)} jogador(es)...")

    for nome in jogadores:
        key = nome.lower()
        if key not in cache:
            print(f"  → {nome}: não está no cache, pulando")
            continue

        print(f"  → {nome}...")
        roles_data = _fetch_roles_for_player(nome)

        if role_key not in roles_data:
            print(f"     role '{role_key}' não encontrada")
            continue

        if "roles_cache" not in cache[key]:
            cache[key]["roles_cache"] = {}

        cache[key]["roles_cache"][role_key] = roles_data[role_key]
        print(f"     roles_cache['{role_key}'] atualizado")

    _save_cache(cache)
    print(f"[refresh] Pronto!")


# ==============================================================================
# Modo 4 — role_cache.json
# ==============================================================================

ROLE_CELLS_MAP = {
    # EVIL ROLES
    "assassin":               {"how_many_played": "A4",  "duo_games": "A7",  "april_fools": "A11", "games_won": "D4",  "games_lost": "E4",  "gawain_loss": "F4",  "nimue_tie_loss": "G4",  "killed_how_many": "A16"},
    "bertilak":               {"how_many_played": "A25", "duo_games": "A28", "april_fools": None,  "games_won": "D25", "games_lost": "E25", "gawain_loss": "F25", "nimue_tie_loss": "G25", "killed_how_many": "A37"},
    "dagonet":                {"how_many_played": "A47", "duo_games": "A50", "april_fools": "A55", "games_won": "D47", "games_lost": "E47", "gawain_loss": "F47", "nimue_tie_loss": "G47", "killed_how_many": "A56"},
    "lucius":                 {"how_many_played": "A69", "duo_games": "A72", "april_fools": None,  "games_won": "D69", "games_lost": "E69", "gawain_loss": "F69", "nimue_tie_loss": "G69", "killed_how_many": "A81"},
    "maduc":                  {"how_many_played": "A91", "duo_games": "A93", "april_fools": None,  "games_won": "D91", "games_lost": "E91", "gawain_loss": "F91", "nimue_tie_loss": "G91", "killed_how_many": "A103"},
    "mark":                   {"how_many_played": "A113","duo_games": "A116","april_fools": None,  "games_won": "D113","games_lost": "E113","gawain_loss": "F113","nimue_tie_loss": "G113","killed_how_many": "A125"},
    "meleagant":              {"how_many_played": "A135","duo_games": "A138","april_fools": None,  "games_won": "D135","games_lost": "E135","gawain_loss": "F135","nimue_tie_loss": "G135","killed_how_many": "A147"},
    "mordred":                {"how_many_played": "A157","duo_games": "A162","april_fools": "A165","games_won": "D157","games_lost": "E157","gawain_loss": "F157","nimue_tie_loss": "G157","killed_how_many": "A169"},
    "morgana":                {"how_many_played": "A179","duo_games": "A182","april_fools": None,  "games_won": "D179","games_lost": "E179","gawain_loss": "F179","nimue_tie_loss": "G179","killed_how_many": "A191"},
    "oberon":                 {"how_many_played": "A201","duo_games": "A204","april_fools": "A207","games_won": "D201","games_lost": "E201","gawain_loss": "F201","nimue_tie_loss": "G201","killed_how_many": "A213"},
    "puck":                   {"how_many_played": "A223","duo_games": "A226","april_fools": None,  "games_won": "D223","games_lost": "E223","gawain_loss": "F223","nimue_tie_loss": "G223","killed_how_many": "A235"},
    "queen mab":              {"how_many_played": "A245","duo_games": "A248","april_fools": None,  "games_won": "D245","games_lost": "E245","gawain_loss": "F245","nimue_tie_loss": "G245","killed_how_many": "A257"},
    "vortigern":              {"how_many_played": "A267","duo_games": "A273","april_fools": None,  "games_won": "D267","games_lost": "E267","gawain_loss": "F267","nimue_tie_loss": "G267","killed_how_many": "A281"},
    "minion":                 {"how_many_played": "A289","duo_games": "A292","april_fools": None,  "games_won": "D289","games_lost": "E289","gawain_loss": "F289","nimue_tie_loss": "G289","killed_how_many": "A301"},
    "bad lancelot":           {"how_many_played": "A311","duo_games": "A314","april_fools": None,  "games_won": "D311","games_lost": "E311","gawain_loss": "F311","nimue_tie_loss": "G311","killed_how_many": "A323"},
    "nimue (e)":              {"how_many_played": "A333","duo_games": "A336","april_fools": None,  "games_won": "D333","games_lost": "E333","gawain_loss": "F333","nimue_tie_loss": "G333","killed_how_many": "A345"},
    "the witch of caerlloyw": {"how_many_played": "A355","duo_games": "A358","april_fools": None,  "games_won": "D355","games_lost": "E355","gawain_loss": "F355","nimue_tie_loss": "G355","killed_how_many": "A364"},
    # GOOD ROLES
    "merlin":                 {"how_many_played": "I4",  "duo_games": "I7",  "april_fools": None,  "games_won": "L4",  "games_lost": "M4",  "gawain_loss": "N4",  "nimue_tie_loss": "O4",  "killed_how_many": "I16", "oops_all_pen": "I21"},
    "apprentice":             {"how_many_played": "I25", "duo_games": "I28", "april_fools": None,  "games_won": "L25", "games_lost": "M25", "gawain_loss": "N25", "nimue_tie_loss": "O25", "killed_how_many": "I37"},
    "caelia":                 {"how_many_played": "I47", "duo_games": "I50", "april_fools": None,  "games_won": "L47", "games_lost": "M47", "gawain_loss": "N47", "nimue_tie_loss": "O47", "killed_how_many": "I58"},
    "elaine":                 {"how_many_played": "I69", "duo_games": "I72", "april_fools": None,  "games_won": "L69", "games_lost": "M69", "gawain_loss": "N69", "nimue_tie_loss": "O69", "killed_how_many": "I81"},
    "galahad":                {"how_many_played": "I91", "duo_games": "I94", "april_fools": None,  "games_won": "L91", "games_lost": "M91", "gawain_loss": "N91", "nimue_tie_loss": "O91", "killed_how_many": "I103"},
    "gawain":                 {"how_many_played": "I113","duo_games": "I113","april_fools": None,  "games_won": "L113","games_lost": "M113","gawain_loss": "N113","nimue_tie_loss": "O113","killed_how_many": "I126"},
    "guinevere":              {"how_many_played": "I135","duo_games": "I138","april_fools": None,  "games_won": "L135","games_lost": "M135","gawain_loss": "N135","nimue_tie_loss": "O135","killed_how_many": "I146"},
    "king arthur":            {"how_many_played": "I157","duo_games": "I160","april_fools": None,  "games_won": "L157","games_lost": "M157","gawain_loss": "N157","nimue_tie_loss": "O157","killed_how_many": "I169"},
    "palamedes":              {"how_many_played": "I179","duo_games": "I182","april_fools": None,  "games_won": "L179","games_lost": "M179","gawain_loss": "N179","nimue_tie_loss": "O179","killed_how_many": "I191"},
    "percival":               {"how_many_played": "I201","duo_games": "I204","april_fools": None,  "games_won": "L201","games_lost": "M201","gawain_loss": "N201","nimue_tie_loss": "O201","killed_how_many": "I213"},
    "sir kay":                {"how_many_played": "I223","duo_games": "I226","april_fools": None,  "games_won": "L223","games_lost": "M223","gawain_loss": "N223","nimue_tie_loss": "O223","killed_how_many": "I235"},
    "loyal servant":          {"how_many_played": "I245","duo_games": "I248","april_fools": None,  "games_won": "L245","games_lost": "M245","gawain_loss": "N245","nimue_tie_loss": "O245","killed_how_many": "I257"},
    "tristan":                {"how_many_played": "I267","duo_games": "I270","april_fools": None,  "games_won": "L267","games_lost": "M267","gawain_loss": "N267","nimue_tie_loss": "O267","killed_how_many": "I281"},
    "iseult":                 {"how_many_played": "I289","duo_games": "I294","april_fools": None,  "games_won": "L289","games_lost": "M289","gawain_loss": "N289","nimue_tie_loss": "O289","killed_how_many": "I301"},
    "lancelot":               {"how_many_played": "I311","duo_games": "I314","april_fools": None,  "games_won": "L311","games_lost": "M311","gawain_loss": "N311","nimue_tie_loss": "O311","killed_how_many": "I323"},
    "nimue (g)":              {"how_many_played": "I333","duo_games": "I333","april_fools": None,  "games_won": "L333","games_lost": "M333","gawain_loss": "N333","nimue_tie_loss": "O333","killed_how_many": "I345"},
    "penpingion":             {"how_many_played": "I355","duo_games": "I358","april_fools": None,  "games_won": "L355","games_lost": "M355","gawain_loss": "N355","nimue_tie_loss": "O355","killed_how_many": "I364"},
}

ROLE_LIST_PARAMS = {
    # evil
    "assassin":               {"player_most": ("B", 4, 6),   "player_least": ("C", 4, 6)},
    "bertilak":               {"player_most": ("B", 25, 28), "player_least": ("C", 25, 28)},
    "dagonet":                {"player_most": ("B", 47, 50), "player_least": ("C", 47, 50)},
    "lucius":                 {"player_most": ("B", 69, 72), "player_least": ("C", 69, 72)},
    "maduc":                  {"player_most": ("B", 91, 94), "player_least": ("C", 91, 94)},
    "mark":                   {"player_most": ("B", 113,116),"player_least": ("C", 113,116)},
    "meleagant":              {"player_most": ("B", 135,138),"player_least": ("C", 135,138)},
    "mordred":                {"player_most": ("B", 157,160),"player_least": ("C", 157,160)},
    "morgana":                {"player_most": ("B", 179,182),"player_least": ("C", 179,182)},
    "oberon":                 {"player_most": ("B", 201,204),"player_least": ("C", 201,204)},
    "puck":                   {"player_most": ("B", 223,226),"player_least": ("C", 223,226)},
    "queen mab":              {"player_most": ("B", 245,248),"player_least": ("C", 245,248)},
    "vortigern":              {"player_most": ("B", 267,270),"player_least": ("C", 267,270)},
    "minion":                 {"player_most": ("B", 289,292),"player_least": ("C", 289,292)},
    "bad lancelot":           {"player_most": ("B", 311,314),"player_least": ("C", 311,314)},
    "nimue (e)":              {"player_most": ("B", 333,336),"player_least": ("C", 333,336)},
    "the witch of caerlloyw": {"player_most": ("B", 355,358),"player_least": ("C", 355,358)},
    # good
    "merlin":                 {"player_most": ("J", 4, 6),   "player_least": ("K", 4, 6)},
    "apprentice":             {"player_most": ("J", 25, 28), "player_least": ("K", 25, 28)},
    "caelia":                 {"player_most": ("J", 47, 50), "player_least": ("K", 47, 50)},
    "elaine":                 {"player_most": ("J", 69, 72), "player_least": ("K", 69, 72)},
    "galahad":                {"player_most": ("J", 91, 94), "player_least": ("K", 91, 94)},
    "gawain":                 {"player_most": ("J", 113,116),"player_least": ("K", 113,116)},
    "guinevere":              {"player_most": ("J", 135,138),"player_least": ("K", 135,138)},
    "king arthur":            {"player_most": ("J", 157,160),"player_least": ("K", 157,160)},
    "palamedes":              {"player_most": ("J", 179,182),"player_least": ("K", 179,182)},
    "percival":               {"player_most": ("J", 201,204),"player_least": ("K", 201,204)},
    "sir kay":                {"player_most": ("J", 223,226),"player_least": ("K", 223,226)},
    "loyal servant":          {"player_most": ("J", 245,248),"player_least": ("K", 245,248)},
    "tristan":                {"player_most": ("J", 267,270),"player_least": ("K", 267,270)},
    "iseult":                 {"player_most": ("J", 289,292),"player_least": ("K", 289,292)},
    "lancelot":               {"player_most": ("J", 311,314),"player_least": ("K", 311,314)},
    "nimue (g)":              {"player_most": ("J", 333,336),"player_least": ("K", 333,336)},
    "penpingion":             {"player_most": ("J", 355,358),"player_least": ("K", 355,358)},
}

ALL_ROLE_PARAMS = ["how_many_played", "duo_games", "april_fools", "games_won",
                   "games_lost", "gawain_loss", "nimue_tie_loss", "killed_how_many",
                   "oops_all_pen", "player_most", "player_least"]


def _load_role_cache() -> dict:
    if not os.path.exists(ROLE_CACHE_FILE):
        print(f"[refresh] Role cache não encontrado: {ROLE_CACHE_FILE}")
        return {}
    with open(ROLE_CACHE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_role_cache(cache: dict):
    with open(ROLE_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=4, ensure_ascii=False)
    print(f"[refresh] Role cache salvo em {ROLE_CACHE_FILE}")


def refresh_role_cache(role_filter: str | None = None, params: list | None = None):
    cache  = _load_role_cache()
    params = params or ALL_ROLE_PARAMS

    roles_to_update = list(ROLE_CELLS_MAP.keys())
    if role_filter:
        role_filter = role_filter.strip().lower()
        if role_filter not in ROLE_CELLS_MAP:
            print(f"[refresh] Role '{role_filter}' não encontrada.")
            print(f"Roles disponíveis: {', '.join(ROLE_CELLS_MAP.keys())}")
            return
        roles_to_update = [role_filter]

    print(f"\n[refresh] Atualizando {len(roles_to_update)} role(s), parâmetros: {params}\n")
    print("[refresh] Lendo aba Role Stats...")
    dados = pagina_roles.get_all_values()
    time.sleep(1)

    for role in roles_to_update:
        print(f"  → {role}")
        if role not in cache:
            cache[role] = {}

        cells       = ROLE_CELLS_MAP.get(role, {})
        list_params = ROLE_LIST_PARAMS.get(role, {})

        for param in params:
            if param in ("player_most", "player_least"):
                if param in list_params:
                    col, row_start, row_end = list_params[param]
                    valor = _col_values_trimmed(dados, col, row_start, row_end)
                    cache[role][param] = valor
                    print(f"     {param} = {valor}")
                continue

            celula = cells.get(param)
            if not celula:
                if param not in cache[role]:
                    cache[role][param] = 0
                continue

            valor = _safe_int(_cell(dados, celula))
            cache[role][param] = valor
            print(f"     {param} = {valor}")

    _save_role_cache(cache)
    print(f"\n[refresh] Pronto!")


# ==============================================================================
# Modo 3 — lookup
# ==============================================================================

def lookup_cell(cell: str):
    cell = cell.upper().strip()
    if cell in CELL_MAP:
        print(f"[lookup] {cell} → chave: '{CELL_MAP[cell]}'")
    else:
        print(f"[lookup] '{cell}' não está no mapa.")
        print("\nCélulas disponíveis:")
        for c, k in sorted(CELL_MAP.items()):
            print(f"  {c:6s} → {k}")


# ==============================================================================
# Modo 5 — Death Stats
# ==============================================================================

DEATH_KEYS = [
    "was_killed_correctly", "was_killed_incorrectly",
    "died_for_good", "died_for_evil",
    "died_as_nimue", "died_as_gawain",
    "tricker_good_role", "tricker_evil_role",
    "roles_that_died_with",
]


def refresh_death_stats(player_filter: str | None = None):
    from utils_sheets import compute_death_stats

    cache = _load_cache()

    jogadores_filter = None
    if player_filter:
        matched = _fuzzy_match_name_local(player_filter, nomes)
        if not matched:
            print(f"[refresh] Jogador '{player_filter}' não encontrado.")
            return
        jogadores_filter = matched.lower()
        print(f"[refresh] Filtrando para: {matched}")

    print("[refresh] Rodando compute_death_stats()...")
    all_death, duo_death = compute_death_stats()

    for player_name, death_dict in all_death.items():
        key = player_name.lower()
        if jogadores_filter and key != jogadores_filter:
            continue
        if key not in cache:
            print(f"  → {player_name}: não está no cache, pulando")
            continue
        for k in DEATH_KEYS:
            if k in death_dict:
                cache[key][k] = death_dict[k]
        print(f"  → {player_name}: death stats atualizadas")

    for player_name, duo_dict in duo_death.items():
        key = player_name.lower()
        if jogadores_filter and key != jogadores_filter:
            continue
        if key not in cache:
            continue
        for k, v in duo_dict.items():
            cache[key][f"duo_{k}"] = v
        print(f"  → {player_name}: duo death stats atualizadas")

    _save_cache(cache)
    print("[refresh] Death stats concluídas!")


# ==============================================================================
# Modo 6 — GM Games (usa pagina_gm local, não importa utils_sheets)
# ==============================================================================

def _fetch_gm_games_local(gm_name: str, total_games: int) -> list:
    jogos = []
    for i in range(1, total_games + 1):
        pagina_gm.update([[gm_name]], "A2")
        pagina_gm.update([[i]], "B2")
        time.sleep(2)

        dados    = pagina_gm.get("D2:K30")
        co_dados = pagina_gm.get("A6:A13")

        if not dados:
            continue

        first_row = dados[0] if dados else []

        date  = first_row[0].strip() if len(first_row) > 0 and first_row[0].strip() else None
        title = first_row[5].strip() if len(first_row) > 5 and first_row[5].strip() else None
        notes = first_row[7].strip() if len(first_row) > 7 and first_row[7].strip() else None

        outcome_row = co_dados[-1] if co_dados else []
        outcome = outcome_row[0].strip() if outcome_row and outcome_row[0].strip() else None

        co_gms = []
        if co_dados:
            for row in co_dados[:3]:
                val = row[0].strip() if row and row[0].strip() else ""
                if val and val.lower() != "no other gm":
                    co_gms.append(val)

        players = {}
        for linha in dados:
            if len(linha) >= 3 and linha[1].strip():
                players[linha[1].strip()] = linha[2].strip() if len(linha) > 2 else ""

        jogos.append({
            "game_number": i,
            "date":        date,
            "title":       title,
            "notes":       notes,
            "co_gms":      co_gms,
            "players":     players,
            "outcome":     outcome,
        })

        print(f"     jogo {i}/{total_games} lido")

    return jogos


def refresh_gm_games(player_filter: str | None = None):
    stats_cache = _load_cache()
    games_cache = _load_games_cache()

    jogadores = nomes
    if player_filter:
        matched = _fuzzy_match_name_local(player_filter, nomes)
        if not matched:
            print(f"[refresh] Jogador '{player_filter}' não encontrado.")
            return
        jogadores = [matched]

    print(f"[refresh] Atualizando GM games para {len(jogadores)} jogador(es)...")

    for nome in jogadores:
        key   = nome.lower()
        total = _safe_int(stats_cache.get(key, {}).get("total_games_gmed"))
        if not total:
            if player_filter:
                print(f"  → {nome}: total_games_gmed nulo ou zero, pulando")
            continue
        print(f"  → {nome} ({total} jogos)...")
        games_cache[key] = _fetch_gm_games_local(nome, total)
        print(f"     {nome} concluído")

    _save_games_cache(games_cache)
    print("[refresh] GM games cache atualizado!")


# ==============================================================================
# CLI interativo
# ==============================================================================

def _ask(prompt: str, optional: bool = False) -> str | None:
    val = input(prompt).strip()
    return val if val else (None if optional else "")


if __name__ == "__main__":
    print("=" * 55)
    print("  Green Bot — Refresh de Células")
    print("=" * 55)
    print("\nModos disponíveis:")
    print("  1) Atualizar uma célula do stats_cache (ex: I28)")
    print("  2) Atualizar role no stats_cache por jogador")
    print("  3) Lookup — ver qual chave uma célula mapeia")
    print("  4) Atualizar role_cache.json (parâmetros e/ou roles)")
    print("  5) Atualizar death stats no stats_cache")
    print("  6) Atualizar GM games no games_cache")
    print()

    modo = input("Escolha o modo (1 / 2 / 3 / 4 / 5 / 6): ").strip()

    if modo == "1":
        cell   = _ask("Célula (ex: I28): ")
        player = _ask("Jogador (deixe vazio para todos): ", optional=True)
        refresh_cell(cell, player)

    elif modo == "2":
        role   = _ask("Nome da role (ex: merlin): ")
        player = _ask("Jogador (deixe vazio para todos): ", optional=True)
        refresh_role(role, player)

    elif modo == "3":
        cell = _ask("Célula para lookup (ex: I28): ")
        lookup_cell(cell)

    elif modo == "4":
        print("\nParâmetros disponíveis:")
        for i, p in enumerate(ALL_ROLE_PARAMS, 1):
            print(f"  {i:2}) {p}")
        print(f"  {len(ALL_ROLE_PARAMS)+1:2}) todos")
        print()

        escolha = input("Quais parâmetros? (ex: 1 4 5  ou  todos): ").strip().lower()

        if escolha == "todos" or escolha == str(len(ALL_ROLE_PARAMS) + 1):
            params_sel = ALL_ROLE_PARAMS
        else:
            indices = escolha.split()
            params_sel = []
            for idx in indices:
                if idx.isdigit() and 1 <= int(idx) <= len(ALL_ROLE_PARAMS):
                    params_sel.append(ALL_ROLE_PARAMS[int(idx) - 1])
            if not params_sel:
                print("Nenhum parâmetro válido selecionado.")
                exit()

        role_input = _ask("\nRole específica (deixe vazio para todas): ", optional=True)
        refresh_role_cache(role_filter=role_input, params=params_sel)

    elif modo == "5":
        player = _ask("Jogador (deixe vazio para todos): ", optional=True)
        refresh_death_stats(player)

    elif modo == "6":
        player = _ask("GM (deixe vazio para todos): ", optional=True)
        refresh_gm_games(player)

    else:
        print("Modo inválido. Rode novamente e escolha 1, 2, 3, 4, 5 ou 6.")