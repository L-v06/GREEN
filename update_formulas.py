#!/usr/bin/env python3
"""
update_role_formulas.py
-----------------------
Atualiza fórmulas na aba "Role Stats" da planilha.
Roda interativamente — escolha quais parâmetros atualizar.
"""

import gspread
import time
from google.oauth2.service_account import Credentials

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================
SHEET_NAME       = "TESTE"
WORKSHEET_NAME   = "Role Stats"
CREDENTIALS_FILE = "green_credentials.json"
SLEEP            = 0.8

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# =============================================================================
# ROLES DO MAL
# =============================================================================
EVIL_ROLES = {
    "assassin", "bertilak", "dagonet", "lucius", "maduc", "mark",
    "meleagant", "mordred", "morgana", "oberon", "puck", "queen mab",
    "vortigern", "minion", "bad lancelot", "nimue (e)", "the witch of caerlloyw"
}

# =============================================================================
# COLUNA DA PIVOT POR ROLE (Role Breakdown)
# Ordem: Apprentice, Assassin, Bertilak, Caelia, Dagonet, Elaine, Galahad,
#        Gawain, Guinevere, Iseult, King Arthur, Lancelot, Bad Lance,
#        Loyal Servant, Lucius, Maduc, Mark, Meleagant, Merlin, Minion,
#        Mordred, Morgana, Nimue (E), Nimue (G), Oberon, Palamedes,
#        Penpingion, Percival, Puck, Queen Mab, Sir Kay,
#        The Witch of Caerlloyw, Tristan, Vortigern
# =============================================================================
PIVOT_COL = {
    "apprentice":             "B",
    "assassin":               "C",
    "bertilak":               "D",
    "caelia":                 "E",
    "dagonet":                "F",
    "elaine":                 "G",
    "galahad":                "H",
    "gawain":                 "I",
    "guinevere":              "J",
    "iseult":                 "K",
    "king arthur":            "L",
    "lancelot":               "M",
    "bad lancelot":           "N",
    "loyal servant":          "O",
    "lucius":                 "P",
    "maduc":                  "Q",
    "mark":                   "R",
    "meleagant":              "S",
    "merlin":                 "T",
    "minion":                 "U",
    "mordred":                "V",
    "morgana":                "W",
    "nimue (e)":              "X",
    "nimue (g)":              "Y",
    "oberon":                 "Z",
    "palamedes":              "AA",
    "penpingion":             "AB",
    "percival":               "AC",
    "puck":                   "AD",
    "queen mab":              "AE",
    "sir kay":                "AF",
    "the witch of caerlloyw": "AG",
    "tristan":                "AH",
    "vortigern":              "AI",
}

# =============================================================================
# MAPEAMENTO DE CÉLULAS POR ROLE
# player_most e player_least inferidos da linha base de cada role
# =============================================================================
CELLS_MAP = {
    # -------------------- EVIL ROLES --------------------
    "assassin":               {"row": 4,   "games_won": "D4",   "games_lost": "E4",   "gawain_loss": "F4",   "nimue_tie_loss": "G4"},
    "bertilak":               {"row": 25,  "games_won": "D25",  "games_lost": "E25",  "gawain_loss": "F25",  "nimue_tie_loss": "G25"},
    "dagonet":                {"row": 47,  "games_won": "D47",  "games_lost": "E47",  "gawain_loss": "F47",  "nimue_tie_loss": "G47"},
    "lucius":                 {"row": 69,  "games_won": "D69",  "games_lost": "E69",  "gawain_loss": "F69",  "nimue_tie_loss": "G69"},
    "maduc":                  {"row": 91,  "games_won": "D91",  "games_lost": "E91",  "gawain_loss": "F91",  "nimue_tie_loss": "G91"},
    "mark":                   {"row": 113, "games_won": "D113", "games_lost": "E113", "gawain_loss": "F113", "nimue_tie_loss": "G113"},
    "meleagant":              {"row": 135, "games_won": "D135", "games_lost": "E135", "gawain_loss": "F135", "nimue_tie_loss": "G135"},
    "mordred":                {"row": 157, "games_won": "D157", "games_lost": "E157", "gawain_loss": "F157", "nimue_tie_loss": "G157"},
    "morgana":                {"row": 179, "games_won": "D179", "games_lost": "E179", "gawain_loss": "F179", "nimue_tie_loss": "G179"},
    "oberon":                 {"row": 201, "games_won": "D201", "games_lost": "E201", "gawain_loss": "F201", "nimue_tie_loss": "G201"},
    "puck":                   {"row": 223, "games_won": "D223", "games_lost": "E223", "gawain_loss": "F223", "nimue_tie_loss": "G223"},
    "queen mab":              {"row": 245, "games_won": "D245", "games_lost": "E245", "gawain_loss": "F245", "nimue_tie_loss": "G245"},
    "vortigern":              {"row": 267, "games_won": "D267", "games_lost": "E267", "gawain_loss": "F267", "nimue_tie_loss": "G267"},
    "minion":                 {"row": 289, "games_won": "D289", "games_lost": "E289", "gawain_loss": "F289", "nimue_tie_loss": "G289"},
    "bad lancelot":           {"row": 311, "games_won": "D311", "games_lost": "E311", "gawain_loss": "F311", "nimue_tie_loss": "G311"},
    "nimue (e)":              {"row": 333, "games_won": "D333", "games_lost": "E333", "gawain_loss": "F333", "nimue_tie_loss": "G333"},
    "the witch of caerlloyw": {"row": 355, "games_won": "D355", "games_lost": "E355", "gawain_loss": "F355", "nimue_tie_loss": "G355"},

    # -------------------- GOOD ROLES --------------------
    "merlin":                 {"row": 4,   "games_won": "L4",   "games_lost": "M4",   "gawain_loss": "N4",   "nimue_tie_loss": "O4"},
    "apprentice":             {"row": 25,  "games_won": "L25",  "games_lost": "M25",  "gawain_loss": "N25",  "nimue_tie_loss": "O25"},
    "caelia":                 {"row": 47,  "games_won": "L47",  "games_lost": "M47",  "gawain_loss": "N47",  "nimue_tie_loss": "O47"},
    "elaine":                 {"row": 69,  "games_won": "L69",  "games_lost": "M69",  "gawain_loss": "N69",  "nimue_tie_loss": "O69"},
    "galahad":                {"row": 91,  "games_won": "L91",  "games_lost": "M91",  "gawain_loss": "N91",  "nimue_tie_loss": "O91"},
    "gawain":                 {"row": 113, "games_won": "L113", "games_lost": "M113", "gawain_loss": "N113", "nimue_tie_loss": "O113"},
    "guinevere":              {"row": 135, "games_won": "L135", "games_lost": "M135", "gawain_loss": "N135", "nimue_tie_loss": "O135"},
    "king arthur":            {"row": 157, "games_won": "L157", "games_lost": "M157", "gawain_loss": "N157", "nimue_tie_loss": "O157"},
    "palamedes":              {"row": 179, "games_won": "L179", "games_lost": "M179", "gawain_loss": "N179", "nimue_tie_loss": "O179"},
    "percival":               {"row": 201, "games_won": "L201", "games_lost": "M201", "gawain_loss": "N201", "nimue_tie_loss": "O201"},
    "sir kay":                {"row": 223, "games_won": "L223", "games_lost": "M223", "gawain_loss": "N223", "nimue_tie_loss": "O223"},
    "loyal servant":          {"row": 245, "games_won": "L245", "games_lost": "M245", "gawain_loss": "N245", "nimue_tie_loss": "O245"},
    "tristan":                {"row": 267, "games_won": "L267", "games_lost": "M267", "gawain_loss": "N267", "nimue_tie_loss": "O267"},
    "iseult":                 {"row": 289, "games_won": "L289", "games_lost": "M289", "gawain_loss": "N289", "nimue_tie_loss": "O289"},
    "lancelot":               {"row": 311, "games_won": "L311", "games_lost": "M311", "gawain_loss": "N311", "nimue_tie_loss": "O311"},
    "nimue (g)":              {"row": 333, "games_won": "L333", "games_lost": "M333", "gawain_loss": "N333", "nimue_tie_loss": "O333"},
    "penpingion":             {"row": 355, "games_won": "L355", "games_lost": "M355", "gawain_loss": "N355", "nimue_tie_loss": "O355"},
}

# =============================================================================
# FÓRMULAS
# Mude aqui se precisar ajustar a lógica das fórmulas no futuro
# =============================================================================

def formula_games_won(role: str, is_evil: bool) -> str:
    outcome = "ew" if is_evil else "gw"
    return (
        f'=COUNTIFS(\'Game Log\'!$C$2:$C,"{role}",\'Game Log\'!$E$2:$E,"{outcome}")'
        f' - SUMIFS(\'Game Log\'!$F$2:$F,\'Game Log\'!$C$2:$C,"{role}",\'Game Log\'!$E$2:$E,"{outcome}")'
    )

def formula_games_lost(role: str, is_evil: bool) -> str:
    outcome = "el" if is_evil else "gl"
    return (
        f'=COUNTIFS(\'Game Log\'!$C$2:$C,"{role}",\'Game Log\'!$E$2:$E,"{outcome}")'
        f' - SUMIFS(\'Game Log\'!$F$2:$F,\'Game Log\'!$C$2:$C,"{role}",\'Game Log\'!$E$2:$E,"{outcome}")'
    )

def formula_gawain_loss(role: str, is_evil: bool) -> str:
    outcome = "gal-e" if is_evil else "gal-g"
    return (
        f'=COUNTIFS(\'Game Log\'!$C$2:$C,"{role}",\'Game Log\'!$E$2:$E,"{outcome}")'
        f' - SUMIFS(\'Game Log\'!$F$2:$F,\'Game Log\'!$C$2:$C,"{role}",\'Game Log\'!$E$2:$E,"{outcome}")'
    )

def formula_nimue_tie_loss(role: str, is_evil: bool) -> str:
    outcome = "tnl-e" if is_evil else "tnl-g"
    return (
        f'=COUNTIFS(\'Game Log\'!$C$2:$C,"{role}",\'Game Log\'!$E$2:$E,"{outcome}")'
        f' - SUMIFS(\'Game Log\'!$F$2:$F,\'Game Log\'!$C$2:$C,"{role}",\'Game Log\'!$E$2:$E,"{outcome}")'
    )

def formula_player_most(pivot_col: str) -> str:
    return (
        f"=LET("
        f"jogadores,'Role Breakdown'!$A$3:$A$59,"
        f"counts,'Role Breakdown'!{pivot_col}$3:{pivot_col}$59,"
        f"datas,ARRAYFORMULA(IFERROR(VLOOKUP(jogadores,'Player Last Played'!$A$2:$C$58,2,FALSE),0)),"
        f"bucket,ARRAYFORMULA(IFERROR(VLOOKUP(jogadores,'Player Last Played'!$A$2:$C$58,3,FALSE),3)),"
        f"mask,ARRAYFORMULA(counts>0),"
        f"jogs_f,FILTER(jogadores,mask),"
        f"counts_f,FILTER(counts,mask),"
        f"bucket_f,FILTER(bucket,mask),"
        f"datas_f,FILTER(datas,mask),"
        f"sorted,SORT(HSTACK(jogs_f,counts_f,bucket_f,datas_f),3,TRUE,2,FALSE,4,FALSE),"
        f"ARRAY_CONSTRAIN(INDEX(sorted,,1),3,1))"
    )

def formula_player_least(pivot_col: str) -> str:
    return (
        f"=LET("
        f"jogadores,'Role Breakdown'!$A$3:$A$59,"
        f"counts,'Role Breakdown'!{pivot_col}$3:{pivot_col}$59,"
        f"datas,ARRAYFORMULA(IFERROR(VLOOKUP(jogadores,'Player Last Played'!$A$2:$C$58,2,FALSE),0)),"
        f"bucket,ARRAYFORMULA(IFERROR(VLOOKUP(jogadores,'Player Last Played'!$A$2:$C$58,3,FALSE),3)),"
        f"mask,ARRAYFORMULA(counts>0),"
        f"jogs_f,FILTER(jogadores,mask),"
        f"counts_f,FILTER(counts,mask),"
        f"bucket_f,FILTER(bucket,mask),"
        f"datas_f,FILTER(datas,mask),"
        f"sorted,SORT(HSTACK(jogs_f,counts_f,bucket_f,datas_f),3,TRUE,2,TRUE,4,FALSE),"
        f"ARRAY_CONSTRAIN(INDEX(sorted,,1),3,1))"
    )


# =============================================================================
# PARÂMETROS DISPONÍVEIS
# =============================================================================
PARAMS = {
    "1": "games_won",
    "2": "games_lost",
    "3": "gawain_loss",
    "4": "nimue_tie_loss",
    "5": "player_most",
    "6": "player_least",
    "7": "todos",
}

def _get_formula(param: str, role: str, is_evil: bool, row: int, pivot_col: str) -> tuple[str, str]:
    """Retorna (célula, fórmula) para um parâmetro e role."""
    col_most  = "B"
    col_least = "C"

    if param == "games_won":
        return CELLS_MAP[role]["games_won"], formula_games_won(role, is_evil)
    elif param == "games_lost":
        return CELLS_MAP[role]["games_lost"], formula_games_lost(role, is_evil)
    elif param == "gawain_loss":
        return CELLS_MAP[role]["gawain_loss"], formula_gawain_loss(role, is_evil)
    elif param == "nimue_tie_loss":
        return CELLS_MAP[role]["nimue_tie_loss"], formula_nimue_tie_loss(role, is_evil)
    elif param == "player_most":
        return f"{col_most}{row}", formula_player_most(pivot_col)
    elif param == "player_least":
        return f"{col_least}{row}", formula_player_least(pivot_col)


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 52)
    print("  Role Stats — Upload de Fórmulas")
    print("=" * 52)

    # --- Escolha dos parâmetros ---
    print("\nParâmetros disponíveis:")
    for k, v in PARAMS.items():
        print(f"  {k}) {v}")

    escolha = input("\nQuais parâmetros atualizar? (ex: 1 3 5  ou  7 para todos): ").strip().split()

    if "7" in escolha:
        params_selecionados = [v for k, v in PARAMS.items() if v != "todos"]
    else:
        params_selecionados = [PARAMS[e] for e in escolha if e in PARAMS and PARAMS[e] != "todos"]

    if not params_selecionados:
        print("Nenhum parâmetro válido selecionado.")
        return

    print(f"\n✅ Parâmetros selecionados: {', '.join(params_selecionados)}")

    # --- Conecta ao Sheets ---
    print("\n📊 Conectando ao Google Sheets...")
    creds  = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)

    try:
        planilha = client.open(SHEET_NAME)
        pagina   = planilha.worksheet(WORKSHEET_NAME)
    except Exception as e:
        print(f"❌ Erro ao acessar planilha: {e}")
        return

    # --- Atualiza ---
    total = len(CELLS_MAP)
    print(f"\n🔄 Atualizando {len(params_selecionados)} parâmetro(s) para {total} roles...\n")

    for role, cells in CELLS_MAP.items():
        is_evil    = role in EVIL_ROLES
        row        = cells["row"]
        pivot_col  = PIVOT_COL.get(role, "")

        print(f"📌 {role.title()} ({'Evil' if is_evil else 'Good'})")

        for param in params_selecionados:
            if param in ("player_most", "player_least") and not pivot_col:
                print(f"   ⚠️  Coluna pivot não mapeada para '{role}', pulando {param}")
                continue

            try:
                celula, formula = _get_formula(param, role, is_evil, row, pivot_col)
                pagina.update_acell(celula, formula)
                print(f"   ✅ {param:20s} → {celula}")
                time.sleep(SLEEP)
            except Exception as e:
                print(f"   ❌ Erro em {param}: {e}")

    print("\n✨ Pronto!")


if __name__ == "__main__":
    main()