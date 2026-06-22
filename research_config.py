RESEARCH_TIER = "starter"

TIER_CONFIG = {
    "free": {
        "vercel_searches": 5,
        "round_searches": 2,
        "round_extracts": 1,
        "parallel_rounds": False,
        "search_depth": "basic",
        "max_credits_per_session": 35,
    },
    "starter": {
        "vercel_searches": 8,
        "round_searches": 3,
        "round_extracts": 2,
        "parallel_rounds": False,
        "search_depth": "advanced",
        "max_credits_per_session": 70,
    },
    "production": {
        "vercel_searches": 10,
        "round_searches": 5,
        "round_extracts": 3,
        "parallel_rounds": True,
        "search_depth": "advanced",
        "max_credits_per_session": 150,
    }
}

def get_config():
    return TIER_CONFIG[RESEARCH_TIER]

def get_credit_estimate(num_rounds):
    cfg = get_config()
    per_round = (cfg["round_searches"] * 1) + (cfg["round_extracts"] * 3)
    return cfg["vercel_searches"] + (per_round * num_rounds)
