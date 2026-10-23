# Onboarding scenarios

A scenario is data: YAML validated by [scenario.schema.json](../contracts/scenario.schema.json).
A run pins the version it started on, so editing a scenario never strands a live newcomer.

## First run: `onboarding_default` v1

| Step | Kind | What happens | Timeout |
|---|---|---|---|
| `welcome` | send | greeting, three buttons: "С чего начать", "Мой наставник", "Задать вопрос" | — |
| `first_day_checklist` | wait | checklist message, expects a button press | 48 h → remind, then escalate to recruiter |
| `meet_the_team` | send | team, mentor, first-week meetings | 72 h → remind |
| `documents` | wait | list of documents to bring, expects a file or a button "Готово" | 72 h → remind, then escalate to recruiter |
| `ask_anything` | wait | free questions go to the assistant; a human handoff button is always visible | 5 days → remind |
| `week_one_check` | wait | three-question quiz, any answer routes to `week_one_done` | 48 h → escalate |
| `done` | terminal | completion message and a feedback link | — |

Free text at any `wait` step is answered by the assistant; the scenario position does not move
unless the step expects a message.

## Recruiter flows

| Flow | Trigger | Behaviour |
|---|---|---|
| Stall detection | no step progress past its timeout | escalation row with the step and the last activity |
| Manual nudge | recruiter sends a message | delivered by the bot, recorded in the transcript |
| Escalation inbox | assistant cannot ground an answer | question, retrieved chunk ids, and confidence attached |
| Progress overview | cockpit list | current step, progress fraction, open escalations, last activity |

## Rules

1. Every `wait` step has a timeout with an action; a step without one is a review blocker.
2. Every keyboard button id is unique inside the scenario; the router maps id to a route, never
   to free text.
3. A terminal step has no timeout and no routes.
4. Escalation never blocks the scenario: the run continues when the answer arrives.
5. Copy is Russian, in the company voice, second person plural ("вы"), no emoji in scenario text.
