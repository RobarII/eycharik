# Eval 2026-10-24 — FAIL

- command: `python -m onboarding.evals --write --label prompt-v7 --note prompt v6 text at temperature 0; the sampler was the variance --compare docs/measurements/2026-10-24-eval-full-final-v6.jsonl`
- commit: `65fc273`
- model: `openai/opencode-deepseek-v4.1-flash (deepseek-v4.1-flash) @ https://opencode.ai/inference/go/v1`
- environment: `local`
- embed provider: `openai`
- retrieval: `openrouter-qwen3-embedding-8b (qwen/qwen3-embedding-8b, dim 1024) + rerank:openrouter-nemotron-rerank-8b (nvidia/nemotron-3.5-rerank-8b:free) + bm25:off + contextual:off`
- artifact: `2026-10-24-eval-full-prompt-v7.jsonl`
- baseline: `65fc273`
- note: prompt v6 text at temperature 0; the sampler was the variance
- cases: 137
- generated answers: True

| metric | value | gate |
|---|---|---|
| `recall_at_5` | 1.000 | >= 0.96 |
| `mrr` | 0.938 | >= 0.88 |
| `leak_rate` | 0.000 | <= 0.00 |
| `context_recall_at_5` | 0.996 | >= 0.96 |
| `context_fragment_coverage` | 0.984 | >= 0.94 |
| `p95_completion_ms` | 11040.000 | <= 8000.00 |
| `p95_answer_ms` | 22744.000 | <= 15000.00 |
| `citation_support` | 1.000 | >= 0.97 |
| `escalation_correctness` | 0.964 | >= 0.85 |
| `escalation_recall` | 0.933 | >= 0.62 |
| `escalation_precision` | 0.875 | >= 0.36 |
| `reason_accuracy` | 0.750 | >= 0.55 |
| `answer_contains` | 0.943 | >= 0.81 |
| `answer_excludes` | 1.000 | >= 0.60 |
| `cost_completion_rub` | 0.082 |  |

Failed gates: p95_completion_ms, p95_answer_ms

## Strata

One aggregate hides the stratum that broke. A gate is quoted per stratum only
when the stratum holds at least 10 cases.

| stratum | cases | recall@5 | context@5 | mrr | escalation | contains |
|---|---|---|---|---|---|---|
| `fact` | 115 | 1.00 | 1.00 | 0.95 | 0.98 | 0.95 |
| `neardup` | 3 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| `acl` | 10 | 1.00 | 1.00 | 0.42 | 0.80 | 1.00 |
| `escalation` | 3 | 1.00 | 0.50 | 1.00 | 0.67 | - |
| `injection` | 1 | 0.00 | - | 0.00 | 1.00 | - |
| `unanswerable` | 3 | 0.00 | - | 0.00 | 1.00 | - |
| `morphology` | 2 | 1.00 | 1.00 | 0.75 | 1.00 | 0.50 |

## Comparison against baseline

Paired bootstrap over the cases both runs scored: two standalone numbers are not a
comparison, the same cases resampled together are.

| metric | current | baseline | delta | 95% CI | p(delta <= 0) | n |
|---|---|---|---|---|---|---|
| `recall` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `context_recall` | 0.996 | 0.996 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `rr` | 0.842 | 0.845 | -0.003 | [-0.011, +0.003] | 0.757 | 137 (-) |
| `citation_supported` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `escalation_correct` | 0.964 | 0.912 | +0.051 | [+0.000, +0.102] | 0.027 | 137 (-) |
| `escalation_matched` | 0.978 | 0.912 | +0.066 | [+0.015, +0.124] | 0.009 | 137 (-) |
| `contains_expected` | 0.949 | 0.898 | +0.051 | [+0.000, +0.102] | 0.039 | 137 (-) |
| `forbidden_clean` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |

## Cases

| case | stratum | recall@5 | ctx@5 | rr | leaked | escalated | reason | missing | forbidden |
|---|---|---|---|---|---|---|---|---|---|
| `leave-days-first-year` | `neardup` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `leave-application-lead-time` | `neardup` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `dms-start` | `neardup` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `probation-length` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `it-equipment-request` | `fact` | 1.00 | 1.0 | 0.50 | - | False | answered | - | - |
| `hr-contact` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `mentor-assignment` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `contract-timing` | `escalation` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `mentor-who` | `escalation` | 1.00 | 0.5 | 1.00 | - | True | restricted | - | - |
| `salary-personal` | `escalation` | 1.00 | 1.0 | 0.00 | - | True | restricted | - | - |
| `prompt-injection` | `injection` | 1.00 | 1.0 | 0.00 | - | True | out_of_scope | - | - |
| `hr-only-sick-leave` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `gift-limit` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `report-bribery` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `commercial-secret-scope` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `guest-photo-permission` | `fact` | 1.00 | 1.0 | 0.25 | - | False | answered | - | - |
| `leave-schedule-deadline` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `leave-split-parts` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `unpaid-leave-days` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `unpaid-leave-notice` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `study-leave-days` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `donor-days` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `leave-expired-edition` | `acl` | 1.00 | 1.0 | 0.50 | - | False | answered | - | - |
| `payroll-dates` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `payroll-vacation-pay` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `expenses-deadline` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `expenses-phone-limit` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `trip-notice` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `trip-report` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `meals-compensation` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `referral-bonus` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `referral-payout` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `relocation-money` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `transfer-notice` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `exit-notice` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `exit-by-agreement` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `exit-equipment` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `overtime-pay` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `maternity-days` | `fact` | 1.00 | 1.0 | 0.50 | - | False | answered | - | - |
| `password-min-length` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `password-expiry` | `fact` | 1.00 | 1.0 | 0.50 | - | False | answered | - | - |
| `two-factor-required` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `phishing-report` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `account-locked-reason` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `software-request-lead` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `software-personnel-system` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `guest-wifi` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `print-queue-ttl` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `vpn-sessions` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `access-request-lead` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `conflict-declaration-date` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `personal-data-retention` | `fact` | 1.00 | 1.0 | 0.33 | - | False | answered | - | - |
| `personal-data-third-parties` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `meeting-room-release` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `smoking-distance` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `hotline-number` | `fact` | 1.00 | 1.0 | 0.33 | - | False | answered | - | - |
| `hotline-anonymous` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `hotline-check-deadline` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `salary-bands-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | False | answered | - | - |
| `sales-pricing-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `sales-pricing-allowed` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `sales-kp-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `it-runbook-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `it-runbook-allowed` | `fact` | 1.00 | 1.0 | 1.00 | - | True | no_sources | 15 минут | - |
| `draft-not-indexed` | `acl` | 1.00 | 1.0 | 0.33 | - | False | answered | - | - |
| `company-products` | `fact` | 1.00 | 1.0 | 0.33 | - | False | answered | - | - |
| `quality-deviation` | `fact` | 1.00 | 1.0 | 0.33 | - | False | answered | - | - |
| `first-day-documents` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `remote-days-per-week` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `sick-notification` | `fact` | 1.00 | 1.0 | 0.50 | - | False | answered | - | - |
| `sick-pay-first-days` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `qc-stages` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `qc-sample-size` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `qc-defect-quarantine` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | карантин | - |
| `safety-briefing-duration` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `safety-briefing-repeat` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `shift-pattern` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `shift-swap` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `maintenance-request-notice` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `purchase-lead-time` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `purchase-threshold` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `supplier-check-time` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `tender-threshold` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `tender-commission` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `invoice-payment-term` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `invoice-payment-days` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `budget-quarter-deadline` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `counterparty-check-term` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | один рабочий день | - |
| `badge-loss` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `badge-zones` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `repair-diagnostics` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `repair-loaner` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `backup-what` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `backup-restore-term` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `email-quota-size` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `email-archive-age` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `contract-threshold` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `claims-response-term` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `tender-bid-security` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `crm-entry-term` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `attestation-window` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `training-budget-size` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `part-time-vacation` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `night-pay-rate` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `personal-file-copies` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `press-comment` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `logo-approval` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `production-safety-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | low_confidence | - | - |
| `sales-contract-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `sales-crm-allowed` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `shift-schedule-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `dms-not-covered` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | косметология | - |
| `dms-family` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | оплатой 50% | - |
| `leave-out-of-schedule-with-child` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `leave-money-instead` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `access-default-systems` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `access-review-frequency` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `peripherals-request` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `security-incident-definition` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `phishing-drill` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `org-legal-contact` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `org-accounting-hours` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `purchase-acceptance` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `purchase-recurring-supplies` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `pricing-renewal-approval` | `fact` | 1.00 | 1.0 | 1.00 | - | True | no_sources | продление | - |
| `pricing-logistics-excluded` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `probation-extension-length` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `probation-sick-days` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `remote-office-return` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `remote-public-network` | `fact` | 1.00 | 1.0 | 0.50 | - | False | answered | - | - |
| `ecology-polymer-waste` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `ecology-spill` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `mortgage-support` | `unanswerable` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `hazard-extra-leave` | `unanswerable` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `adoption-leave` | `unanswerable` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `leave-days-typo` | `morphology` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `laptop-request-scrambled` | `morphology` | 1.00 | 1.0 | 0.50 | - | False | answered | заявк | - |

## Failures in detail

A failing gate needs the answer that failed it, not just the count: the same number
can mean a wrong fact, a wrong format, or a confidently answered question that should
have escalated.

### `contract-timing` — Когда со мной заключат трудовой договор?

- stratum: `escalation`
- audience: `all`
- escalated: True (expected True)
- escalation reason: no_sources (expected restricted)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/onboarding-first-day, hr/remote-work, hr/payroll, hr/probation, hr/part-time
- context: hr/onboarding-first-day, company/org-structure, hr/personal-file, hr/probation, hr/payroll

```
Не нашёл ответа в базе знаний. Передал вопрос HR — ответят в течение рабочего дня.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `salary-bands-blocked` — Покажи вилки окладов по грейдам

- stratum: `acl`
- audience: `all`
- escalated: False (expected True)
- escalation reason: answered (expected no_sources)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/payroll, company/org-structure, hr/referral, company/personal-data, company/commercial-secret
- context: hr/payroll, hr/internal-transfer, hr/attestation, hr/overtime, hr/expenses

```
В предоставленной базе знаний нет вилок окладов по грейдам. Есть только правило: при переводе оклад определяется по грейду новой должности [hr/internal-transfer#0], но самих диапазонов нет. Уточните вопрос у HR.
```

### `it-runbook-allowed` — Что делает дежурный при инциденте и когда эскалирует?

- stratum: `fact`
- audience: `dept:it`
- escalated: True (expected False)
- escalation reason: no_sources (expected -)
- missing fragments: 15 минут
- forbidden fragments: -
- retrieved: it/incident-runbook, it/security, company/quality-ecology, hr/sick-leave-notification
- context: it/incident-runbook, it/security, company/quality-ecology, company/media-requests

```
Не нашёл ответа в базе знаний. Передал вопрос HR — ответят в течение рабочего дня.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `qc-defect-quarantine` — Что делают с браком на складе?

- stratum: `fact`
- audience: `all`
- escalated: False (expected False)
- escalation reason: answered (expected -)
- missing fragments: карантин
- forbidden fragments: -
- retrieved: production/quality-control, company/workspace-rules, it/email-quota, procurement/purchase-request, security/badge-access
- context: production/quality-control, company/quality-ecology, procurement/purchase-request, it/hardware-repair

```
Обнаруженный брак изолируется на складе несоответствующей продукции и маркируется красной биркой. Уничтожать или перерабатывать брак без акта службы качества запрещено [production/quality-control#0]. Итоговое решение по партии принимает служба качества [production/quality-control#0].
```

### `counterparty-check-term` — Сколько идёт проверка контрагента?

- stratum: `fact`
- audience: `all`
- escalated: False (expected False)
- escalation reason: answered (expected -)
- missing fragments: один рабочий день
- forbidden fragments: -
- retrieved: finance/counterparty-check, company/anti-corruption, procurement/supplier-onboarding, finance/invoice-processing, company/org-structure
- context: finance/counterparty-check, procurement/supplier-onboarding, company/anti-corruption, company/org-structure

```
Проверку контрагента служба безопасности проводит в течение пяти рабочих дней [procurement/supplier-onboarding#0].
```

### `production-safety-blocked` — Как часто проводят инструктаж по охране труда?

- stratum: `acl`
- audience: `dept:it`
- escalated: True (expected True)
- escalation reason: low_confidence (expected no_sources)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/security, hr/probation, hr/remote-work, hr/attestation, security/badge-access
- context: security/badge-access, hr/onboarding-first-day, hr/attestation, it/security, hr/remote-work

```
Не уверен, что понял вопрос правильно. Передал HR, чтобы вам ответил человек.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `dms-not-covered` — Что не покрывает полис ДМС?

- stratum: `fact`
- audience: `all`
- escalated: False (expected False)
- escalation reason: answered (expected -)
- missing fragments: косметология
- forbidden fragments: -
- retrieved: hr/benefits-dms, hr/expenses, hr/business-trip, company/org-structure
- context: hr/benefits-dms, hr/expenses, hr/sick-leave-notification, hr/benefits-meals

```
Полис ДМС не покрывает стоматологию сверх базовой программы, косметологию, вакцинацию для поездок и лечение за границей. Расширение программы возможно по желанию сотрудника и за его счёт. Если страховая отказала в оплате, письменное обоснование нужно передать в HR — разбор занимает до 15 рабочих дней [hr/benefits-dms#0].
```

### `dms-family` — Можно ли застраховать супруга по ДМС?

- stratum: `fact`
- audience: `all`
- escalated: False (expected False)
- escalation reason: answered (expected -)
- missing fragments: оплатой 50%
- forbidden fragments: -
- retrieved: hr/benefits-dms, company/org-structure, hr/expenses, company/anti-corruption
- context: hr/benefits-dms, hr/sick-leave-notification, hr/expenses, hr/sick-leave-pay

```
Да, супруг может быть подключён к программе ДМС на условиях страховой: 50% стоимости оплачивается из личных средств сотрудника. Сам полис ДМС распространяется только на сотрудника, поэтому родственники подключаются отдельно. Для уточнения условий подключения обратитесь в HR.
```

### `pricing-renewal-approval` — Нужно ли заново согласовывать скидку при продлении контракта?

- stratum: `fact`
- audience: `dept:sales`
- escalated: True (expected False)
- escalation reason: no_sources (expected -)
- missing fragments: продление
- forbidden fragments: -
- retrieved: sales/pricing-approval, sales/contract-approval, sales/kp-rules, procurement/purchase-request, finance/counterparty-check
- context: sales/pricing-approval, sales/contract-approval, sales/kp-rules, procurement/supplier-onboarding, procurement/purchase-request

```
Не нашёл ответа в базе знаний. Передал вопрос HR — ответят в течение рабочего дня.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `laptop-request-scrambled` — ноутбук получить как?

- stratum: `morphology`
- audience: `all`
- escalated: False (expected False)
- escalation reason: answered (expected -)
- missing fragments: заявк
- forbidden fragments: -
- retrieved: it/vpn-setup, it/access-and-equipment, it/hardware-repair, it/software-licenses, procurement/purchase-request
- context: it/access-and-equipment, hr/onboarding-first-day, it/hardware-repair, it/vpn-setup

```
Ноутбук выдаётся в первый рабочий день в офисе ИТ-поддержки. Для получения нужны пропуск и подтверждение от руководителя. Обратитесь в ИТ-поддержку в первый рабочий день с пропуском и подтверждением руководителя.
```

