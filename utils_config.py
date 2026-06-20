# utils_config

import os
import json
import discord
from dotenv import load_dotenv

try:
    from thefuzz import fuzz
except ImportError:
    try:
        from rapidfuzz import fuzz
    except ImportError:
        fuzz = None

load_dotenv()


_MODE = os.getenv("BOT_MODE", "prod").lower()
_PFX  = "DEV_" if _MODE == "dev" else "PROD_"
CONFIG_FILE     = f"game_data_{_MODE}.json"
BOT_CONFIG_FILE = f"bot_config_{_MODE}.json"

CACHE_FILE       = f"stats_cache_{_MODE}.json"
CACHE_GAMES_FILE = f"cache_games_{_MODE}.json"
CACHE_ROLES_FILE = f"cache_roles_{_MODE}.json"

# ==============================================================================
# VARIÁVEIS DE AMBIENTE / CONFIG
# ==============================================================================
def load_bot_config() -> dict:
    if not os.path.exists(BOT_CONFIG_FILE):
        return {}
    with open(BOT_CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_env_or_config(key: str, default=None):
    # Ordem de busca:
    # 1. PROD_KEY / DEV_KEY  (novo padrão com prefixo)
    # 2. KEY sem prefixo     (legado — ex: SERVER_ID, AVALON_SERVER_ID)
    # 3. AVALON_KEY          (alias antigo do main.py)
    # 4. bot_config JSON     (configurado via /config no Discord)
    value = (
        os.getenv(_PFX + key)
        or os.getenv(key)
        or os.getenv("AVALON_" + key)
    )
    if value:
        return int(value) if value.isdigit() else value
    config = load_bot_config()
    return config.get(key) or config.get(key.lower()) or default


GUILD_ID                      = get_env_or_config("SERVER_ID")
ROUND_TABLE_ID                = get_env_or_config("ROUND_TABLE_ID")
QUEST_CHAT_ID                 = get_env_or_config("QUEST_CHAT_ID")
STATS_CHANNEL_ID              = get_env_or_config("STATS_CHANNEL_ID")
GM_ROLE_ID                    = get_env_or_config("GM_ROLE_ID")
EVIL_ROLE_ID                  = get_env_or_config("EVIL_ROLE_ID")
KNIGHTS_OF_THE_ROUND_TABLE_ID = get_env_or_config("KNIGHTS_OF_THE_ROUND_TABLE_ID")
SHEET_NAME                    = get_env_or_config("SHEET_NAME")



PLAYER_ALIASES = {
    'archie': 'achilles',
    'sam': 'telletubie',
    'noodle': 'sky', 'bird': 'sky', 'birb': 'sky', 'skyla': 'sky', 'Rowlet' : 'sky',
    'ody': 'saige', 'marsy': 'mars', 'nox': 'nix',
    'silliest': 'silly',
    'gape': 'gabe',
    'nitrux': 'henry',
    'bell': 'belle',
    'marzy': 'mars', 'kris': 'krista', 'dyl': 'dyloune',
    'penguin':"blue", 'articpenguin' : 'blue', 'blue penguin' : 'blue'
}


def _fuzzy_match_name_local(
    candidate: str,
    known_players: list[str],
    threshold: int = 72,
) -> str | None:
    if not candidate or not known_players:
        return None

    cand_low = candidate.strip().lower()

    # tenta resolver pelo alias primeiro
    if cand_low in PLAYER_ALIASES:
        cand_low = PLAYER_ALIASES[cand_low]

    if len(cand_low) < 2:
        return None

    best_score, best_match = 0, None
    for known in known_players:
        known_low = known.lower()
        if cand_low == known_low:
            return known  # retorna com capitalização original da lista
        if fuzz:
            score = fuzz.ratio(cand_low, known_low)
        else:
            common = sum(1 for c in cand_low if c in known_low)
            score = int(100 * common / max(len(cand_low), len(known_low)))
        if score > best_score:
            best_score, best_match = score, known

    return best_match if best_score >= threshold else None