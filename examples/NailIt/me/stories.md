# Stories (synthetic example; your real file lives in ~/NailIt/me/)

## Facts
F1 | Led a migration of the billing service to a new queue | confirmed | performance review
F2 | Cut failed payments from about 9 to 3 per week | approximate | team dashboard
F3 | Team of 4 engineers | confirmed | org chart

## S1 Billing queue migration
```yaml
facts: [F1, F2, F3]
trigger: Tell me about a time you improved reliability.
alt_triggers: [Biggest technical decision you made]
answers: [disagree_with_manager]
lp_tags: [ownership]
competencies: [delivery, decisions]
stages:
  HOOK: Failed payments were costing us customers (F2).
  WORLD: A team of 4 owned billing (F3).
  CALL: I proposed moving to a new queue (F1).
  CROSSROADS: Patch the old system or migrate.
  ORDEAL: The migration window clashed with a launch.
  RESULT: Failed payments dropped from about 9 to 3 a week (F2).
  RESULT_OF_RESULT: Support stopped escalating billing tickets.
  LESSON: Reliability work needs a visible weekly number.
ally: the support lead
my_part: wrote the plan and ran the cut-over
team_part: two engineers built the consumers
trade_off: slower feature work for two sprints
rejected_option: patching the old queue
obstacle_internal: I wanted to do it all myself
obstacle_external: a launch in the same month
transformation: from firefighting to measuring
stakeholder_outcome: support had fewer escalations
punchline: We stopped losing payments we had already won.
opening_hook: Every failed payment was a customer we had already won.
goal_verb: stabilise
delivery_cues: [pause after the number]
compressed:
  3_words: Queue, measured, fixed
  1_sentence: I led a billing queue migration that cut failed payments by about two thirds.
  30s: Failed payments were about 9 a week; I proposed and ran a queue migration with a team of 4 and we got to about 3.
  90s: Full HOOK to LESSON version, result first.
plot_type: overcoming the monster
type: success
concerns: [the numbers are approximate]
confidential: false
```
