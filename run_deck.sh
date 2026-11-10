#!/bin/zsh
# Rebuild the rehearsal deck on TensorX: test call, extraction, then 300 cards. Safe to rerun (resumes).
set -e
cd "$(dirname "$0")"
ML=~/NailIt/library/model_level
uv run python -c "
from nailit.config import load_secrets; load_secrets()
from nailit.answers import ai
for m in ('tx:deepseek/deepseek-v4.1-flash-1017','tx:z-ai/glm-5.3','tx:deepseek/deepseek-v4-pro-0813','tx:moonshotai/kimi-k3.1-pro'):
    print(m, ai.chat(m, 'Reply {\"ok\": true}', json_mode=True, max_tokens=2000))"
uv run python -m nailit.answers.harvest --offline
[ -f $ML/deck.json ] && [ ! -f $ML/deck_v1_openai.json ] && mv $ML/deck.json $ML/deck_v1_openai.json
uv run python -m nailit.answers.generate --limit 300 2>&1 | tee ~/NailIt/deck_build.log
