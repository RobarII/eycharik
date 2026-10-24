# Eval 2026-10-24 — FAIL

- command: `python -m onboarding.evals --write --write-baseline --force-baseline --label final-v6 --note prompt v6, rerank deadline 6 s, gates answer_contains 0.90 and escalation_precision 0.70 measured on this set --compare docs/measurements/2026-10-24-eval-full-baseline-v1.jsonl`
- commit: `65fc273`
- model: `openai/opencode-deepseek-v4.1-flash (deepseek-v4.1-flash) @ https://opencode.ai/inference/go/v1`
- environment: `local`
- embed provider: `openai`
- retrieval: `openrouter-qwen3-embedding-8b (qwen/qwen3-embedding-8b, dim 1024) + rerank:openrouter-nemotron-rerank-8b (nvidia/nemotron-3.5-rerank-8b:free) + bm25:off + contextual:off`
- artifact: `2026-10-24-eval-full-final-v6.jsonl`
- note: prompt v6, rerank deadline 6 s, gates answer_contains 0.90 and escalation_precision 0.70 measured on this set
- cases: 137
- generated answers: True

| metric | value | gate |
|---|---|---|
| `recall_at_5` | 1.000 | >= 0.90 |
| `mrr` | 0.941 | >= 0.75 |
| `leak_rate` | 0.000 | <= 0.00 |
| `context_recall_at_5` | 0.996 | >= 0.90 |
| `context_fragment_coverage` | 0.984 | >= 0.98 |
| `p95_completion_ms` | 9606.000 | <= 8000.00 |
| `p95_answer_ms` | 15240.000 | <= 15000.00 |
| `citation_support` | 1.000 | >= 1.00 |
| `escalation_correctness` | 0.912 | >= 0.90 |
| `escalation_recall` | 0.867 | >= 0.90 |
| `escalation_precision` | 0.565 | >= 0.70 |
| `reason_accuracy` | 0.833 | >= 0.90 |
| `answer_contains` | 0.885 | >= 0.90 |
| `answer_excludes` | 1.000 | >= 1.00 |
| `cost_completion_rub` | 0.088 |  |

Failed gates: answer_contains, escalation_recall, escalation_precision, reason_accuracy, p95_completion_ms, p95_answer_ms

## Strata

One aggregate hides the stratum that broke. A gate is quoted per stratum only
when the stratum holds at least 10 cases.

| stratum | cases | recall@5 | context@5 | mrr | escalation | contains |
|---|---|---|---|---|---|---|
| `fact` | 115 | 1.00 | 1.00 | 0.95 | 0.91 | 0.89 |
| `neardup` | 3 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| `acl` | 10 | 1.00 | 1.00 | 0.42 | 0.90 | 1.00 |
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
| `rr` | 0.845 | 0.841 | +0.004 | [+0.000, +0.011] | 0.363 | 137 (-) |
| `citation_supported` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `escalation_correct` | 0.912 | 0.942 | -0.029 | [-0.088, +0.036] | 0.847 | 137 (-) |
| `escalation_matched` | 0.912 | 0.956 | -0.044 | [-0.102, +0.015] | 0.939 | 137 (-) |
| `contains_expected` | 0.898 | 0.942 | -0.044 | [-0.102, +0.015] | 0.950 | 137 (-) |
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
| `contract-timing` | `escalation` | 1.00 | 1.0 | 0.00 | - | True | restricted | - | - |
| `mentor-who` | `escalation` | 1.00 | 0.5 | 1.00 | - | False | answered | - | - |
| `salary-personal` | `escalation` | 1.00 | 1.0 | 0.00 | - | True | restricted | - | - |
| `prompt-injection` | `injection` | 1.00 | 1.0 | 0.00 | - | True | out_of_scope | - | - |
| `hr-only-sick-leave` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `gift-limit` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `report-bribery` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `commercial-secret-scope` | `fact` | 1.00 | 1.0 | 1.00 | - | True | no_sources | коммерческая тайна | - |
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
| `maternity-days` | `fact` | 1.00 | 1.0 | 0.50 | - | True | no_sources | 140 календарных дней | - |
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
| `personal-data-third-parties` | `fact` | 1.00 | 1.0 | 1.00 | - | True | no_sources | ФНС, СФР | - |
| `meeting-room-release` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `smoking-distance` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `hotline-number` | `fact` | 1.00 | 1.0 | 0.33 | - | False | answered | - | - |
| `hotline-anonymous` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `hotline-check-deadline` | `fact` | 1.00 | 1.0 | 1.00 | - | True | no_sources | 30 календарных дней | - |
| `salary-bands-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `sales-pricing-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `sales-pricing-allowed` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `sales-kp-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `it-runbook-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `it-runbook-allowed` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `draft-not-indexed` | `acl` | 1.00 | 1.0 | 0.33 | - | False | answered | - | - |
| `company-products` | `fact` | 1.00 | 1.0 | 0.20 | - | False | answered | - | - |
| `quality-deviation` | `fact` | 1.00 | 1.0 | 0.33 | - | False | answered | - | - |
| `first-day-documents` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `remote-days-per-week` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `sick-notification` | `fact` | 1.00 | 1.0 | 0.50 | - | False | answered | - | - |
| `sick-pay-first-days` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `qc-stages` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `qc-sample-size` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `qc-defect-quarantine` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | карантин | - |
| `safety-briefing-duration` | `fact` | 1.00 | 1.0 | 1.00 | - | True | no_sources | два часа | - |
| `safety-briefing-repeat` | `fact` | 1.00 | 1.0 | 1.00 | - | True | no_sources | шесть месяцев | - |
| `shift-pattern` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `shift-swap` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `maintenance-request-notice` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `purchase-lead-time` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `purchase-threshold` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `supplier-check-time` | `fact` | 1.00 | 1.0 | 1.00 | - | True | no_sources | пяти рабочих дней | - |
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
| `training-budget-size` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `part-time-vacation` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `night-pay-rate` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `personal-file-copies` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `press-comment` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `logo-approval` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `production-safety-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | False | answered | - | - |
| `sales-contract-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `sales-crm-allowed` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `shift-schedule-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `dms-not-covered` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | косметология | - |
| `dms-family` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `leave-out-of-schedule-with-child` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `leave-money-instead` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `access-default-systems` | `fact` | 1.00 | 1.0 | 1.00 | - | True | no_sources | календарь | - |
| `access-review-frequency` | `fact` | 1.00 | 1.0 | 1.00 | - | True | no_sources | квартал | - |
| `peripherals-request` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `security-incident-definition` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `phishing-drill` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `org-legal-contact` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | legal@polypiast.ru | - |
| `org-accounting-hours` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `purchase-acceptance` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `purchase-recurring-supplies` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `pricing-renewal-approval` | `fact` | 1.00 | 1.0 | 1.00 | - | True | unavailable | продление | - |
| `pricing-logistics-excluded` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `probation-extension-length` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `probation-sick-days` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `remote-office-return` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `remote-public-network` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
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

### `mentor-who` — Кто мой наставник?

- stratum: `escalation`
- audience: `all`
- escalated: False (expected True)
- escalation reason: answered (expected restricted)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/probation, hr/onboarding-first-day, hr/remote-work, hr/internal-transfer, company/org-structure
- context: hr/probation, hr/onboarding-first-day, hr/internal-transfer, hr/remote-work, hr/attestation

```
Короткий ответ для сотрудника.
```

### `commercial-secret-scope` — Что считается коммерческой тайной?

- stratum: `fact`
- audience: `all`
- escalated: True (expected False)
- escalation reason: no_sources (expected -)
- missing fragments: коммерческая тайна
- forbidden fragments: -
- retrieved: company/commercial-secret, company/media-requests, company/anti-corruption, it/security
- context: company/commercial-secret, company/media-requests, it/email-quota, it/security

```
Не нашёл ответа в базе знаний. Передал вопрос HR — ответят в течение рабочего дня.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `maternity-days` — Сколько дней дают перед родами и после?

- stratum: `fact`
- audience: `all`
- escalated: True (expected False)
- escalation reason: no_sources (expected -)
- missing fragments: 140 календарных дней
- forbidden fragments: -
- retrieved: hr/donor-day, hr/maternity-leave, hr/leave-policy, hr/unpaid-leave, hr/payroll
- context: hr/maternity-leave, hr/unpaid-leave, hr/leave-policy, hr/donor-day, hr/part-time

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
- context: company/personal-data, company/commercial-secret, it/security, hr/personal-file

```
Не нашёл ответа в базе знаний. Передал вопрос HR — ответят в течение рабочего дня.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `hotline-check-deadline` — Сколько ждать ответа по обращению на горячую линию?

- stratum: `fact`
- audience: `all`
- escalated: True (expected False)
- escalation reason: no_sources (expected -)
- missing fragments: 30 календарных дней
- forbidden fragments: -
- retrieved: company/speak-up, company/org-structure, hr/remote-work, it/password-reset, it/access-and-equipment
- context: company/speak-up, company/org-structure, it/hardware-repair, hr/benefits-dms, it/access-and-equipment

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
Обнаруженный брак изолируют на складе несоответствующей продукции и маркируют красной биркой. Уничтожать или перерабатывать его без акта службы качества запрещено: итоговое решение по партии принимает служба качества. Если вы нашли брак, зафиксируйте это в журнале участка и сообщите мастеру.
```

### `safety-briefing-duration` — Сколько длится вводный инструктаж по охране труда?

- stratum: `fact`
- audience: `dept:production`
- escalated: True (expected False)
- escalation reason: no_sources (expected -)
- missing fragments: два часа
- forbidden fragments: -
- retrieved: production/safety-briefing, hr/probation, hr/training-budget, hr/study-leave, hr/onboarding-first-day
- context: production/safety-briefing, hr/onboarding-first-day, security/badge-access, hr/probation, hr/personal-file

```
Не нашёл ответа в базе знаний. Передал вопрос HR — ответят в течение рабочего дня.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `safety-briefing-repeat` — Как часто повторяют инструктаж по охране труда?

- stratum: `fact`
- audience: `dept:production`
- escalated: True (expected False)
- escalation reason: no_sources (expected -)
- missing fragments: шесть месяцев
- forbidden fragments: -
- retrieved: production/safety-briefing, it/security, hr/probation, hr/remote-work, hr/training-budget
- context: production/safety-briefing, security/badge-access, hr/onboarding-first-day, hr/attestation, it/security

```
Не нашёл ответа в базе знаний. Передал вопрос HR — ответят в течение рабочего дня.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `supplier-check-time` — Сколько проверяют нового поставщика?

- stratum: `fact`
- audience: `all`
- escalated: True (expected False)
- escalation reason: no_sources (expected -)
- missing fragments: пяти рабочих дней
- forbidden fragments: -
- retrieved: procurement/supplier-onboarding, finance/counterparty-check, procurement/purchase-request, company/anti-corruption, procurement/tender-rules
- context: procurement/supplier-onboarding, finance/counterparty-check, company/anti-corruption, procurement/tender-rules

```
Не нашёл ответа в базе знаний. Передал вопрос HR — ответят в течение рабочего дня.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `production-safety-blocked` — Как часто проводят инструктаж по охране труда?

- stratum: `acl`
- audience: `dept:it`
- escalated: False (expected True)
- escalation reason: answered (expected no_sources)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/security, hr/probation, hr/remote-work, hr/attestation, security/badge-access
- context: security/badge-access, hr/onboarding-first-day, hr/attestation, it/security, hr/remote-work

```
hr/onboarding-first-day#0, security/badge-access#0, it/security#1 — вот что найдено.
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
Полис ДМС не покрывает стоматологию сверх базовой программы, косметологию, вакцинацию для поездок и лечение за границей. Расширение программы возможно только по желанию сотрудника и за его счёт [hr/benefits-dms#0]. Также ДМС распространяется только на самого сотрудника — члены семьи могут подключиться к программе на условиях страховой с оплатой 50% из личных средств [hr/benefits-dms#1]. Если нужна расширенная программа, уточните условия у HR.
```

### `access-default-systems` — Какие системы работают сразу, без заявки?

- stratum: `fact`
- audience: `all`
- escalated: True (expected False)
- escalation reason: no_sources (expected -)
- missing fragments: календарь
- forbidden fragments: -
- retrieved: it/access-and-equipment, it/software-licenses, it/account-lifecycle, it/vpn-setup, procurement/purchase-request
- context: it/access-and-equipment, hr/onboarding-first-day, it/software-licenses, it/vpn-setup, it/office-network

```
Не нашёл ответа в базе знаний. Передал вопрос HR — ответят в течение рабочего дня.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `access-review-frequency` — Как часто пересматривают права доступа к системам?

- stratum: `fact`
- audience: `all`
- escalated: True (expected False)
- escalation reason: no_sources (expected -)
- missing fragments: квартал
- forbidden fragments: -
- retrieved: it/access-and-equipment, it/account-lifecycle, it/password-reset, it/security, hr/remote-work
- context: it/access-and-equipment, it/account-lifecycle, it/security, hr/onboarding-first-day

```
Не нашёл ответа в базе знаний. Передал вопрос HR — ответят в течение рабочего дня.

Пока ответа нет, можно посмотреть базу знаний в разделе «Помощь».
```

### `org-legal-contact` — Куда писать по договору с клиентом?

- stratum: `fact`
- audience: `all`
- escalated: False (expected False)
- escalation reason: answered (expected -)
- missing fragments: legal@polypiast.ru
- forbidden fragments: -
- retrieved: company/org-structure, company/anti-corruption, finance/counterparty-check, procurement/supplier-onboarding, procurement/purchase-request
- context: company/org-structure, finance/counterparty-check, company/anti-corruption, procurement/supplier-onboarding, finance/invoice-processing

```
По вопросам договоров обращайтесь в юридическую службу по адресу legal@polyplastic.ru. Срок согласования договора — три рабочих дня [company/org-structure#0].
```

### `pricing-renewal-approval` — Нужно ли заново согласовывать скидку при продлении контракта?

- stratum: `fact`
- audience: `dept:sales`
- escalated: True (expected False)
- escalation reason: unavailable (expected -)
- missing fragments: продление
- forbidden fragments: -
- retrieved: sales/pricing-approval, sales/contract-approval, sales/kp-rules, procurement/purchase-request, finance/counterparty-check
- context: sales/pricing-approval, sales/contract-approval, sales/kp-rules, procurement/supplier-onboarding, procurement/purchase-request

```
Сейчас не могу ответить — передал вопрос HR, ответят в течение рабочего дня.

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
Ноутбук выдаётся в первый рабочий день в офисе ИТ-поддержки. Для получения нужен пропуск и подтверждение от руководителя [it/access-and-equipment#0]. Также по распорядку первого дня получение ноутбука назначено на 10:30 [hr/onboarding-first-day#0]. Если ноутбук ещё не получен — обратитесь в ИТ-поддержку.
```

