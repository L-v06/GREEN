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
from utils_config import SHEET_NAME

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
# MAPEAMENTO DE CÉLULAS POR ROLE
# Evil  → player_most = B{row}, player_least = C{row}
# Good  → player_most = J{row}, player_least = K{row}
# As fórmulas de player encontram a coluna da pivot pelo nome da role automaticamente
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
# Mude aqui se precisar ajustar a lógica no futuro
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

def formula_player_most(role_display: str) -> str:
    # role_display = nome com capitalização correta (ex: "Bad Lancelot", "King Arthur")
    return (
        "=LET("
        f'roleName,"{role_display}",'
        "colNum,IFERROR(MATCH(roleName,'Role Breakdown'!$A$2:$AI$2,0),-1),"
        "players,'Role Breakdown'!$A$3:$A$59,"
        "counts,IF(colNum=-1,ARRAYFORMULA(IF(players<>\"\",0,\"\")),ARRAYFORMULA(OFFSET('Role Breakdown'!$A$3,0,colNum-1,57,1))),"
        "buckets,ARRAYFORMULA(IFERROR(VLOOKUP(players,backupthing!$A$2:$C$200,3,FALSE),999)),"
        "lastPlayed,ARRAYFORMULA(IFERROR(VLOOKUP(players,backupthing!$A$2:$B$200,2,FALSE),DATE(1900,1,1))),"
        "isCurrent,ARRAYFORMULA((buckets<=1)*ISNUMBER(counts)*(counts>0)),"
        "validCounts,ARRAYFORMULA(IF(isCurrent,counts,-1)),"
        "maxVal1,MAX(validCounts),"
        "tieDates1,ARRAYFORMULA(IF(validCounts=maxVal1,lastPlayed,DATE(1900,1,1))),"
        "newestDate1,MAX(tieDates1),"
        "name1,IFERROR(INDEX(players,MATCH(newestDate1,tieDates1,0)),\"\"),"
        "validCounts2,ARRAYFORMULA(IF(players=name1,-1,validCounts)),"
        "maxVal2,MAX(validCounts2),"
        "tieDates2,ARRAYFORMULA(IF(validCounts2=maxVal2,lastPlayed,DATE(1900,1,1))),"
        "newestDate2,MAX(tieDates2),"
        "name2,IF(maxVal2<=0,\"\",IFERROR(INDEX(players,MATCH(newestDate2,tieDates2,0)),\"\")),"
        "validCounts3,ARRAYFORMULA(IF(players=name2,-1,validCounts2)),"
        "maxVal3,MAX(validCounts3),"
        "tieDates3,ARRAYFORMULA(IF(validCounts3=maxVal3,lastPlayed,DATE(1900,1,1))),"
        "newestDate3,MAX(tieDates3),"
        "name3,IF(maxVal3<=0,\"\",IFERROR(INDEX(players,MATCH(newestDate3,tieDates3,0)),\"\")),"
        "IF(colNum=-1,\"Role not found\",IF(maxVal1<=0,\"N/A\",VSTACK(name1,IF(name2=\"\",\"\",name2),IF(name3=\"\",\"\",name3)))))"
    )

def formula_player_least(role_display: str) -> str:
    return (
        "=LET("
        f'roleName,"{role_display}",'
        "colNum,IFERROR(MATCH(roleName,'Role Breakdown'!$A$2:$AI$2,0),-1),"
        "players,'Role Breakdown'!$A$3:$A$59,"
        "counts,IF(colNum=-1,ARRAYFORMULA(IF(players<>\"\",0,\"\")),ARRAYFORMULA(OFFSET('Role Breakdown'!$A$3,0,colNum-1,57,1))),"
        "buckets,ARRAYFORMULA(IFERROR(VLOOKUP(players,backupthing!$A$2:$C$200,3,FALSE),999)),"
        "lastPlayed,ARRAYFORMULA(IFERROR(VLOOKUP(players,backupthing!$A$2:$B$200,2,FALSE),DATE(2099,1,1))),"
        "isCurrent,ARRAYFORMULA((buckets<=1)*ISNUMBER(counts)*(counts>0)),"
        "validCounts,ARRAYFORMULA(IF(isCurrent,counts,999999)),"
        "minVal1,MIN(validCounts),"
        "tieDates1,ARRAYFORMULA(IF(validCounts=minVal1,lastPlayed,DATE(2099,1,1))),"
        "oldestDate1,MIN(tieDates1),"
        "name1,IFERROR(INDEX(players,MATCH(oldestDate1,tieDates1,0)),\"\"),"
        "validCounts2,ARRAYFORMULA(IF(players=name1,999999,validCounts)),"
        "minVal2,MIN(validCounts2),"
        "tieDates2,ARRAYFORMULA(IF(validCounts2=minVal2,lastPlayed,DATE(2099,1,1))),"
        "oldestDate2,MIN(tieDates2),"
        "name2,IF(minVal2>=999999,\"\",IFERROR(INDEX(players,MATCH(oldestDate2,tieDates2,0)),\"\")),"
        "validCounts3,ARRAYFORMULA(IF(players=name2,999999,validCounts2)),"
        "minVal3,MIN(validCounts3),"
        "tieDates3,ARRAYFORMULA(IF(validCounts3=minVal3,lastPlayed,DATE(2099,1,1))),"
        "oldestDate3,MIN(tieDates3),"
        "name3,IF(minVal3>=999999,\"\",IFERROR(INDEX(players,MATCH(oldestDate3,tieDates3,0)),\"\")),"
        "IF(colNum=-1,\"Role not found\",IF(minVal1>=999999,\"N/A\",VSTACK(name1,IF(name2=\"\",\"\",name2),IF(name3=\"\",\"\",name3)))))"
    )

# Capitalização correta de cada role para o MATCH na pivot
ROLE_DISPLAY = {
    "assassin":               "Assassin",
    "bertilak":               "Bertilak",
    "dagonet":                "Dagonet",
    "lucius":                 "Lucius",
    "maduc":                  "Maduc",
    "mark":                   "Mark",
    "meleagant":              "Meleagant",
    "mordred":                "Mordred",
    "morgana":                "Morgana",
    "oberon":                 "Oberon",
    "puck":                   "Puck",
    "queen mab":              "Queen Mab",
    "vortigern":              "Vortigern",
    "minion":                 "Minion",
    "bad lancelot":           "Bad Lance",
    "nimue (e)":              "Nimue (E)",
    "the witch of caerlloyw": "The Witch of Caerlloyw",
    "merlin":                 "Merlin",
    "apprentice":             "Apprentice",
    "caelia":                 "Caelia",
    "elaine":                 "Elaine",
    "galahad":                "Galahad",
    "gawain":                 "Gawain",
    "guinevere":              "Guinevere",
    "king arthur":            "King Arthur",
    "palamedes":              "Palamedes",
    "percival":               "Percival",
    "sir kay":                "Sir Kay",
    "loyal servant":          "Loyal Servant",
    "tristan":                "Tristan",
    "iseult":                 "Iseult",
    "lancelot":               "Lancelot",
    "nimue (g)":              "Nimue (G)",
    "penpingion":             "Penpingion",
}

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

def _get_formula(param: str, role: str, is_evil: bool, row: int) -> tuple[str, str]:
    """Retorna (célula, fórmula) para um parâmetro e role."""
    col_most  = "B" if is_evil else "J"
    col_least = "C" if is_evil else "K"
    display   = ROLE_DISPLAY.get(role, role.title())

    if param == "games_won":
        return CELLS_MAP[role]["games_won"], formula_games_won(role, is_evil)
    elif param == "games_lost":
        return CELLS_MAP[role]["games_lost"], formula_games_lost(role, is_evil)
    elif param == "gawain_loss":
        return CELLS_MAP[role]["gawain_loss"], formula_gawain_loss(role, is_evil)
    elif param == "nimue_tie_loss":
        return CELLS_MAP[role]["nimue_tie_loss"], formula_nimue_tie_loss(role, is_evil)
    elif param == "player_most":
        return f"{col_most}{row}", formula_player_most(display)
    elif param == "player_least":
        return f"{col_least}{row}", formula_player_least(display)


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 52)
    print("  Role Stats — Upload de Fórmulas")
    print("=" * 52)

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

    print("\n📊 Conectando ao Google Sheets...")
    creds  = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)

    try:
        planilha = client.open(SHEET_NAME)
        pagina   = planilha.worksheet(WORKSHEET_NAME)
    except Exception as e:
        print(f"❌ Erro ao acessar planilha: {e}")
        return

    total = len(CELLS_MAP)
    print(f"\n🔄 Atualizando {len(params_selecionados)} parâmetro(s) para {total} roles...\n")

    for role, cells in CELLS_MAP.items():
        is_evil = role in EVIL_ROLES
        row     = cells["row"]

        print(f"📌 {ROLE_DISPLAY.get(role, role.title())} ({'Evil' if is_evil else 'Good'})")

        for param in params_selecionados:
            try:
                celula, formula = _get_formula(param, role, is_evil, row)
                pagina.update_acell(celula, formula)
                print(f"   ✅ {param:20s} → {celula}")
                time.sleep(SLEEP)
            except Exception as e:
                print(f"   ❌ Erro em {param}: {e}")

    print("\n✨ Pronto!")


if __name__ == "__main__":
    main()