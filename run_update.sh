#!/bin/zsh
# Update the cleaned deck on TensorX: redo weak cards, read the new sources, add cards for new questions.
# Safe to rerun. Log: ~/NailIt/deck_update.log
set -e
cd "$(dirname "$0")"
LOG=~/NailIt/deck_update.log
uv run python -c "
from nailit.config import load_secrets; load_secrets()
from nailit.answers import ai, generate as g
for m in dict.fromkeys([g.HELPER, g.DRAFTER, *g.JUDGES, g.WRITER]):
    print(m, ai.chat(m, 'Reply {\"ok\": true}', json_mode=True, max_tokens=2000))"
echo "== 1/3 redo: cards without follow-ups, and direct questions (salary, pay history, tools, logistics)" | tee $LOG
uv run python -m nailit.answers.generate --redo-unpolished \
  --redo "salary|compensation|earning now|software|tools|start\?|questions for us|hear about this|interviewing other" 2>&1 | tee -a $LOG
echo "== 2/3 read the 89 new sources (interviewing.io, Exponent, Hacker News) and regroup questions" | tee -a $LOG
uv run python -m nailit.answers.harvest --offline 2>&1 | tee -a $LOG
echo "== 3/3 add cards for questions the deck doesn't cover yet (both judges)" | tee -a $LOG
uv run python -m nailit.answers.generate --limit 100 2>&1 | tee -a $LOG
uv run python -m nailit.answers.curate --check 2>&1 | tee -a $LOG
