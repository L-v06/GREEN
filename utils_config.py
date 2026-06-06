# utils_config

import os
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


def get_env_or_config(key: str, default=None):
    value = os.getenv(key)
    return value if value is not None else default  # corrigido: agora retorna o valor


GUILD_ID = get_env_or_config("SERVER_ID")
ROUND_TABLE_ID = get_env_or_config("ROUND_TABLE_ID")



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