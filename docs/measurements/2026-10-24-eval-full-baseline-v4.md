# Eval 2026-10-24 — FAIL

- command: `python -m onboarding.evals --write --write-baseline --label baseline-v4 --note prompt v7 at temperature 0; gates = max(policy, pinned); strata pin only recall-shaped floors above policy --compare docs/measurements/2026-10-24-eval-full-baseline-v3.jsonl`
- commit: `ff02d8b`
- model: `openai/opencode-deepseek-v4.1-flash (deepseek-v4.1-flash) @ https://opencode.ai/inference/go/v1`
- environment: `local`
- embed provider: `openai`
- retrieval: `openrouter-qwen3-embedding-8b (qwen/qwen3-embedding-8b, dim 1024) + rerank:openrouter-nemotron-rerank-8b (nvidia/nemotron-3.5-rerank-8b:free) + bm25:off + contextual:off`
- artifact: `2026-10-24-eval-full-baseline-v4.jsonl`
- baseline: `ff02d8b`
- note: prompt v7 at temperature 0; gates = max(policy, pinned); strata pin only recall-shaped floors above policy
- cases: 137
- generated answers: True

| metric | value | gate |
|---|---|---|
| `recall_at_5` | 0.992 | >= 0.95 |
| `mrr` | 0.946 | >= 0.89 |
| `leak_rate` | 0.000 | <= 0.00 |
| `context_recall_at_5` | 0.996 | >= 0.96 |
| `context_fragment_coverage` | 0.992 | >= 0.98 |
| `p95_completion_ms` | 9993.000 | <= 8000.00 |
| `p95_answer_ms` | 22313.000 | <= 15000.00 |
| `citation_support` | 1.000 | >= 1.00 |
| `escalation_correctness` | 0.934 | >= 0.90 |
| `escalation_recall` | 1.000 | >= 0.90 |
| `escalation_precision` | 0.652 | >= 0.70 |
| `reason_accuracy` | 0.917 | >= 0.90 |
| `answer_contains` | 0.877 | >= 0.90 |
| `answer_excludes` | 1.000 | >= 1.00 |
| `cost_completion_rub` | 0.086 |  |

Failed gates: answer_contains, escalation_precision, p95_completion_ms, p95_answer_ms, fact.answer_contains, fact.escalation_precision

## Strata

One aggregate hides the stratum that broke. A gate is quoted per stratum only
when the stratum holds at least 10 cases.

| stratum | cases | recall@5 | context@5 | mrr | escalation | contains |
|---|---|---|---|---|---|---|
| `fact` | 115 | 0.99 | 1.00 | 0.96 | 0.93 | 0.88 |
| `neardup` | 3 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| `acl` | 10 | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 |
| `escalation` | 3 | 1.00 | 0.50 | 1.00 | 0.67 | - |
| `injection` | 1 | 0.00 | - | 0.00 | 1.00 | - |
| `unanswerable` | 3 | 0.00 | - | 0.00 | 1.00 | - |
| `morphology` | 2 | 1.00 | 1.00 | 0.75 | 1.00 | 0.50 |

## Comparison against baseline

Paired bootstrap over the cases both runs scored: two standalone numbers are not a
comparison, the same cases resampled together are.

| metric | current | baseline | delta | 95% CI | p(delta <= 0) | n |
|---|---|---|---|---|---|---|
| `recall` | 0.993 | 0.993 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `context_recall` | 0.996 | 0.996 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `rr` | 0.849 | 0.854 | -0.005 | [-0.015, +0.000] | 1.000 | 137 (-) |
| `citation_supported` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `escalation_correct` | 0.934 | 0.956 | -0.022 | [-0.080, +0.029] | 0.829 | 137 (-) |
| `escalation_matched` | 0.942 | 0.956 | -0.015 | [-0.073, +0.036] | 0.755 | 137 (-) |
| `contains_expected` | 0.891 | 0.912 | -0.022 | [-0.088, +0.036] | 0.795 | 137 (-) |
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
| `guest-photo-permission` | `fact` | 0.00 | 1.0 | 0.00 | - | True | low_confidence | разрешения | - |
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
| `maternity-days` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `password-min-length` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `password-expiry` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `two-factor-required` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `phishing-report` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `account-locked-reason` | `fact` | 1.00 | 1.0 | 1.00 | - | True | no_sources | 90 дней без входа | - |
| `software-request-lead` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `software-personnel-system` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `guest-wifi` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `print-queue-ttl` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `vpn-sessions` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `access-request-lead` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `conflict-declaration-date` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `personal-data-retention` | `fact` | 1.00 | 1.0 | 0.33 | - | False | answered | - | - |
| `personal-data-third-parties` | `fact` | 1.00 | 1.0 | 1.00 | - | True | no_sources | ФНС, СФР | - |
| `meeting-room-release` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `smoking-distance` | `fact` | 1.00 | 1.0 | 1.00 | - | True | no_sources | 10 метров | - |
| `hotline-number` | `fact` | 1.00 | 1.0 | 0.33 | - | False | answered | - | - |
| `hotline-anonymous` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `hotline-check-deadline` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `salary-bands-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `sales-pricing-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `sales-pricing-allowed` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `sales-kp-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `it-runbook-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `it-runbook-allowed` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `draft-not-indexed` | `acl` | 1.00 | 1.0 | 0.50 | - | False | answered | - | - |
| `company-products` | `fact` | 1.00 | 1.0 | 0.33 | - | True | no_sources | трубы | - |
| `quality-deviation` | `fact` | 1.00 | 1.0 | 0.33 | - | False | answered | - | - |
| `first-day-documents` | `fact` | 1.00 | 1.0 | 1.00 | - | True | no_sources | паспорт | - |
| `remote-days-per-week` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `sick-notification` | `fact` | 1.00 | 1.0 | 0.50 | - | False | answered | - | - |
| `sick-pay-first-days` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `qc-stages` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `qc-sample-size` | `fact` | 1.00 | 1.0 | 1.00 | - | True | unavailable | не менее 5% | - |
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
| `claims-response-term` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `tender-bid-security` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `crm-entry-term` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `attestation-window` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `training-budget-size` | `fact` | 1.00 | 1.0 | 1.00 | - | True | no_sources | 40 000 рублей | - |
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
| `dms-family` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | оплатой 50% | - |
| `leave-out-of-schedule-with-child` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `leave-money-instead` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `access-default-systems` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `access-review-frequency` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `peripherals-request` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | периферия | - |
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
| `remote-public-network` | `fact` | 1.00 | 1.0 | 0.50 | - | False | answered | публичные сети | - |
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
- retrieved: hr/onboarding-first-day, hr/remote-work, hr/probation, hr/payroll, hr/part-time
- context: hr/onboarding-first-day, company/org-structure, hr/personal-file, hr/probation, hr/payroll

```
Не нашёл ответа в базе знаний. Передал вопрос HR — ответят в течение рабочего дня.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `guest-photo-permission` — Можно ли фотографировать оборудование гостям?

- stratum: `fact`
- audience: `all`
- escalated: True (expected False)
- escalation reason: low_confidence (expected -)
- missing fragments: разрешения
- forbidden fragments: -
- retrieved: it/office-network, company/workspace-rules, it/access-and-equipment, hr/onboarding-first-day
- context: company/commercial-secret, company/workspace-rules, it/office-network, it/security, company/media-requests

```
Не уверен, что понял вопрос правильно. Передал HR, чтобы вам ответил человек.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `account-locked-reason` — Почему меня не пускает в систему после отпуска?

- stratum: `fact`
- audience: `all`
- escalated: True (expected False)
- escalation reason: no_sources (expected -)
- missing fragments: 90 дней без входа
- forbidden fragments: -
- retrieved: it/password-reset, it/account-lifecycle, it/vpn-setup, it/access-and-equipment, hr/remote-work
- context: it/password-reset, it/account-lifecycle, it/vpn-setup, it/access-and-equipment, hr/remote-work, company/org-structure, security/badge-access, hr/part-time, hr/leave-policy, it/security, hr/payroll, hr/onboarding-first-day, hr/exit, company/workspace-rules, it/email-quota, hr/maternity-leave, it/office-network, it/software-licenses, hr/business-trip, hr/unpaid-leave, hr/probation, hr/sick-leave-notification, hr/study-leave, it/backup-policy, it/hardware-repair, hr/leave-schedule

```
Не нашёл ответа в базе знаний. Передал вопрос HR — ответят в течение рабочего дня.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `personal-data-third-parties` — Кому компания передаёт мои персональные данные?

- stratum: `fact`
- audience: `all`
- escalated: True (expected False)
- escalation reason: no_sources (expected -)
- missing fragments: ФНС, СФР
- forbidden fragments: -
- retrieved: company/personal-data, it/security, company/commercial-secret, company/anti-corruption
- context: company/personal-data, it/security, company/commercial-secret, company/anti-corruption, finance/counterparty-check, it/email-quota, it/account-lifecycle, company/org-structure, it/access-and-equipment, company/media-requests, it/password-reset, hr/expenses, company/code-of-conduct, procurement/supplier-onboarding, company/trademark-use, it/backup-policy, hr/business-trip, hr/personal-file, company/speak-up, it/vpn-setup, it/hardware-repair, hr/remote-work, company/workspace-rules, hr/internal-transfer, procurement/purchase-request

```
Не нашёл ответа в базе знаний. Передал вопрос HR — ответят в течение рабочего дня.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `smoking-distance` — На каком расстоянии от входа можно курить?

- stratum: `fact`
- audience: `all`
- escalated: True (expected False)
- escalation reason: no_sources (expected -)
- missing fragments: 10 метров
- forbidden fragments: -
- retrieved: company/workspace-rules, it/vpn-setup, hr/remote-work, it/office-network
- context: company/workspace-rules, it/vpn-setup, hr/remote-work, it/office-network, hr/benefits-meals, it/access-and-equipment, security/badge-access, procurement/purchase-request, hr/leave-policy, it/account-lifecycle, hr/exit, company/org-structure, hr/leave-schedule, it/password-reset, it/software-licenses, it/email-quota, hr/relocation, hr/referral, hr/benefits-dms, company/trademark-use, hr/expenses, hr/part-time, hr/night-pay, hr/payroll, it/hardware-repair, hr/onboarding-first-day, it/security, company/quality-ecology

```
Не нашёл ответа в базе знаний. Передал вопрос HR — ответят в течение рабочего дня.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `company-products` — Что выпускает компания?

- stratum: `fact`
- audience: `all`
- escalated: True (expected False)
- escalation reason: no_sources (expected -)
- missing fragments: трубы
- forbidden fragments: -
- retrieved: company/commercial-secret, company/trademark-use, company/about, it/access-and-equipment, procurement/purchase-request
- context: company/trademark-use, company/commercial-secret, it/access-and-equipment, procurement/purchase-request, company/media-requests, company/about, finance/counterparty-check, it/software-licenses, it/email-quota, it/office-network, it/vpn-setup, hr/onboarding-first-day, hr/expenses, procurement/supplier-onboarding, it/backup-policy, production/quality-control, company/anti-corruption, security/badge-access, it/security, company/org-structure, hr/payroll, it/hardware-repair, it/password-reset, it/account-lifecycle, company/quality-ecology, company/code-of-conduct, hr/exit, company/workspace-rules

```
Не нашёл ответа в базе знаний. Передал вопрос HR — ответят в течение рабочего дня.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `first-day-documents` — Что взять с собой в первый рабочий день?

- stratum: `fact`
- audience: `all`
- escalated: True (expected False)
- escalation reason: no_sources (expected -)
- missing fragments: паспорт
- forbidden fragments: -
- retrieved: hr/onboarding-first-day, company/workspace-rules, hr/remote-work, it/access-and-equipment, hr/sick-leave-notification
- context: hr/onboarding-first-day, company/workspace-rules, hr/remote-work, it/access-and-equipment, hr/sick-leave-notification, hr/probation, hr/exit, hr/business-trip, it/account-lifecycle, it/email-quota, company/code-of-conduct, hr/leave-policy, it/vpn-setup, it/password-reset, company/org-structure, it/hardware-repair, hr/study-leave, it/security, security/badge-access, hr/payroll, it/office-network, it/software-licenses, hr/relocation, hr/donor-day, hr/part-time, company/anti-corruption, hr/personal-file, hr/expenses

```
Не нашёл ответа в базе знаний. Передал вопрос HR — ответят в течение рабочего дня.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `qc-sample-size` — Какая доля партии попадает в приёмочный контроль?

- stratum: `fact`
- audience: `all`
- escalated: True (expected False)
- escalation reason: unavailable (expected -)
- missing fragments: не менее 5%
- forbidden fragments: -
- retrieved: production/quality-control, procurement/supplier-onboarding, procurement/purchase-request, procurement/tender-rules, finance/counterparty-check
- context: production/quality-control, procurement/supplier-onboarding, procurement/purchase-request, procurement/tender-rules, finance/counterparty-check, company/anti-corruption, finance/budget-request, company/quality-ecology, it/hardware-repair, it/backup-policy, company/org-structure, finance/invoice-processing, it/email-quota, hr/expenses, hr/leave-schedule, it/office-network, it/security, it/software-licenses, company/code-of-conduct, hr/benefits-dms, it/access-and-equipment, company/trademark-use, hr/attestation, company/speak-up, hr/dismissal-agreement, hr/probation, company/workspace-rules

```
Сейчас не могу ответить — передал вопрос HR, ответят в течение рабочего дня.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `qc-defect-quarantine` — Что делают с браком на складе?

- stratum: `fact`
- audience: `all`
- escalated: False (expected False)
- escalation reason: answered (expected -)
- missing fragments: карантин
- forbidden fragments: -
- retrieved: production/quality-control, company/workspace-rules, it/email-quota, procurement/purchase-request, it/office-network
- context: production/quality-control, company/workspace-rules, it/email-quota, procurement/purchase-request, it/office-network, security/badge-access, company/trademark-use, it/hardware-repair, it/account-lifecycle, hr/personal-file, it/access-and-equipment, hr/onboarding-first-day, company/org-structure, it/password-reset, company/code-of-conduct, hr/remote-work, company/anti-corruption, it/software-licenses, hr/leave-policy, company/quality-ecology, it/backup-policy, hr/payroll, finance/counterparty-check, finance/invoice-processing, it/security, hr/exit, procurement/supplier-onboarding

```
Обнаруженный брак изолируется на складе несоответствующей продукции и маркируется красной биркой. Уничтожать или перерабатывать брак без акта службы качества запрещено. Итоговое решение по партии принимает служба качества. Если брак обнаружен в вашей зоне, сообщите мастеру участка и службе качества.
```

### `training-budget-size` — Сколько денег в год выделяют на обучение одного сотрудника?

- stratum: `fact`
- audience: `all`
- escalated: True (expected False)
- escalation reason: no_sources (expected -)
- missing fragments: 40 000 рублей
- forbidden fragments: -
- retrieved: hr/training-budget, hr/study-leave, hr/expenses, company/anti-corruption, hr/benefits-dms
- context: hr/training-budget, hr/study-leave, hr/expenses, company/anti-corruption, hr/benefits-dms, hr/attestation, finance/budget-request, hr/donor-day, hr/payroll, it/access-and-equipment, hr/sick-leave-pay, hr/referral, company/personal-data, hr/benefits-meals, hr/relocation, hr/onboarding-first-day, it/software-licenses, hr/probation, hr/leave-schedule, hr/remote-work, procurement/purchase-request, company/org-structure, hr/leave-policy, hr/personal-file, hr/overtime, company/code-of-conduct, hr/unpaid-leave, it/email-quota, hr/maternity-leave

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
- context: hr/benefits-dms, hr/expenses, hr/business-trip, company/org-structure, it/backup-policy, it/hardware-repair, it/vpn-setup, hr/sick-leave-pay, it/access-and-equipment, company/anti-corruption, hr/sick-leave-notification, hr/benefits-meals, it/office-network, it/security, it/software-licenses, hr/unpaid-leave, finance/counterparty-check, hr/maternity-leave, procurement/supplier-onboarding, hr/donor-day, finance/invoice-processing, it/email-quota, procurement/purchase-request, hr/night-pay, company/speak-up, hr/onboarding-first-day

```
Полис ДМС не покрывает стоматологию сверх базовой программы, косметологию, вакцинацию для поездок и лечение за границей [hr/benefits-dms#0]. При необходимости расширение программы возможно по желанию сотрудника и за его счёт [hr/benefits-dms#0]. Если нужно уточнить состав базовой программы, обратитесь в HR.
```

### `dms-family` — Можно ли застраховать супруга по ДМС?

- stratum: `fact`
- audience: `all`
- escalated: False (expected False)
- escalation reason: answered (expected -)
- missing fragments: оплатой 50%
- forbidden fragments: -
- retrieved: hr/benefits-dms, company/org-structure, hr/expenses, hr/sick-leave-notification
- context: hr/benefits-dms, company/org-structure, hr/expenses, company/anti-corruption, hr/sick-leave-notification, procurement/supplier-onboarding, hr/business-trip, it/security, it/access-and-equipment, it/vpn-setup, hr/probation, finance/counterparty-check, it/software-licenses, hr/onboarding-first-day, company/speak-up, hr/sick-leave-pay, it/backup-policy, company/code-of-conduct, procurement/purchase-request, hr/donor-day, it/office-network, it/password-reset, security/badge-access, hr/unpaid-leave, finance/invoice-processing

```
Согласно базе знаний, члены семьи (включая супруга) могут быть подключены к программе ДМС на условиях страховой, при этом оплата составляет 50% из личных средств сотрудника [hr/benefits-dms#1]. Для уточнения порядка подключения обратитесь в HR-подразделение по почте hr@polypiast.ru [company/org-structure#0].
```

### `peripherals-request` — Как получить гарнитуру и мышку?

- stratum: `fact`
- audience: `all`
- escalated: False (expected False)
- escalation reason: answered (expected -)
- missing fragments: периферия
- forbidden fragments: -
- retrieved: it/access-and-equipment, hr/onboarding-first-day, it/vpn-setup, hr/remote-work
- context: it/access-and-equipment, hr/onboarding-first-day, it/vpn-setup, hr/remote-work, it/office-network, it/software-licenses, company/org-structure, procurement/purchase-request, company/workspace-rules, it/hardware-repair, it/security, hr/exit, company/trademark-use, hr/benefits-dms, it/account-lifecycle, hr/expenses, it/password-reset, company/anti-corruption, hr/benefits-meals, security/badge-access, hr/donor-day, company/code-of-conduct, hr/payroll, hr/probation, procurement/supplier-onboarding, it/backup-policy

```
Мышь, клавиатура, гарнитура и док-станция выдаются по заявке в ИТ-поддержку. Оформите заявку — и оборудование вам предоставят.
```

### `pricing-renewal-approval` — Нужно ли заново согласовывать скидку при продлении контракта?

- stratum: `fact`
- audience: `dept:sales`
- escalated: False (expected False)
- escalation reason: answered (expected -)
- missing fragments: продление
- forbidden fragments: -
- retrieved: sales/pricing-approval, sales/contract-approval, sales/kp-rules, finance/counterparty-check, procurement/purchase-request
- context: sales/pricing-approval, sales/contract-approval, sales/kp-rules, finance/counterparty-check, procurement/purchase-request, procurement/supplier-onboarding, company/anti-corruption, hr/dismissal-agreement, sales/crm-rules, hr/probation, procurement/tender-rules, hr/referral, hr/overtime, it/software-licenses, company/trademark-use, hr/night-pay, hr/donor-day, company/workspace-rules, hr/internal-transfer, it/password-reset, sales/tender-participation, hr/leave-policy, company/code-of-conduct, finance/invoice-processing, hr/payroll, hr/relocation, hr/expenses, hr/part-time, finance/budget-request, hr/remote-work

```
При продлении действующего контракта новое согласование скидки не требуется, если скидка не выросла [sales/pricing-approval#0]. Если скидка увеличивается, её нужно согласовать по общим уровням: до 5% — самостоятельно, от 5% до 10% — с руководителем группы, выше 10% — письменно с директором по продажам [sales/pricing-approval#0]. Следующий шаг: проверьте, не выросла ли скидка относительно действующего контракта, и при росте оформите согласование.
```

### `remote-public-network` — Можно ли поработать из кафе?

- stratum: `fact`
- audience: `all`
- escalated: False (expected False)
- escalation reason: answered (expected -)
- missing fragments: публичные сети
- forbidden fragments: -
- retrieved: company/workspace-rules, hr/remote-work, it/office-network, it/vpn-setup
- context: hr/remote-work, company/workspace-rules, it/office-network, it/vpn-setup, hr/benefits-meals, hr/overtime, hr/part-time, it/access-and-equipment, it/account-lifecycle, it/password-reset, hr/payroll, company/org-structure, hr/leave-policy, hr/night-pay, hr/exit, it/hardware-repair, procurement/purchase-request, hr/referral, hr/expenses, hr/onboarding-first-day, hr/business-trip, security/badge-access, it/software-licenses, hr/relocation, hr/study-leave, company/trademark-use, hr/donor-day

```
Работать удалённо разрешено только из домашней сети или с мобильного интернета, поэтому кафе с публичным Wi-Fi не подходит. Кроме того, экран не должен быть виден посторонним. Согласуйте день удалённой работы с руководителем заранее.
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
Ноутбук выдают в первый рабочий день в офисе ИТ-поддержки. Для получения нужны пропуск и подтверждение от руководителя [it/access-and-equipment#0]. Если вы уже не первый день в компании — уточните в ИТ-поддержке, согласована ли выдача.
```

