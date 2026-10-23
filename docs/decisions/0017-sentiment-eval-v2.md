# 0017 — The sentiment eval is a measuring instrument, not a demo

Date: 2026-10-23
Status: accepted

## Context

ADR 0011 shipped three sentiment providers behind one port, and measured two of them on a 16-case
set: `keyword` at 0.375 tone accuracy and `prompt` at 0.875. Those numbers answered "does it work at
all". They could not answer the questions a reviewer actually asks:

- is 0.875 different from 0.938, or is that one case out of sixteen?
- does the classifier miss a crisis, and does the product escalate it?
- does the answer survive a second call, or does the verdict move?
- can a run be broken by a provider outage while still printing a confident table?

A set that small with point estimates only is a demo. Worse, the first full run of the new set
returned `fallback_rate = 1.000` — a tripped circuit breaker — and the runner still wrote a
measurement file. An instrument that reports numbers during an outage is the failure mode this ADR
closes.

## Decision

`docs/evals/sentiment.yaml` is now version 2: 107 cases, `dev`/`test` split assigned before the
first run, every tone and every tag present in both halves, and `expect_escalation` for the cases a
recruiter must be alerted about. The label rules live in
`docs/evals/sentiment-guide.md` and change before a label does.

The runner (`apps/api/onboarding/evals/sentiment.py`) is held to five rules:

1. **Every share carries a Wilson 95% interval.** A share without an interval is not reportable.
2. **Tone quality is reported as macro F1, per-tone recall, and a confusion matrix.** Accuracy alone
   lets a dead class hide behind a common one.
3. **Escalation is measured through `core/risk.py`**, the code that decides in production, and
   missed escalations are listed by name. This is the metric that outranks the averages.
4. **Repetition is part of the run.** `--repeat N` calls the provider N times per case, reports
   pooled and per-case majority accuracy, and names the cases whose verdict moved. No gate may be
   tighter than that instability.
5. **A degraded provider aborts the run.** More than 10% infrastructure fallbacks (a timeout, a
   breaker, a 5xx) exits non-zero and writes nothing. A malformed model answer is *not* an outage:
   it stays in the table as a model result.

Every run writes the Markdown table and a JSONL artifact with one line per call. `--compare
<artifact>` runs a paired bootstrap over the cases both runs scored and reports the delta, its 95%
interval, and `p(delta <= 0)`. Two standalone accuracies are never compared again.

## Measured

Same set, same machine, `--min-interval 0.5`, provider `deepseek-v4.1-flash` via the
`opencode-deepseek-v4.1-flash` profile. Files are in `docs/measurements/`.

| run | cases | accuracy [95% CI] | macro F1 | escalation recall | fallback rate |
|---|---|---|---|---|---|
| keyword, test | 58 | 0.345 [0.24, 0.47] | 0.297 | 0.600 | 0.000 |
| prompt, test, 3 reps | 58 | 0.770 [0.70, 0.83] | 0.606 | 0.800 | 0.195 |
| prompt, dev, 1 rep | 49 | 0.816 [0.69, 0.90] | 0.743 | 0.800 | 0.245 |

Paired bootstrap, prompt vs keyword on the same 58 test cases: `case_accuracy` 0.776 vs 0.345,
delta **+0.431**, 95% CI **[0.29, 0.57]**, `p(delta <= 0) = 0.000`. The model is better than
keywords; that was never in doubt, and now it is stated with a number that has an interval.

Jev has no row: `JEV_API_KEY` is absent. The runner refuses to score it rather than guess.

Three findings the old set could not produce:

1. **19.5% of prompt calls return unparseable JSON** and fall back to keywords. The same model
   sometimes answers `{"messages": []}` or echoes a `{"role": "user", ...}` envelope. This is a
   prompt/model defect with a price: one in five survey answers is labeled by keywords.
2. **24 of 58 cases changed tone between three identical calls** at `temperature: 0.0`. Any gate on
   this provider must be wider than that instability, or it will fail on noise.
3. **`false_alarm_rate` is 0.403.** `core/risk.py` turns every negative answer into high +
   recruiter, so four calm answers in ten would page a person. That is a product rule, not a
   classifier defect, and it is now visible in a table instead of an argument.

## Consequences

- A quality claim about the radar quotes `case_accuracy` with an interval, the split, the commit,
  and the fallback rate. Without all four it is an anecdote.
- The prompt provider's 19.5% format fallback is the first thing to fix; until then the prompt
  classifier's measured quality is partly the keyword classifier's.
- A gate is still absent. The next step is a threshold derived from this baseline minus the interval
  width, on a provider whose instability is known.
- Labels were written by one annotator. The set is a considered opinion, not an inter-annotator
  truth; a kappa run on a sample is the next step, and every measurement note says so.
- ADR 0011 stands. Its v1 numbers are not comparable with these and are not restated.

## Alternatives

- Keep the 16-case set and add intervals — rejected: 16 cases buys ±16 points, so no interval
  separates the providers anyone cares about.
- Score with an LLM judge — rejected: another unmeasured model in the measuring path, and this
  task has a small closed label space a human can own.
- Tune the prompt until the test split passes — rejected: that is how a test set stops being one.
