# utils_sheet_update.py
import re
from datetime import datetime, timedelta
from collections import Counter
from utils_sheets import planilha, nomes

# ==============================================================================
# Helpers
# ==============================================================================

def add_one_day(date_str: str, input_format="%m/%d/%Y", output_format="%m/%d/%Y") -> str:
    """Adiciona um dia à data (formato americano)."""
    dt = datetime.strptime(date_str, input_format)
    dt += timedelta(days=1)
    return dt.strftime(output_format)


def determine_gm_type(gm_name_list: list[str]) -> str:
    count = len(gm_name_list)
    if count == 1:   return "Single"
    elif count == 2: return "Duo"
    elif count == 3: return "Triple"
    return "Multi"


def determine_game_type(players: list[dict]) -> str:
    """
    Analisa os papéis de todos os jogadores:
    - Se todos aparecem exatamente 1 vez → Solo
    - Se todos aparecem exatamente 2 vezes → Pairs
    - Qualquer outra combinação → Mixed
    """
    role_counts = Counter(p["role"].strip().lower() for p in players)
    if all(v == 1 for v in role_counts.values()):
        return "Solo"
    if all(v == 2 for v in role_counts.values()):
        return "Pairs"
    return "Mixed"


def parse_death_info(embed) -> dict | None:
    """
    Extrai do embed informações de morte.
    Exemplos suportados:
        ☠️ Nix (The Witch of Caerlloyw) was killed
        💀 Deaths
        ☠️ Nome (Papel) was killed
        Death: nome1, nome2 as papel1, papel2
        Nome (Papel) was killed   ← no footer, sem emoji
    """
    text = embed.description or ""
    for field in embed.fields:
        text += "\n" + (field.value or "")
    # Inclui o footer também
    if embed.footer and embed.footer.text:
        text += "\n" + embed.footer.text

    # Padrão 1: ☠️ Nome (Papel) was killed / died
    kills = re.findall(r"☠️\s*(.+?)\s*\(([^)]+)\)\s*(?:was\s*killed|died)", text, re.IGNORECASE)
    if kills:
        who_died = [n.strip() for n, _ in kills]
        role_died = [r.strip() for _, r in kills]
        return {"who_died": who_died, "role_died": role_died}

    # Padrão 2: "Death: nome1, nome2 as papel1, papel2"
    match = re.search(r"Death\s*:\s*(.+?)\s+as\s+(.+)", text, re.IGNORECASE)
    if match:
        names = [n.strip() for n in match.group(1).split(",")]
        roles = [r.strip() for r in match.group(2).split(",")]
        return {"who_died": names, "role_died": roles}

    # Padrão 3: "Death: nome (papel)"
    match = re.search(r"Death\s*:\s*(.+?)\s*\(([^)]+)\)", text, re.IGNORECASE)
    if match:
        return {"who_died": [match.group(1).strip()], "role_died": [match.group(2).strip()]}

    # Padrão 4: "Nome (Papel) was killed" no footer — formato fixo do bot, sem emoji
    kills = re.findall(r"^([^\n(]+?)\s*\(([^)]+)\)\s*was\s+killed$", text, re.IGNORECASE | re.MULTILINE)
    if kills:
        return {
            "who_died": [n.strip() for n, _ in kills],
            "role_died": [r.strip() for _, r in kills]
        }

    return None


# ==============================================================================
# Construção das linhas para Game Log
# ==============================================================================
def _outcome_code(role: str, outcome: str) -> str:
    r = role.strip().lower()
    good = ['merlin', 'apprentice', 'caelia', 'elaine', 'galahad', 'gawain',
            'guinevere', 'king arthur', 'palamedes', 'percival', 'sir kay',
            'tristan', 'iseult', 'loyal servant of arthur', 'penpingion',
            'good lancelot', 'nimue (g)']
    evil = ['assassin', 'bertilak', 'dagonet', 'lucius', 'maduc', 'mark',
            'meleagant', 'mordred', 'morgana', 'oberon', 'puck', 'queen mab',
            'vortigern', 'the witch of caerlloyw', 'minion of morgana',
            'bad lancelot', 'nimue (e)']
    is_gawain = (r == 'gawain')
    is_nimue = r in ['nimue (g)', 'nimue (e)']
    is_good = r in good or is_gawain
    is_evil = r in evil

    if outcome == "gawain_wins":
        return "gaw" if is_gawain else ("gal-e" if is_evil else "gal-g")
    if outcome == "evil_wins":
        return "ew" if is_evil else "gl"
    if outcome == "good_wins":
        return "gw" if is_good else "el"
    if outcome in ("nimue_killed", "draw"):
        return "tnl-g" if (is_good or is_gawain or is_nimue) else "tnl-e"
    return ""


def _vote_code(role: str, vote: str) -> str:
    if vote == "nc":
        return ""
    r = role.strip().lower()
    good = ['merlin', 'apprentice', 'caelia', 'elaine', 'galahad', 'gawain',
            'guinevere', 'king arthur', 'palamedes', 'percival', 'sir kay',
            'tristan', 'iseult', 'loyal servant of arthur', 'penpingion',
            'good lancelot', 'nimue (g)']
    evil = ['assassin', 'bertilak', 'dagonet', 'lucius', 'maduc', 'mark',
            'meleagant', 'mordred', 'morgana', 'oberon', 'puck', 'queen mab',
            'vortigern', 'the witch of caerlloyw', 'minion of morgana',
            'bad lancelot', 'nimue (e)']
    is_good = r in good or r == 'gawain'
    is_evil = r in evil

    if vote == "vc_good":  return "vc" if is_good else ""
    if vote == "vi_good":  return "vi" if is_good else ""
    if vote == "vc_evil":  return "vc" if is_evil else ""
    if vote == "vi_evil":  return "vi" if is_evil else ""
    if vote == "vc":       return "vc"
    if vote == "vi":       return "vi"
    return ""


def build_game_log_rows(data: dict) -> list[list]:
    """Constrói as linhas para a aba 'Game Log'. Aplica +1 dia na data."""
    players = data["players"]
    outcome = data["outcome"]
    vote = data["vote"]
    start_date = data["date"]                   # já está em MM/DD/YYYY
    start_date_plus1 = add_one_day(start_date)  # <<< +1 dia corrigido aqui

    def sort_key(p):
        r = p["role"].strip().lower()
        good = ['merlin', 'apprentice', 'caelia', 'elaine', 'galahad', 'gawain',
                'guinevere', 'king arthur', 'palamedes', 'percival', 'sir kay',
                'tristan', 'iseult', 'loyal servant of arthur', 'penpingion',
                'good lancelot', 'nimue (g)']
        return 0 if r in good else 1

    players_sorted = sorted(players, key=sort_key)
    role_counts = Counter(p["role"].strip().lower() for p in players_sorted)
    role_index = {}

    rows = []
    for p in players_sorted:
        name = p["name"]
        role = p["role"]
        role_key = role.strip().lower()
        count = role_counts[role_key]
        idx = role_index.get(role_key, 0)
        role_index[role_key] = idx + 1

        outcome_col = _outcome_code(role, outcome)
        vote_col = _vote_code(role, vote)

        col_f = ""
        col_g = ""
        col_i = ""
        if count == 2:
            col_i = "duo"
            if idx == 0:
                col_f = "1"
                col_g = "Duo"
        elif count == 3:
            col_i = "triple"
            if idx == 0:
                col_f = "2"
                col_g = "Triple"

        rows.append([start_date_plus1, name, role, "", outcome_col, col_f, col_g, vote_col, col_i])
    return rows


def _get_last_content_row(sheet) -> int:
    """Retorna o número da última linha que contém qualquer valor (1-indexed)."""
    all_values = sheet.get_all_values()
    last = 0
    for i, row in enumerate(all_values):
        if any(cell.strip() for cell in row):
            last = i + 1
    return last


def write_game_log_rows(rows: list[list]):
    """Escreve na aba 'Game Log', após uma linha em branco do último conteúdo."""
    if not rows:
        return
    sheet = planilha.worksheet('Game Log')
    last_row = _get_last_content_row(sheet)
    start_row = last_row + 2
    end_row = start_row + len(rows) - 1

    sub_AB  = [[r[0], r[1]] for r in rows]
    sub_C   = [[r[2]] for r in rows]
    sub_E_I = [[r[4], r[5], r[6], r[7], r[8]] for r in rows]

    sheet.update(f"A{start_row}:B{end_row}", sub_AB, value_input_option="USER_ENTERED")
    sheet.update(f"C{start_row}:C{end_row}", sub_C, value_input_option="USER_ENTERED")
    sheet.update(f"E{start_row}:I{end_row}", sub_E_I, value_input_option="USER_ENTERED")


# ==============================================================================
# Construção das linhas para Death Log
# ==============================================================================
def build_death_log_rows(date: str, end_date: str, gm: str, gm_type: str,
                         game_type: str, who_wins: str,
                         deaths: dict | None) -> list[list]:
    """
    Constrói as linhas para a aba 'Death Log'.
    deaths: {'who_died': [nomes], 'role_died': [papéis]}
    """
    if not deaths or not deaths.get("who_died"):
        return []

    start_date_plus1 = add_one_day(date)
    rows = []
    who_died_list = deaths["who_died"]
    role_died_list = deaths["role_died"]

    for i in range(max(len(who_died_list), len(role_died_list))):
        name = who_died_list[i] if i < len(who_died_list) else ""
        role = role_died_list[i] if i < len(role_died_list) else ""
        rows.append([
            start_date_plus1, gm, gm_type, game_type,
            who_wins, name, end_date, role
        ])
    return rows


def write_death_log_rows(rows: list[list]):
    """Escreve na aba 'Death Log', diretamente após a última linha preenchida."""
    if not rows:
        return
    sheet = planilha.worksheet('Death Log')
    last_row = _get_last_content_row(sheet)
    start_row = last_row + 1
    end_row = start_row + len(rows) - 1
    sheet.update(f"A{start_row}:H{end_row}", rows, value_input_option="USER_ENTERED")