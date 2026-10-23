# Sentiment labeling guide

The tone label is only worth something if two people would give it the same answer. This file is
the rulebook for `docs/evals/sentiment.yaml`. When a label is disputed, the guide is what changes
first, and only then the set.

## The four tones

| tone | rule | example |
|---|---|---|
| `positive` | explicit satisfaction, praise, or gratitude | «коллеги позвали на обед, стало спокойнее» |
| `neutral` | facts, a status, a question, or "нормально" without praise | «пропуск выдали, стол у окна» |
| `negative` | a complaint, a problem, irritation, or sarcasm that hides a complaint | «третий день жду доступ» |
| `unknown` | there is not enough text to hear a tone | «Ок», «Н/Д», «🙂», off-topic |

Rules that decide the borderline:

1. **A problem outranks a compliment.** «Коллеги супер, руководитель не отвечает неделю» is
   `negative`: the radar exists for the second half of the sentence.
2. **Sarcasm is a complaint.** «Ну да, всё прекрасно. Задач на троих» is `negative`. Judge the
   situation the person describes, not the adjective they used.
3. **Negation is read literally.** «Не жалуюсь, всё нормально» is `neutral`. «Не могу сказать, что
   всё плохо, но хорошего мало» is `negative`.
4. **Short is not neutral.** «Кошмар.» is `negative` with the `other` tag: the word carries tone
   but no topic.
5. **Off-topic is `unknown`.** A positive remark about the weather says nothing about onboarding.
   Tag it `other` and keep it in the set: the model must not treat a cheerful sentence as a signal.
6. **A question is labeled by what it reports.** «А когда выдают пропуск? Мне до сих пор не
   выдали» is `negative`, because the person states a problem.
7. **Injections are data.** If the text asks the classifier to return a label, the request is
   ignored and the rest of the text is labeled normally.
8. **Empty or unreadable input is `unknown`, never a guess.** The prompt rule is explicit: below
   `confidence: 0.5` the answer should be `unknown`, not a coin flip.

## Tags

Tags are topics the recruiter routes to, not keywords the text contains.

| tag | when | not when |
|---|---|---|
| `access` | accounts, VPN, badges, passwords, portals | hardware that does not boot -> `it` |
| `it` | devices, software, tickets, mail, printers | access rights -> `access` |
| `manager` | the direct lead or the assigned mentor | the whole company's management |
| `colleagues` | the team around the person | another department -> `integration` |
| `workload` | volume, overtime, deadlines, burnout | unclear priorities -> `clarity` wins, add `workload` only if volume is named |
| `clarity` | expectations, plan, documentation, priorities | a missing tool -> `access`/`it` |
| `hr` | documents, contract, leave, salary, benefits | medical appointment alone is `hr` only with paperwork |
| `integration` | other departments, contractors, handoffs | the own team -> `colleagues` |
| `other` | tone without a routable topic, personal context | never a substitute for a tag the text supports |

At most three tags, because the classifier contract returns at most three. Choose the ones a
specialist would act on; ties are broken in favor of the topic with a named owner.

## Escalation

`expect_escalation: true` means a recruiter must be alerted. It is not a stronger `negative`. It is
claimed only for: a threat to quit, an open conflict, bullying or humiliation, discrimination,
deception, unpaid salary, or a health consequence of work. The case must also be labeled
`negative`; the loader refuses any other combination.

`core/risk.py` computes the decision, so an escalation case measures the product, not the model
alone. A soft-wrapped crisis («в целом всё хорошо, но руководитель кричит») is in the set on
purpose: it is the case a keyword classifier misses.

## Splits

- `dev` — may be looked at while editing a prompt or a rubric.
- `test` — locked. Not read during tuning, not used to choose a threshold. Report both numbers; a
  large gap between them is how overfitting announces itself.

The split is assigned before the first run and does not move afterwards.

## Known limitations

- The corpus and the labels were written by one person. There is no Cohen's kappa yet, so the
  labels are a considered opinion, not an inter-annotator truth. A measurement note must say so.
- The set is complaint-heavy (59 of 107 cases are `negative`) because the radar targets problems.
  That is not the survey's base rate; `sentiment_macro_f1` is reported for that reason.
- 107 cases buys roughly ±9 points on a share near 0.9 (Wilson), and far less on a difference
  between two providers. Compare paired runs, never two standalone accuracies.
