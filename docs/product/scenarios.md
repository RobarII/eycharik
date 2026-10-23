# Onboarding scenarios

A scenario is data: YAML validated by [scenario.schema.json](../contracts/scenario.schema.json).
A run pins the version it started on, so editing a scenario never strands a live newcomer. Every
step also has a human-readable `title`; the cabinet shows it instead of the raw `step_id`.

## First run: `onboarding_default` v1

| Step | Kind | What happens | Timeout |
|---|---|---|---|
| `welcome` | send | greeting, then the first-day checklist follows automatically | — |
| `first_day_checklist` | wait | pass, laptop, mentor, access checklist; buttons "Готово" / "Задать вопрос" both lead to the next step | 48 h → remind |
| `meet_the_team` | wait | mentor and team; expects a reply, default route to documents | 72 h → remind |
| `documents` | wait | passport, SNILS, INN, diploma, photo; expects a file, default route to the week-one check | 72 h → escalate and move on |
| `week_one_check` | wait | three questions about the first week; any acknowledgement finishes the run | 48 h → escalate |
| `done` | terminal | completed; no timeout, no routes | — |

Free text at a step that expects a button or a file is answered by the assistant and the run does
not move. At a step that expects a message, a question is answered and the run stays; a plain
acknowledgement ("готово", "отправил") advances the step. The check is deterministic
(`core.transitions.is_question`), not a model decision.

Timeout actions are `remind` (send a nudge, keep the run) or `escalate` (hand the run to the
recruiter, optionally continue with `next`). Documents uses `escalate` with `next` so a newcomer who
never sends files still gets to the week-one check and a human sees the stall.

## Deployed scenarios

| Scenario | Version | Shape |
|---|---|---|
| `onboarding_default` | 1 | five-step demo: welcome, first day, team, documents, week one |
| `onboarding_default` | 2 | the client timeline: day before, day one, day three, two weeks, month two, end of probation |
| `onboarding_plant` | 1 | the plant variant: same timeline, own transport copy, no remote-work question |

Version 1 stays deployed after version 2 ships: a run is pinned to the version it started with, so
editing content never rewrites someone's script mid-onboarding.

The timeline is relative, not absolute. The client's spreadsheet names clock times ("day one,
12:00"); a scenario names delays ("three hours after the previous step"). Absolute times would
need a per-site working calendar, which the pilot does not have yet.

## Surveys

A `survey` step asks its `questions` one at a time and stores every answer in the run. Three
question kinds exist:

| Kind | Input | Follow-up |
|---|---|---|
| `choice` | the option buttons drawn from `options` | none |
| `scale` | a number from 1 to 10 | a score below `low_threshold` asks `reason_prompt` before the survey continues |
| `open` | free text | the answer goes to the sentiment classifier |

Every free-text answer, including a reason, produces a risk signal. Scores and text are evaluated
by the pure rules in `core/risk.py`: a negative answer with a tag, or a confident complaint plus a
low score, escalates to `escalate_to`; a weak signal only feeds the weekly digest. A survey has no
routes: it ends at `next`, and its `timeout` re-asks the current question.

A scenario may declare `segments` (production sites). The run picks the scenario that matches the
employee's site at creation time, so office copy and plant copy never mix.

## Recruiter flows

| Flow | Trigger | Behaviour |
|---|---|---|
| Stall detection | no step progress past its timeout | escalation audit row with the step and the reason |
| Progress overview | cabinet list | current step title, progress fraction, last activity, status |
| Question inbox | assistant cannot ground an answer | question, owner, reason, citations; scoped to the recruiter's employees |
| Role scoping | recruiter vs HR token | recruiter sees own employees, HR sees all; enforced by SQL, out-of-scope is 404 |
| Audit trail | every transition and escalation | append-only `audit_log`, read in the run detail |

Manual nudges from the cabinet are not implemented: the cabinet is read-only in v1. Sending a
message to a newcomer stays with the bot's scenario messages and the human HR channel.

## Rules

1. Every `wait` step has a timeout with an action; a step without one is a review blocker.
2. Every keyboard button id is unique inside the scenario; the router maps id to a route, never to
   free text.
3. A terminal step has no timeout and no routes.
4. Escalation never blocks the scenario: the run continues when the answer arrives.
5. A survey answer is stored before the next question is sent; a repeated delivery must not lose it.
6. Copy is Russian, in the company voice, second person plural ("вы"), no emoji in scenario text.
