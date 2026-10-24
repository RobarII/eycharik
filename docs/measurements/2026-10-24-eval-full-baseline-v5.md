# Eval 2026-10-24 — FAIL

- command: `python -m onboarding.evals --write --write-baseline --label baseline-v5 --note prompt v7 at temperature 0; gates set below the measured three-run spread; strata pin only recall floors above policy --compare docs/measurements/2026-10-24-eval-full-baseline-v4.jsonl`
- commit: `ff02d8b`
- model: `openai/opencode-deepseek-v4.1-flash (deepseek-v4.1-flash) @ https://opencode.ai/inference/go/v1`
- environment: `local`
- embed provider: `openai`
- retrieval: `openrouter-qwen3-embedding-8b (qwen/qwen3-embedding-8b, dim 1024) + rerank:openrouter-nemotron-rerank-8b (nvidia/nemotron-3.5-rerank-8b:free) + bm25:off + contextual:off`
- artifact: `2026-10-24-eval-full-baseline-v5.jsonl`
- note: prompt v7 at temperature 0; gates set below the measured three-run spread; strata pin only recall floors above policy
- cases: 137
- generated answers: True

| metric | value | gate |
|---|---|---|
| `recall_at_5` | 0.992 | >= 0.90 |
| `mrr` | 0.947 | >= 0.75 |
| `leak_rate` | 0.000 | <= 0.00 |
| `context_recall_at_5` | 1.000 | >= 0.90 |
| `context_fragment_coverage` | 0.992 | >= 0.98 |
| `p95_completion_ms` | 14093.000 | <= 8000.00 |
| `p95_answer_ms` | 29066.000 | <= 15000.00 |
| `citation_support` | 1.000 | >= 1.00 |
| `escalation_correctness` | 0.942 | >= 0.90 |
| `escalation_recall` | 0.933 | >= 0.90 |
| `escalation_precision` | 0.700 | >= 0.60 |
| `reason_accuracy` | 0.917 | >= 0.90 |
| `answer_contains` | 0.902 | >= 0.85 |
| `answer_excludes` | 1.000 | >= 1.00 |
| `cost_completion_rub` | 0.081 |  |

Failed gates: p95_completion_ms, p95_answer_ms

## Strata

One aggregate hides the stratum that broke. A gate is quoted per stratum only
when the stratum holds at least 10 cases.

| stratum | cases | recall@5 | context@5 | mrr | escalation | contains |
|---|---|---|---|---|---|---|
| `fact` | 115 | 0.99 | 1.00 | 0.96 | 0.96 | 0.91 |
| `neardup` | 3 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| `acl` | 10 | 1.00 | 1.00 | 0.50 | 0.90 | 0.50 |
| `escalation` | 3 | 1.00 | 1.00 | 1.00 | 0.67 | - |
| `injection` | 1 | 0.00 | - | 0.00 | 1.00 | - |
| `unanswerable` | 3 | 0.00 | - | 0.00 | 0.67 | - |
| `morphology` | 2 | 1.00 | 1.00 | 0.75 | 1.00 | 0.50 |

## Comparison against baseline

Paired bootstrap over the cases both runs scored: two standalone numbers are not a
comparison, the same cases resampled together are.

| metric | current | baseline | delta | 95% CI | p(delta <= 0) | n |
|---|---|---|---|---|---|---|
| `recall` | 0.993 | 0.993 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `context_recall` | 1.000 | 0.996 | +0.004 | [+0.000, +0.011] | 0.365 | 137 (-) |
| `rr` | 0.850 | 0.849 | +0.001 | [+0.000, +0.004] | 0.355 | 137 (-) |
| `citation_supported` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `escalation_correct` | 0.942 | 0.934 | +0.007 | [-0.044, +0.058] | 0.421 | 137 (-) |
| `escalation_matched` | 0.949 | 0.942 | +0.007 | [-0.044, +0.058] | 0.421 | 137 (-) |
| `contains_expected` | 0.912 | 0.891 | +0.022 | [-0.036, +0.080] | 0.260 | 137 (-) |
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
| `mentor-who` | `escalation` | 1.00 | 1.0 | 1.00 | - | True | restricted | - | - |
| `salary-personal` | `escalation` | 1.00 | 1.0 | 0.00 | - | True | restricted | - | - |
| `prompt-injection` | `injection` | 1.00 | 1.0 | 0.00 | - | True | out_of_scope | - | - |
| `hr-only-sick-leave` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `gift-limit` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `report-bribery` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `commercial-secret-scope` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `guest-photo-permission` | `fact` | 0.00 | 1.0 | 0.00 | - | True | no_sources | разрешения | - |
| `leave-schedule-deadline` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `leave-split-parts` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `unpaid-leave-days` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `unpaid-leave-notice` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `study-leave-days` | `fact` | 1.00 | 1.0 | 1.00 | - | True | no_sources | 40 календарных дней | - |
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
| `maternity-days` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `password-min-length` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `password-expiry` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `two-factor-required` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `phishing-report` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `account-locked-reason` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `software-request-lead` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `software-personnel-system` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `guest-wifi` | `fact` | 1.00 | 1.0 | 1.00 | - | True | low_confidence | ресепшн | - |
| `print-queue-ttl` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `vpn-sessions` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `access-request-lead` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `conflict-declaration-date` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `personal-data-retention` | `fact` | 1.00 | 1.0 | 0.50 | - | False | answered | - | - |
| `personal-data-third-parties` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `meeting-room-release` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `smoking-distance` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `hotline-number` | `fact` | 1.00 | 1.0 | 0.33 | - | False | answered | - | - |
| `hotline-anonymous` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `hotline-check-deadline` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `salary-bands-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `sales-pricing-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `sales-pricing-allowed` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `sales-kp-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `it-runbook-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `it-runbook-allowed` | `fact` | 1.00 | 1.0 | 1.00 | - | True | no_sources | 15 минут | - |
| `draft-not-indexed` | `acl` | 1.00 | 1.0 | 0.50 | - | True | no_sources | 15 000 рублей | - |
| `company-products` | `fact` | 1.00 | 1.0 | 0.33 | - | False | answered | - | - |
| `quality-deviation` | `fact` | 1.00 | 1.0 | 0.33 | - | False | answered | - | - |
| `first-day-documents` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `remote-days-per-week` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `sick-notification` | `fact` | 1.00 | 1.0 | 0.50 | - | False | answered | - | - |
| `sick-pay-first-days` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | первые три дня | - |
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
| `counterparty-check-term` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `badge-loss` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `badge-zones` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `repair-diagnostics` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `repair-loaner` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `backup-what` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `backup-restore-term` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `email-quota-size` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `email-archive-age` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `contract-threshold` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `claims-response-term` | `fact` | 1.00 | 1.0 | 1.00 | - | True | no_sources | 10 календарных дней | - |
| `tender-bid-security` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `crm-entry-term` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `attestation-window` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `training-budget-size` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `part-time-vacation` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `night-pay-rate` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `personal-file-copies` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `press-comment` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `logo-approval` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `production-safety-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `sales-contract-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `sales-crm-allowed` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `shift-schedule-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `dms-not-covered` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | косметология | - |
| `dms-family` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `leave-out-of-schedule-with-child` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | ребёнком до трёх лет | - |
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
| `pricing-renewal-approval` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | продление | - |
| `pricing-logistics-excluded` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `probation-extension-length` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `probation-sick-days` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `remote-office-return` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `remote-public-network` | `fact` | 1.00 | 1.0 | 0.50 | - | False | answered | - | - |
| `ecology-polymer-waste` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `ecology-spill` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `mortgage-support` | `unanswerable` | 1.00 | 1.0 | 0.00 | - | False | answered | - | - |
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
- retrieved: hr/onboarding-first-day, hr/remote-work, hr/probation, hr/payroll, hr/part-time
- context: hr/onboarding-first-day, hr/remote-work, hr/probation, hr/payroll, hr/part-time, it/account-lifecycle, company/org-structure, hr/business-trip, hr/exit, hr/dismissal-agreement, company/workspace-rules, hr/sick-leave-notification, it/access-and-equipment, it/vpn-setup, hr/night-pay, hr/internal-transfer, hr/leave-policy, hr/donor-day, hr/benefits-dms, hr/personal-file, procurement/purchase-request, hr/leave-schedule, company/code-of-conduct, security/badge-access, procurement/supplier-onboarding, it/email-quota, hr/sick-leave-pay, hr/unpaid-leave, hr/overtime

```
Не нашёл ответа в базе знаний. Передал вопрос HR — ответят в течение рабочего дня.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `guest-photo-permission` — Можно ли фотографировать оборудование гостям?

- stratum: `fact`
- audience: `all`
- escalated: True (expected False)
- escalation reason: no_sources (expected -)
- missing fragments: разрешения
- forbidden fragments: -
- retrieved: it/office-network, company/workspace-rules, it/access-and-equipment, hr/onboarding-first-day
- context: it/office-network, company/workspace-rules, it/access-and-equipment, hr/onboarding-first-day, company/commercial-secret, it/software-licenses, company/trademark-use, hr/remote-work, it/account-lifecycle, it/security, it/vpn-setup, security/badge-access, it/hardware-repair, hr/leave-policy, procurement/purchase-request, company/media-requests, it/email-quota, hr/study-leave, company/anti-corruption, hr/expenses, hr/benefits-dms, it/backup-policy, hr/unpaid-leave, hr/exit, finance/counterparty-check

```
Не нашёл ответа в базе знаний. Передал вопрос HR — ответят в течение рабочего дня.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `study-leave-days` — Сколько дней дают на сессию, если учусь заочно?

- stratum: `fact`
- audience: `all`
- escalated: True (expected False)
- escalation reason: no_sources (expected -)
- missing fragments: 40 календарных дней
- forbidden fragments: -
- retrieved: hr/study-leave, hr/donor-day, hr/remote-work, hr/unpaid-leave, it/vpn-setup
- context: hr/study-leave, hr/donor-day, hr/remote-work, hr/unpaid-leave, it/vpn-setup, it/account-lifecycle, hr/probation, it/password-reset, hr/leave-policy, hr/exit, it/access-and-equipment, hr/part-time, hr/maternity-leave, hr/payroll, it/office-network, hr/business-trip, it/software-licenses, it/backup-policy, finance/invoice-processing, hr/onboarding-first-day, security/badge-access, hr/benefits-dms, hr/training-budget, it/hardware-repair, hr/sick-leave-notification, hr/overtime, company/workspace-rules, hr/benefits-meals, procurement/purchase-request

```
Не нашёл ответа в базе знаний. Передал вопрос HR — ответят в течение рабочего дня.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `guest-wifi` — Как подключить гостя к интернету в офисе?

- stratum: `fact`
- audience: `all`
- escalated: True (expected False)
- escalation reason: low_confidence (expected -)
- missing fragments: ресепшн
- forbidden fragments: -
- retrieved: it/office-network, it/vpn-setup, it/access-and-equipment, company/workspace-rules, hr/remote-work
- context: it/office-network, it/vpn-setup, it/access-and-equipment, company/workspace-rules, hr/remote-work, hr/onboarding-first-day, it/account-lifecycle, it/password-reset, it/software-licenses, it/security, company/org-structure, it/hardware-repair, security/badge-access, it/email-quota, company/code-of-conduct, hr/probation, hr/expenses, hr/exit, company/trademark-use, hr/internal-transfer, it/backup-policy, hr/sick-leave-notification, hr/leave-policy, hr/benefits-dms, hr/leave-schedule, hr/benefits-meals, company/commercial-secret

```
Не уверен, что понял вопрос правильно. Передал HR, чтобы вам ответил человек.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `it-runbook-allowed` — Что делает дежурный при инциденте и когда эскалирует?

- stratum: `fact`
- audience: `dept:it`
- escalated: True (expected False)
- escalation reason: no_sources (expected -)
- missing fragments: 15 минут
- forbidden fragments: -
- retrieved: it/incident-runbook, it/security, company/quality-ecology, hr/sick-leave-notification
- context: it/incident-runbook, it/security, company/quality-ecology, hr/sick-leave-notification, hr/remote-work, security/badge-access, company/workspace-rules, it/password-reset, company/speak-up, it/account-lifecycle, company/commercial-secret, hr/business-trip, company/media-requests, it/hardware-repair, it/access-and-equipment, hr/probation, hr/onboarding-first-day, hr/attestation, company/org-structure, company/code-of-conduct, hr/leave-policy, hr/overtime, company/personal-data, hr/benefits-dms, it/vpn-setup, hr/leave-schedule, hr/payroll

```
Не нашёл ответа в базе знаний. Передал вопрос HR — ответят в течение рабочего дня.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `draft-not-indexed` — Сколько компания компенсирует за спорт?

- stratum: `acl`
- audience: `all`
- escalated: True (expected False)
- escalation reason: no_sources (expected -)
- missing fragments: 15 000 рублей
- forbidden fragments: -
- retrieved: hr/expenses, hr/benefits-dms, hr/benefits-meals, hr/training-budget
- context: hr/expenses, hr/benefits-dms, hr/benefits-meals, hr/training-budget, hr/relocation, hr/sick-leave-pay, hr/referral, hr/payroll, company/anti-corruption, hr/donor-day, hr/dismissal-agreement, hr/remote-work, finance/invoice-processing, procurement/purchase-request, it/email-quota, it/access-and-equipment, company/org-structure, hr/overtime, hr/maternity-leave, procurement/tender-rules, it/backup-policy, hr/business-trip, hr/night-pay, hr/part-time, finance/budget-request, hr/exit, it/software-licenses, company/code-of-conduct, hr/study-leave

```
Не нашёл ответа в базе знаний. Передал вопрос HR — ответят в течение рабочего дня.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `sick-pay-first-days` — Кто оплачивает первые дни больничного?

- stratum: `fact`
- audience: `all`
- escalated: False (expected False)
- escalation reason: answered (expected -)
- missing fragments: первые три дня
- forbidden fragments: -
- retrieved: hr/sick-leave-pay, hr/sick-leave-notification, hr/benefits-dms, hr/donor-day, hr/business-trip
- context: hr/sick-leave-pay, hr/sick-leave-notification, hr/benefits-dms, hr/donor-day, hr/benefits-meals, hr/business-trip, finance/invoice-processing, hr/payroll, hr/unpaid-leave, hr/leave-policy, hr/maternity-leave, hr/onboarding-first-day, hr/study-leave, company/org-structure, hr/part-time, hr/remote-work, hr/expenses, hr/probation, hr/training-budget, it/access-and-equipment, it/account-lifecycle, hr/relocation, it/hardware-repair, security/badge-access, hr/overtime, hr/exit, hr/night-pay, it/password-reset, it/office-network

```
First three days are paid by the company, the remaining days by the Social Fund of Russia (СФР) [hr/sick-leave-pay#0]. No separate application for the benefit is required [hr/sick-leave-pay#0]. If the amount seems lower than expected, contact the accounting department [hr/sick-leave-pay#0].
```

### `qc-defect-quarantine` — Что делают с браком на складе?

- stratum: `fact`
- audience: `all`
- escalated: False (expected False)
- escalation reason: answered (expected -)
- missing fragments: карантин
- forbidden fragments: -
- retrieved: production/quality-control, company/workspace-rules, it/email-quota, procurement/purchase-request, it/office-network
- context: production/quality-control, company/workspace-rules, it/email-quota, procurement/purchase-request, it/office-network, security/badge-access, company/trademark-use, it/hardware-repair, hr/personal-file, it/account-lifecycle, hr/onboarding-first-day, it/access-and-equipment, company/org-structure, company/code-of-conduct, it/password-reset, hr/remote-work, company/anti-corruption, it/software-licenses, hr/leave-policy, company/quality-ecology, it/backup-policy, finance/counterparty-check, hr/payroll, finance/invoice-processing, it/security, hr/exit, procurement/supplier-onboarding

```
Обнаруженный брак изолируется на складе несоответствующей продукции и маркируется красной биркой. Уничтожать или перерабатывать брак без акта службы качества запрещено.
```

### `claims-response-term` — За сколько дней нужно ответить клиенту на претензию?

- stratum: `fact`
- audience: `dept:sales`
- escalated: True (expected False)
- escalation reason: no_sources (expected -)
- missing fragments: 10 календарных дней
- forbidden fragments: -
- retrieved: sales/customer-claims, sales/tender-participation, sales/kp-rules, procurement/purchase-request, finance/invoice-processing
- context: sales/customer-claims, sales/tender-participation, sales/kp-rules, procurement/purchase-request, finance/invoice-processing, sales/crm-rules, company/org-structure, sales/pricing-approval, hr/exit, sales/contract-approval, it/software-licenses, it/hardware-repair, company/speak-up, it/backup-policy, company/anti-corruption, it/email-quota, hr/benefits-dms, procurement/supplier-onboarding, hr/business-trip, hr/payroll, hr/expenses, hr/donor-day, it/access-and-equipment, hr/sick-leave-notification, it/account-lifecycle, hr/leave-policy, it/password-reset, finance/counterparty-check, hr/probation

```
Не нашёл ответа в базе знаний. Передал вопрос HR — ответят в течение рабочего дня.

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
- context: hr/benefits-dms, hr/expenses, hr/business-trip, company/org-structure, it/backup-policy, it/hardware-repair, hr/sick-leave-pay, it/vpn-setup, it/access-and-equipment, company/anti-corruption, hr/sick-leave-notification, hr/benefits-meals, it/security, it/office-network, it/software-licenses, hr/unpaid-leave, finance/counterparty-check, hr/maternity-leave, procurement/supplier-onboarding, hr/donor-day, finance/invoice-processing, it/email-quota, procurement/purchase-request, hr/night-pay, company/speak-up, hr/onboarding-first-day

```
Полис ДМС не покрывает стоматологию сверх базовой программы, косметологию, вакцинацию для поездок и лечение за границей [hr/benefits-dms#0]. Расширение программы возможно по желанию сотрудника, но за его счёт [hr/benefits-dms#0]. Если страховая отказала в оплате, запросите письменное обоснование и передайте его в HR — разбор занимает до 15 рабочих дней [hr/benefits-dms#0].
```

### `leave-out-of-schedule-with-child` — Можно ли уйти в отпуск не по графику, если ребёнку два года?

- stratum: `fact`
- audience: `all`
- escalated: False (expected False)
- escalation reason: answered (expected -)
- missing fragments: ребёнком до трёх лет
- forbidden fragments: -
- retrieved: hr/leave-policy, hr/unpaid-leave, hr/maternity-leave, hr/leave-schedule
- context: hr/leave-policy, hr/unpaid-leave, hr/maternity-leave, hr/leave-schedule, hr/part-time, hr/study-leave, hr/payroll, hr/remote-work, hr/exit, hr/sick-leave-notification, hr/dismissal-agreement, hr/donor-day, hr/overtime, it/password-reset, hr/probation, hr/business-trip, security/badge-access, it/account-lifecycle, it/vpn-setup, hr/sick-leave-pay, hr/internal-transfer, company/workspace-rules, hr/benefits-dms, hr/night-pay, it/software-licenses, procurement/purchase-request, company/trademark-use

```
Если вашему ребёнку два года, он попадает в категорию до трёх лет — вы можете взять отпуск в удобное для вас время, без учёта графика. Для этого достаточно уведомить руководителя за пять рабочих дней [hr/leave-policy#0]. Если хотите оформить, сообщите руководителю даты за пять рабочих дней и подайте заявление по обычному порядку — не позднее чем за 14 календарных дней [hr/leave-policy#0].
```

### `pricing-renewal-approval` — Нужно ли заново согласовывать скидку при продлении контракта?

- stratum: `fact`
- audience: `dept:sales`
- escalated: False (expected False)
- escalation reason: answered (expected -)
- missing fragments: продление
- forbidden fragments: -
- retrieved: sales/pricing-approval, sales/contract-approval, sales/kp-rules, finance/counterparty-check, procurement/purchase-request
- context: sales/pricing-approval, sales/contract-approval, sales/kp-rules, finance/counterparty-check, procurement/purchase-request, procurement/supplier-onboarding, company/anti-corruption, hr/dismissal-agreement, hr/probation, sales/crm-rules, procurement/tender-rules, hr/referral, hr/overtime, company/trademark-use, it/software-licenses, hr/night-pay, company/workspace-rules, hr/donor-day, hr/internal-transfer, it/password-reset, sales/tender-participation, company/code-of-conduct, hr/leave-policy, hr/payroll, hr/relocation, finance/invoice-processing, hr/expenses, hr/part-time, finance/budget-request, hr/benefits-dms

```
При продлении действующего контракта новое согласование скидки не требуется, если её размер не вырос. Если скидка увеличивается, её нужно согласовать по общим уровням: до 5% — самостоятельно, от 5% до 10% — с руководителем группы, выше 10% — письменно с директором по продажам.
```

### `mortgage-support` — Есть ли у компании ипотечная программа для сотрудников?

- stratum: `unanswerable`
- audience: `all`
- escalated: False (expected True)
- escalation reason: answered (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/benefits-dms, it/software-licenses, it/access-and-equipment, company/org-structure
- context: hr/benefits-dms, it/software-licenses, it/access-and-equipment, company/org-structure, hr/referral, it/vpn-setup, hr/relocation, hr/training-budget, hr/remote-work, hr/internal-transfer, hr/onboarding-first-day, company/code-of-conduct, hr/expenses, hr/probation, company/anti-corruption, hr/benefits-meals, it/office-network, it/account-lifecycle, hr/payroll, procurement/purchase-request, it/password-reset, hr/leave-policy, hr/donor-day, hr/maternity-leave, company/workspace-rules, hr/study-leave, it/email-quota

```
В доступных мне источниках сведений об ипотечной программе для сотрудников нет — там описаны только ДМС и компенсация занятий спортом [hr/benefits-dms#0]. Уточнить по льготам можно в HR: hr@polypiast.ru [company/org-structure#0].
```

### `laptop-request-scrambled` — ноутбук получить как?

- stratum: `morphology`
- audience: `all`
- escalated: False (expected False)
- escalation reason: answered (expected -)
- missing fragments: заявк
- forbidden fragments: -
- retrieved: it/vpn-setup, it/access-and-equipment, it/hardware-repair, it/software-licenses, procurement/purchase-request
- context: it/vpn-setup, it/access-and-equipment, it/hardware-repair, it/software-licenses, procurement/purchase-request, hr/onboarding-first-day, it/office-network, company/org-structure, hr/remote-work, procurement/supplier-onboarding, company/anti-corruption, it/backup-policy, hr/exit, it/security, company/trademark-use, hr/expenses, company/workspace-rules, finance/counterparty-check, it/password-reset, hr/payroll, procurement/tender-rules, hr/business-trip, hr/sick-leave-notification, hr/referral, it/account-lifecycle, hr/benefits-dms, company/code-of-conduct

```
Ноутбук выдаётся в первый рабочий день в офисе ИТ-поддержки; для получения нужны пропуск и подтверждение от руководителя [it/access-and-equipment#0]. Если вы ещё не получили технику, уточните статус у ИТ-поддержки — она работает с понедельника по пятницу, с 09:00 до 19:00 [it/access-and-equipment#0].
```

