# utils_sheets.py

import os
import json
import time
import gspread
from google.oauth2.service_account import Credentials

from utils_config import _fuzzy_match_name_local, _PFX, CACHE_FILE, CACHE_GAMES_FILE, SHEET_NAME
from utils_graphs import GOOD_ROLES, EVIL_ROLES


scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file("green_credentials.json", scopes=scopes)
client = gspread.authorize(creds)




planilha = client.open(SHEET_NAME)
pagina = planilha.get_worksheet(0)
pagina_nomes = planilha.worksheet('Death Counter')


nomes = pagina_nomes.col_values(1)
nomes = [n for n in nomes if n not in ("Name", "Null", "Emma","")]

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

def extrair_pares(range_str, pagina_ref=None):
    ref = pagina_ref if pagina_ref else pagina
    dados = ref.get(range_str)
    resultado = {}
    if dados:
        for linha in dados:
            if len(linha) >= 2:
                chave = linha[0]
                valor_str = linha[1]
                if chave and chave.strip() and chave != "-":
                    resultado[chave] = _safe_int(valor_str)
    return resultado

def _fetch_player_stats(nome: str) -> dict:
    pagina.update_acell("A2", nome)
    time.sleep(2)

    dados        = pagina.get("A1:J55")
    dados_roles  = pagina.get("A24:AJ25")
    dados_extras = pagina.get("C58:H70")  # cobre todos os extrair_pares de uma vez
    time.sleep(1)

    # --- roles played ---
    roles_played = {}
    if len(dados_roles) >= 2:
        nomes_roles = dados_roles[0]
        qtds_roles  = dados_roles[1]
        roles_played = {
            nr: _safe_int(qtd)
            for nr, qtd in zip(nomes_roles, qtds_roles)
            if nr and nr.strip() and nr != "-"
        }


    def _pares_local(linhas, row_start, row_end, col_a, col_b):
        resultado = {}
        for i in range(row_start, min(row_end + 1, len(linhas))):
            linha = linhas[i]
            if len(linha) > col_b:
                chave = linha[col_a]
                valor = linha[col_b]
                if chave and chave.strip() and chave != "-":
                    resultado[chave] = _safe_int(valor)
        return resultado

    most_played_good_with     = _pares_local(dados_extras, 0,  2,  0, 1)
    most_played_evil_with     = _pares_local(dados_extras, 0,  2,  4, 5)
    most_played_with          = _pares_local(dados_extras, 5,  7,  0, 1)
    paired_with_the_most      = _pares_local(dados_extras, 5,  7,  4, 5)
    duo_most_played_good_with = _pares_local(dados_extras, 10, 12, 0, 1)
    duo_most_played_evil_with = _pares_local(dados_extras, 10, 12, 4, 5)


    stats = {
        # --- GENERAL STATS ---
        "good_games_won":           _cell(dados, "D2"),
        "evil_games_won":           _cell(dados, "D3"),
        "good_games_lost":          _cell(dados, "D4"),
        "evil_games_lost":          _cell(dados, "D5"),
        "gawain_good_lost":         _cell(dados, "D6"),
        "gawain_evil_lost":         _cell(dados, "D7"),



        "gawain_games_won":         _cell(dados, "F2"),
        "nimue_games_won":          _cell(dados, "F3"),
        "gawain_games_lost":        _cell(dados, "F4"),
        "nimue_games_lost":         _cell(dados, "F5"),
        "nimue_good_lost":          _cell(dados, "F6"),
        "nimue_evil_lost":          _cell(dados, "F7"),



        "total_games_played":       _cell(dados, "F8"),

        "good_role_won_most":       _cell(dados, "H2"),
        "evil_role_won_most":       _cell(dados, "H3"),
        "good_role_lost_most":      _cell(dados, "H4"),
        "evil_role_lost_most":      _cell(dados, "H5"),
        "nimue_win_good":           _cell(dados, "H6"),
        "nimue_win_evil":           _cell(dados, "H7"),

        # --- DUO STATS ---
        "duo_good_games_won":       _cell(dados, "D12"),
        "duo_evil_games_won":       _cell(dados, "D13"),
        "duo_good_games_lost":      _cell(dados, "D14"),
        "duo_evil_games_lost":      _cell(dados, "D15"),
        "duo_gawain_Good_lost":     _cell(dados, "D16"),
        "duo_gawain_Evil_lost":     _cell(dados, "D17"),

        "duo_gawain_games_won":     _cell(dados, "F12"),
        "duo_nimue_games_won":      _cell(dados, "F13"),
        "duo_gawain_games_lost":    _cell(dados, "F14"),
        "duo_nimue_games_lost":     _cell(dados, "F15"),
        "duo_nimue_Good_lost":      _cell(dados, "F16"),
        "duo_nimue_Evil_lost":      _cell(dados, "F17"),


        "duo_good_role_won_most":   _cell(dados, "H12"),
        "duo_evil_role_won_most":   _cell(dados, "H13"),
        "duo_good_role_lost_most":  _cell(dados, "H14"),
        "duo_evil_role_lost_most":  _cell(dados, "H15"),
        "duo_nimue Win_Good":       _cell(dados, "H16"),
        "duo_nimue Win_Evil":       _cell(dados, "H17"),

        "duo_good_win_ratio":       _cell(dados, "J12"),
        "duo_evil_win_ratio":       _cell(dados, "J13"),
        "duo_good_loss_ratio":      _cell(dados, "J14"),
        "duo_evil_loss_ratio":      _cell(dados, "J15"),

        "duo_most_played_good_with":  duo_most_played_good_with,
        "duo_most_played_evil_with":  duo_most_played_evil_with,


        # --- GM STATS ---
        "gm_single":                _cell(dados, "C21"),
        "gm_duo":                   _cell(dados, "D21"),
        "gm_triple":                _cell(dados, "E21"),
        "gm_solo":                  _cell(dados, "F21"),
        "gm_pairs":                 _cell(dados, "G21"),
        "gm_mixed":                 _cell(dados, "H21"),
        "total_games_gmed":         _cell(dados, "I21"),

        # --- VOTES ---
        "death_toll":               _cell(dados, "C28"),
        "correct_vote_ratio":       _cell(dados, "E28"),
        "incorrect_vote_ratio":     _cell(dados, "G28"),
        "how_many_times_voted":     _cell(dados, "I28"),
        "correct_votes":            _cell(dados, "E31"),
        "incorrect_votes":          _cell(dados, "G31"),

        # --- DATES ---
        "date_started_playing":     _cell(dados, "C31"),
        "date_last_played":         _cell(dados, "I31"),
        "everyone_wins_games":      _cell(dados, "E34"),

        # --- ROLES ---
        "role_played_most":         _cell(dados, "C34"),
        "role_played_least":        _cell(dados, "C37"),
        "role_last_played":         _cell(dados, "I34"),
        "good_role_played_most":    _cell(dados, "C40"),
        "evil_role_played_most":    _cell(dados, "C43"),

        # --- STREAKS ---
        "last_date_evil":           _cell(dados, "C46"),
        "last_date_good":           _cell(dados, "C49"),
        "evil_streak":              _cell(dados, "E46"),
        "good_streak":              _cell(dados, "E49"),
        "last_evil_role":           _cell(dados, "G46"),
        "last_good_role":           _cell(dados, "G49"),
        "longest_evil_streak":      _cell(dados, "I46"),
        "longest_good_streak":      _cell(dados, "I49"),
        "longest_game_streak":      _cell(dados, "C52"),
        "current_game_streak":      _cell(dados, "E52"),

         # --- GAMES_PLAYERS_RELATION ---

        "most_played_good_with":      most_played_good_with,
        "most_played_evil_with":      most_played_evil_with,
        "played_with_the_most":       most_played_with,
        "paired_with_the_most":       paired_with_the_most,

        

        

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
        if nome == "Null" or nome == 'Emma':
            continue
        else:
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
            continue

    # Duo → adiciona com prefixo duo_
    for player_name, duo_dict in duo_death.items():
        key = player_name.lower()
        if key in stats_cache:
            for k, v in duo_dict.items():
                stats_cache[key][f"duo_{k}"] = v
        else:
            continue

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

# ==============================================================================
# GM - Jogos por planilha
# trecho para substituir no utils_sheets.py
# ==============================================================================

games_cache: dict = {}

pagina_gm = planilha.worksheet('GM Game Finder')


def _fetch_gm_games(gm_name: str, total_games: int) -> list:
    jogos = []
    for i in range(1, total_games + 1):
        pagina_gm.update([[gm_name]], "A2")
        pagina_gm.update([[i]], "B2")
        time.sleep(2)

        # D2:J30 cobre: date(D), players(E), roles(F), [G ignorado], title(H), [I ignorado], notes(J)
        dados    = pagina_gm.get("D2:K30")
        co_dados = pagina_gm.get("A6:A13")

        if not dados:
            continue

        first_row = dados[0] if dados else []

        date  = first_row[0].strip() if len(first_row) > 0 and first_row[0].strip() else None
        title = first_row[5].strip() if len(first_row) > 5 and first_row[5].strip() else None
        notes = first_row[7].strip() if len(first_row) > 7 and first_row[7].strip() else None

        # co-GMs: A6:A8, ignora "No other GM" e vazios

        outcome_row = co_dados[-1] if co_dados else []
        outcome = outcome_row[0].strip() if outcome_row and outcome_row[0].strip() else None

        co_gms = []
        if co_dados:
            co_dados = co_dados[:3]
            for row in co_dados:
                val = row[0].strip() if row and row[0].strip() else ""
                if val and val.lower() != "no other gm":
                    co_gms.append(val)

        # players: coluna E=índice 1, F=índice 2 dentro do range D2:J30
        players = {}
        for linha in dados:
            if len(linha) >= 3 and linha[1].strip():
                players[linha[1].strip()] = linha[2].strip() if len(linha) > 2 else ""

        

        jogos.append({
            "game_number": i,
            "date": date,
            "title": title,
            "notes": notes,
            "co_gms": co_gms,
            "players": players,
            "outcome": outcome,
        })

    return jogos


def _save_games_cache():
    with open(CACHE_GAMES_FILE, "w", encoding="utf-8") as f:
        json.dump(games_cache, f, indent=4, ensure_ascii=False)
    print(f"[sheets] Games cache salvo em {CACHE_GAMES_FILE}")


def _load_games_cache_from_file() -> bool:
    if not os.path.exists(CACHE_GAMES_FILE):
        return False
    with open(CACHE_GAMES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    games_cache.update(data)
    print(f"[sheets] Games cache carregado ({len(data)} GMs)")
    return True


def load_all_gm_games(force: bool = False):
    if not force and _load_games_cache_from_file():
        return

    gms = [
        nome for nome in nomes
        if _safe_int(stats_cache.get(nome.lower(), {}).get("total_games_gmed")) > 0
    ]

    print(f"[sheets] Buscando jogos de {len(gms)} GMs...")
    for gm_name in gms:
        total = _safe_int(stats_cache[gm_name.lower()]["total_games_gmed"])
        print(f"[sheets] → {gm_name} ({total} jogos)")
        games_cache[gm_name.lower()] = _fetch_gm_games(gm_name, total)

    _save_games_cache()
    print("[sheets] Games cache completo!")


def get_gm_games(gm_name: str) -> list | None:
    return games_cache.get(gm_name.lower())


# ==============================================================================
# Helpers para update_game_info
# ==============================================================================

def _find_or_create_row(all_values: list, gm_name: str, game_number: int) -> int:
    gm_lower = gm_name.strip().lower()
    last_data_row = 1  # começa no cabeçalho

    for i, row in enumerate(all_values):
        if i == 0:
            continue  # pula cabeçalho
        col_m = row[12].strip().lower() if len(row) > 12 else ""
        col_n = row[13].strip()         if len(row) > 13 else ""

        # se tem dado na coluna M, atualiza o último row com dado
        if col_m:
            last_data_row = i + 1

        # se encontrou a linha exata, retorna ela
        if col_m == gm_lower and col_n == str(game_number):
            return i + 1

    # não encontrou — escreve logo após o último dado
    return last_data_row + 1


def _write_game_info_to_table(gm_name: str, game_number: int, title: str | None, notes: str | None):
    """Escreve/atualiza a linha em O:R da tabela GM Game Finder."""
    all_values = pagina_gm.get_all_values()
    row_idx    = _find_or_create_row(all_values, gm_name, game_number)
    row_data   = [gm_name, str(game_number), title or "", notes or ""]
    pagina_gm.update(f"M{row_idx}:P{row_idx}", [row_data], value_input_option="USER_ENTERED")
    print(f"[sheets] Table updated → row {row_idx} | {gm_name} #{game_number}")


def _update_cache_entry(key: str, num: int, title: str | None, notes: str | None):
    if key not in games_cache:
        return
    for jogo in games_cache[key]:
        if jogo["game_number"] == num:
            if title is not None:
                jogo["title"] = title or None
            if notes is not None:
                jogo["notes"] = notes or None
            break


def update_game_info(gm_name: str, game_number: int, title: str | None, notes: str | None):

    # salva no GM principal
    _write_game_info_to_table(gm_name, game_number, title, notes)
    _update_cache_entry(gm_name.lower(), game_number, title, notes)
    print(f"[sheets] Updated → {gm_name} #{game_number} | title={title} | notes={notes}")

    # propaga para co-GMs pela mesma data
    key_main    = gm_name.lower()
    source_jogo = next(
        (j for j in games_cache.get(key_main, []) if j["game_number"] == game_number),
        None,
    )

    if source_jogo and source_jogo.get("co_gms"):
        source_date = source_jogo.get("date")
        for co_gm in source_jogo["co_gms"]:
            co_key  = co_gm.lower()
            co_jogo = next(
                (j for j in games_cache.get(co_key, []) if j.get("date") == source_date),
                None,
            )
            if co_jogo is None:
                print(f"[sheets] Co-GM {co_gm}: jogo com date={source_date} não encontrado no cache")
                continue
            co_num = co_jogo["game_number"]
            _write_game_info_to_table(co_gm, co_num, title, notes)
            _update_cache_entry(co_key, co_num, title, notes)
            print(f"[sheets] Propagated → {co_gm} #{co_num}")

    _save_games_cache()