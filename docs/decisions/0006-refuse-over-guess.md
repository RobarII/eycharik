# 0006: Refuse over guess

Status: accepted. Date: 2026-10-23.

## Context

A wrong answer about vacation days, benefits, or probation is worse than no answer: the employee
acts on it, and HR learns about it later. Model confidence is not evidence. The cost of a wrong
answer is asymmetric, while the cost of an escalation is a few minutes of HR time.

## Decision

An answer is sent only if every citation refers to a chunk that was actually retrieved for that
question. If the model answers without a citation, cites an unseen chunk, or reports confidence
below the threshold, the answer is replaced by an escalation with the reason and the transcript.

The grounding check is deterministic code, not a second model call.

## Consequences

- Some answerable questions escalate; measured by `escalation_rate` and reviewed weekly.
- The refusal text is part of the product voice and is written in `answer-policy.md`.
- Escalated questions feed the knowledge backlog: the top unanswered questions become documents.
- The model is never the authority on whether its own answer is grounded.

## Alternatives

LLM-as-judge on every answer — rejected: doubles latency and cost, and shares the failure mode.
Showing the answer with a disclaimer — rejected: people act on confident text, not on disclaimers.
