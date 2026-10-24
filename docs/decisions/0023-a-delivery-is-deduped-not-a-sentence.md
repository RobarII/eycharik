# 0023: A delivery is deduped, a sentence is not

- Status: accepted
- Date: 2026-10-24
- Builds on: `0019-a-channel-is-an-address.md`

## Context

`0019` made the run follow the person: an answer from any linked messenger is answered there, the
run's address moves, and the move is audited as `channel_changed`. Two messengers now deliver into
one run, which raises a question one messenger never asked: what is a duplicate?

The dedupe key today is `channel:delivery_id` (`telegram:12345`, `vk:message_new:...`, a MAX event
id), and `events.key` is unique, so a messenger that redelivers an update adds nothing. That covers
the retries the APIs actually perform: Telegram retries until it gets `2xx`, VK retries
`message_new`, MAX retries on a non-`200`.

It does not cover a person who writes the same sentence twice in two apps. Both updates are new by
their own messenger's accounting, both are correctly linked to one employee, and both advance the
run. Two answers consume two steps. Live proof of the mechanism, both directions, is
`docs/measurements/2026-10-24-cross-channel-move.md`.

The obvious guard is content dedupe: drop an update whose text matches the previous update for the
same run from a different channel inside a window of N seconds. The step a survey answer lands on
looks like a way to tell them apart, but it is not: by the time the second update is processed the
run has already moved to the next step, so the guard compares an answer against the *next*
question, which is what a person legitimately does when they answer twice in a row.

## Decision

**Dedupe stays keyed on the messenger's delivery id. There is no content dedupe, on one channel or
across channels.**

A repeated sentence is an answer, not a duplicate. The run advances, the address moves to the
messenger that just answered, and both facts are audited.

## Consequences

- A retry by the messenger is free and exact: `events.key` is unique, so the second delivery is
  claimed once and never reaches the run.
- A person answering twice gets two steps, deliberately. On a survey that is two recorded answers,
  which is what the person did.
- A short answer that repeats legitimately (`ок` at two consecutive steps) is never swallowed. A
  window rule would silently drop it, and a dropped survey answer is data loss that nobody notices;
  an extra one is visible in `step_transition` and repairable through the cabinet.
- The audit is the repair tool, not a heuristic: `step_transition` names the step and the event for
  every advance, and `channel_changed` names both addresses for every move. A doubled answer shows
  as two transitions seconds apart from two channels.
- The smoke pins the accepted behaviour instead of leaving it to be rediscovered:
  `test_answers_from_two_messengers_are_two_answers` in `apps/api/tests/test_service.py`.

## Alternatives rejected

- **Content dedupe inside a time window.** Cannot separate "the same sentence sent from two apps"
  from "the same short answer to two consecutive questions". Rejected: it trades a visible,
  repairable duplicate for a silent loss.
- **Content dedupe keyed on `(step, text)`.** The second delivery is processed after the step has
  moved, so the key never matches, and a guard that never fires is worse than none: it reads like
  protection.
- **Refusing a plain message from a channel that is not the run's current address** (moving the
  address only on `/start`). Safe against the duplicate, but it breaks the promise of `0019`: a
  person who picks up their other phone to answer would be told to start over. Rejected.
- **Digesting the inbound text into `events.key`.** Two people, or one person at two steps, may
  send identical text; the digest would collide across runs and employees.
