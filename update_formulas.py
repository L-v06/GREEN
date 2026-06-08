#!/usr/bin/env python3
"""
Script para atualizar as fórmulas das estatísticas (games_won, games_lost,
gawain_loss, nimue_tie_loss) na planilha "TESTE", aba "Role Stats".
Baseado no mapeamento do código original do bot.

CORREÇÃO: Para roles do mal, os sufixos no Game Log são diferentes:
    ew (evil win)   ao invés de gw
    el (evil lose)  ao invés de gl
    gal-e           ao invés de gal-g
    tnl-e           ao invés de tnl-g
"""

import gspread
import time
from google.oauth2.service_account import Credentials

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================
SHEET_NAME = "TESTE"           # Nome da planilha (igual ao do bot)
WORKSHEET_NAME = "Role Stats"  # Aba onde estão os dados dos roles
CREDENTIALS_FILE = "green_credentials.json"
SLEEP_BETWEEN_UPDATES = 0.8    # segundos entre cada célula atualizada

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# =============================================================================
# LISTA DE ROLES DO MAL (usada para decidir os sufixos das fórmulas)
# =============================================================================
EVIL_ROLES = {
    "assassin", "bertilak", "dagonet", "lucius", "maduc", "mark",
    "meleagant", "mordred", "morgana", "oberon", "puck", "queen mab",
    "vortigern", "minion", "bad lancelot", "nimue (e)", "the witch of caerlloyw"
}

# =============================================================================
# MAPEAMENTO DAS CÉLULAS PARA CADA ROLE
# (extraído diretamente do código de mapeamento do bot)
# =============================================================================
CELLS_MAP = {
    # -------------------- EVIL ROLES --------------------
    "assassin": {
        "games_won": "D4",
        "games_lost": "E4",
        "gawain_loss": "F4",
        "nimue_tie_loss": "G4"
    },
    "bertilak": {
        "games_won": "D25",
        "games_lost": "E25",
        "gawain_loss": "F25",
        "nimue_tie_loss": "G25"
    },
    "dagonet": {
        "games_won": "D47",
        "games_lost": "E47",
        "gawain_loss": "F47",
        "nimue_tie_loss": "G47"
    },
    "lucius": {
        "games_won": "D69",
        "games_lost": "E69",
        "gawain_loss": "F69",
        "nimue_tie_loss": "G69"
    },
    "maduc": {
        "games_won": "D91",
        "games_lost": "E91",
        "gawain_loss": "F91",
        "nimue_tie_loss": "G91"
    },
    "mark": {
        "games_won": "D113",
        "games_lost": "E113",
        "gawain_loss": "F113",
        "nimue_tie_loss": "G113"
    },
    "meleagant": {
        "games_won": "D135",
        "games_lost": "E135",
        "gawain_loss": "F135",
        "nimue_tie_loss": "G135"
    },
    "mordred": {
        "games_won": "D157",
        "games_lost": "E157",
        "gawain_loss": "F157",
        "nimue_tie_loss": "G157"
    },
    "morgana": {
        "games_won": "D179",
        "games_lost": "E179",
        "gawain_loss": "F179",
        "nimue_tie_loss": "G179"
    },
    "oberon": {
        "games_won": "D201",
        "games_lost": "E201",
        "gawain_loss": "F201",
        "nimue_tie_loss": "G201"
    },
    "puck": {
        "games_won": "D223",
        "games_lost": "E223",
        "gawain_loss": "F223",
        "nimue_tie_loss": "G223"
    },
    "queen mab": {
        "games_won": "D245",
        "games_lost": "E245",
        "gawain_loss": "F245",
        "nimue_tie_loss": "G245"
    },
    "vortigern": {
        "games_won": "D267",
        "games_lost": "E267",
        "gawain_loss": "F267",
        "nimue_tie_loss": "G267"
    },
    "minion": {
        "games_won": "D289",
        "games_lost": "E289",
        "gawain_loss": "F289",
        "nimue_tie_loss": "G289"
    },
    "bad lancelot": {
        "games_won": "D311",
        "games_lost": "E311",
        "gawain_loss": "F311",
        "nimue_tie_loss": "G311"
    },
    "nimue (e)": {
        "games_won": "D333",
        "games_lost": "E333",
        "gawain_loss": "F333",
        "nimue_tie_loss": "G333"
    },
    "the witch of caerlloyw": {
        "games_won": "D355",
        "games_lost": "E355",
        "gawain_loss": "F355",
        "nimue_tie_loss": "G355"
    },

    # -------------------- GOOD ROLES --------------------
    "merlin": {
        "games_won": "L4",
        "games_lost": "M4",
        "gawain_loss": "N4",
        "nimue_tie_loss": "O4"
    },
    "apprentice": {
        "games_won": "L25",
        "games_lost": "M25",
        "gawain_loss": "N25",
        "nimue_tie_loss": "O25"
    },
    "caelia": {
        "games_won": "L47",
        "games_lost": "M47",
        "gawain_loss": "N47",
        "nimue_tie_loss": "O47"
    },
    "elaine": {
        "games_won": "L69",
        "games_lost": "M69",
        "gawain_loss": "N69",
        "nimue_tie_loss": "O69"
    },
    "galahad": {
        "games_won": "L91",
        "games_lost": "M91",
        "gawain_loss": "N91",
        "nimue_tie_loss": "O91"
    },
    "gawain": {
        "games_won": "L113",
        "games_lost": "M113",
        "gawain_loss": "N113",
        "nimue_tie_loss": "O113"
    },
    "guinevere": {
        "games_won": "L135",
        "games_lost": "M135",
        "gawain_loss": "N135",
        "nimue_tie_loss": "O135"
    },
    "king arthur": {
        "games_won": "L157",
        "games_lost": "M157",
        "gawain_loss": "N157",
        "nimue_tie_loss": "O157"
    },
    "palamedes": {
        "games_won": "L179",
        "games_lost": "M179",
        "gawain_loss": "N179",
        "nimue_tie_loss": "O179"
    },
    "percival": {
        "games_won": "L201",
        "games_lost": "M201",
        "gawain_loss": "N201",
        "nimue_tie_loss": "O201"
    },
    "sir kay": {
        "games_won": "L223",
        "games_lost": "M223",
        "gawain_loss": "N223",
        "nimue_tie_loss": "O223"
    },
    "loyal servant": {
        "games_won": "L245",
        "games_lost": "M245",
        "gawain_loss": "N245",
        "nimue_tie_loss": "O245"
    },
    "tristan": {
        "games_won": "L267",
        "games_lost": "M267",
        "gawain_loss": "N267",
        "nimue_tie_loss": "O267"
    },
    "iseult": {
        "games_won": "L289",
        "games_lost": "M289",
        "gawain_loss": "N289",
        "nimue_tie_loss": "O289"
    },
    "lancelot": {
        "games_won": "L311",
        "games_lost": "M311",
        "gawain_loss": "N311",
        "nimue_tie_loss": "O311"
    },
    "nimue (g)": {
        "games_won": "L333",
        "games_lost": "M333",
        "gawain_loss": "N333",
        "nimue_tie_loss": "O333"
    },
    "penpingion": {
        "games_won": "L355",
        "games_lost": "M355",
        "gawain_loss": "N355",
        "nimue_tie_loss": "O355"
    },
}

# =============================================================================
# CONSTRUÇÃO DAS FÓRMULAS (COM SUPORTE A ROLES DO MAL)
# =============================================================================
def formula_games_won(role_name: str, is_evil: bool) -> str:
    """Fórmula para games_won. Se evil, usa 'ew' em vez de 'gw'."""
    outcome = "ew" if is_evil else "gw"
    return f'=COUNTIFS(\'Game Log\'!$C$2:$C,"{role_name}",\'Game Log\'!$E$2:$E,"{outcome}") - SUMIFS(\'Game Log\'!$F$2:$F,\'Game Log\'!$C$2:$C,"{role_name}",\'Game Log\'!$E$2:$E,"{outcome}")'

def formula_games_lost(role_name: str, is_evil: bool) -> str:
    """Fórmula para games_lost. Se evil, usa 'el' em vez de 'gl'."""
    outcome = "el" if is_evil else "gl"
    return f'=COUNTIFS(\'Game Log\'!$C$2:$C,"{role_name}",\'Game Log\'!$E$2:$E,"{outcome}") - SUMIFS(\'Game Log\'!$F$2:$F,\'Game Log\'!$C$2:$C,"{role_name}",\'Game Log\'!$E$2:$E,"{outcome}")'

def formula_gawain_loss(role_name: str, is_evil: bool) -> str:
    """Fórmula para gawain_loss. Se evil, usa 'gal-e' em vez de 'gal-g'."""
    outcome = "gal-e" if is_evil else "gal-g"
    return f'=COUNTIFS(\'Game Log\'!$C$2:$C,"{role_name}",\'Game Log\'!$E$2:$E,"{outcome}") - SUMIFS(\'Game Log\'!$F$2:$F,\'Game Log\'!$C$2:$C,"{role_name}",\'Game Log\'!$E$2:$E,"{outcome}")'

def formula_nimue_tie_loss(role_name: str, is_evil: bool) -> str:
    """Fórmula para nimue_tie_loss. Se evil, usa 'tnl-e' em vez de 'tnl-g'."""
    outcome = "tnl-e" if is_evil else "tnl-g"
    return f'=COUNTIFS(\'Game Log\'!$C$2:$C,"{role_name}",\'Game Log\'!$E$2:$E,"{outcome}") - SUMIFS(\'Game Log\'!$F$2:$F,\'Game Log\'!$C$2:$C,"{role_name}",\'Game Log\'!$E$2:$E,"{outcome}")'

# =============================================================================
# FUNÇÃO PRINCIPAL
# =============================================================================
def main():
    print("📊 Conectando ao Google Sheets...")
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)

    try:
        planilha = client.open(SHEET_NAME)
        pagina = planilha.worksheet(WORKSHEET_NAME)
    except Exception as e:
        print(f"❌ Erro ao acessar planilha/aba: {e}")
        return

    total_roles = len(CELLS_MAP)
    print(f"🔄 Atualizando fórmulas para {total_roles} roles...\n")

    for role_name, cells in CELLS_MAP.items():
        role_lower = role_name.lower()
        is_evil = role_lower in EVIL_ROLES

        print(f"📌 Processando: {role_name.title()} ({'Evil' if is_evil else 'Good'})")

        f_won = formula_games_won(role_lower, is_evil)
        f_lost = formula_games_lost(role_lower, is_evil)
        f_gawain = formula_gawain_loss(role_lower, is_evil)
        f_nimue = formula_nimue_tie_loss(role_lower, is_evil)

        try:
            pagina.update_acell(cells["games_won"], f_won)
            time.sleep(SLEEP_BETWEEN_UPDATES)
            pagina.update_acell(cells["games_lost"], f_lost)
            time.sleep(SLEEP_BETWEEN_UPDATES)
            pagina.update_acell(cells["gawain_loss"], f_gawain)
            time.sleep(SLEEP_BETWEEN_UPDATES)
            pagina.update_acell(cells["nimue_tie_loss"], f_nimue)
            time.sleep(SLEEP_BETWEEN_UPDATES)

            print(f"   ✅ Fórmulas inseridas em: {cells['games_won']}, {cells['games_lost']}, {cells['gawain_loss']}, {cells['nimue_tie_loss']}")
        except Exception as e:
            print(f"   ❌ Erro ao escrever fórmulas para {role_name}: {e}")

    print("\n✨ Atualização concluída!")

if __name__ == "__main__":
    main()