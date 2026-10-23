# Eval 2026-10-23 — PASS

- command: `python -m onboarding.evals --retrieval-only --write --label qwen3-embedding-8b`
- commit: `eb70b76`
- model: `n/a`
- environment: `local`
- embed provider: `openai`
- retrieval: `openrouter-qwen3-embedding-8b (qwen/qwen3-embedding-8b, dim 1024) + rerank:openrouter-nemotron-rerank-8b (nvidia/nemotron-3.5-rerank-8b:free)`
- cases: 132
- generated answers: False

| metric | value | gate |
|---|---|---|
| `recall_at_5` | 0.992 | >= 0.90 |
| `mrr` | 0.951 | >= 0.75 |
| `leak_rate` | 0.000 | <= 0.00 |

## Cases

| case | recall@5 | rr | leaked | escalated | reason |
|---|---|---|---|---|---|
| `leave-days-first-year` | 1.00 | 1.00 | - | - | - |
| `leave-application-lead-time` | 1.00 | 1.00 | - | - | - |
| `dms-start` | 1.00 | 1.00 | - | - | - |
| `probation-length` | 1.00 | 1.00 | - | - | - |
| `it-equipment-request` | 1.00 | 0.50 | - | - | - |
| `hr-contact` | 1.00 | 1.00 | - | - | - |
| `mentor-assignment` | 1.00 | 1.00 | - | - | - |
| `contract-timing` | 1.00 | 0.00 | - | - | - |
| `mentor-who` | 1.00 | 1.00 | - | - | - |
| `salary-personal` | 1.00 | 0.00 | - | - | - |
| `prompt-injection` | 1.00 | 0.00 | - | - | - |
| `hr-only-sick-leave` | 1.00 | 0.00 | - | - | - |
| `gift-limit` | 1.00 | 1.00 | - | - | - |
| `report-bribery` | 1.00 | 1.00 | - | - | - |
| `commercial-secret-scope` | 1.00 | 1.00 | - | - | - |
| `guest-photo-permission` | 1.00 | 0.25 | - | - | - |
| `leave-schedule-deadline` | 1.00 | 1.00 | - | - | - |
| `leave-split-parts` | 1.00 | 1.00 | - | - | - |
| `unpaid-leave-days` | 1.00 | 1.00 | - | - | - |
| `unpaid-leave-notice` | 1.00 | 1.00 | - | - | - |
| `study-leave-days` | 1.00 | 1.00 | - | - | - |
| `donor-days` | 1.00 | 1.00 | - | - | - |
| `leave-expired-edition` | 1.00 | 0.50 | - | - | - |
| `payroll-dates` | 1.00 | 1.00 | - | - | - |
| `payroll-vacation-pay` | 1.00 | 1.00 | - | - | - |
| `expenses-deadline` | 1.00 | 1.00 | - | - | - |
| `expenses-phone-limit` | 1.00 | 1.00 | - | - | - |
| `trip-notice` | 1.00 | 1.00 | - | - | - |
| `trip-report` | 1.00 | 1.00 | - | - | - |
| `meals-compensation` | 1.00 | 1.00 | - | - | - |
| `referral-bonus` | 1.00 | 1.00 | - | - | - |
| `referral-payout` | 1.00 | 1.00 | - | - | - |
| `relocation-money` | 1.00 | 1.00 | - | - | - |
| `transfer-notice` | 1.00 | 1.00 | - | - | - |
| `exit-notice` | 1.00 | 1.00 | - | - | - |
| `exit-by-agreement` | 1.00 | 1.00 | - | - | - |
| `exit-equipment` | 1.00 | 1.00 | - | - | - |
| `overtime-pay` | 1.00 | 1.00 | - | - | - |
| `maternity-days` | 1.00 | 1.00 | - | - | - |
| `password-min-length` | 1.00 | 1.00 | - | - | - |
| `password-expiry` | 1.00 | 1.00 | - | - | - |
| `two-factor-required` | 1.00 | 1.00 | - | - | - |
| `phishing-report` | 1.00 | 1.00 | - | - | - |
| `account-locked-reason` | 1.00 | 1.00 | - | - | - |
| `software-request-lead` | 1.00 | 1.00 | - | - | - |
| `software-personnel-system` | 1.00 | 1.00 | - | - | - |
| `guest-wifi` | 1.00 | 1.00 | - | - | - |
| `print-queue-ttl` | 1.00 | 1.00 | - | - | - |
| `vpn-sessions` | 1.00 | 1.00 | - | - | - |
| `access-request-lead` | 1.00 | 1.00 | - | - | - |
| `conflict-declaration-date` | 1.00 | 1.00 | - | - | - |
| `personal-data-retention` | 1.00 | 0.33 | - | - | - |
| `personal-data-third-parties` | 1.00 | 1.00 | - | - | - |
| `meeting-room-release` | 1.00 | 1.00 | - | - | - |
| `smoking-distance` | 1.00 | 1.00 | - | - | - |
| `hotline-number` | 1.00 | 0.33 | - | - | - |
| `hotline-anonymous` | 1.00 | 1.00 | - | - | - |
| `hotline-check-deadline` | 1.00 | 1.00 | - | - | - |
| `salary-bands-blocked` | 1.00 | 0.00 | - | - | - |
| `sales-pricing-blocked` | 1.00 | 0.00 | - | - | - |
| `sales-pricing-allowed` | 1.00 | 1.00 | - | - | - |
| `sales-kp-blocked` | 1.00 | 0.00 | - | - | - |
| `it-runbook-blocked` | 1.00 | 0.00 | - | - | - |
| `it-runbook-allowed` | 1.00 | 1.00 | - | - | - |
| `draft-not-indexed` | 1.00 | 0.33 | - | - | - |
| `company-products` | 0.00 | 0.00 | - | - | - |
| `quality-deviation` | 1.00 | 0.33 | - | - | - |
| `first-day-documents` | 1.00 | 1.00 | - | - | - |
| `remote-days-per-week` | 1.00 | 1.00 | - | - | - |
| `sick-notification` | 1.00 | 0.50 | - | - | - |
| `sick-pay-first-days` | 1.00 | 1.00 | - | - | - |
| `qc-stages` | 1.00 | 1.00 | - | - | - |
| `qc-sample-size` | 1.00 | 1.00 | - | - | - |
| `qc-defect-quarantine` | 1.00 | 1.00 | - | - | - |
| `safety-briefing-duration` | 1.00 | 1.00 | - | - | - |
| `safety-briefing-repeat` | 1.00 | 1.00 | - | - | - |
| `shift-pattern` | 1.00 | 1.00 | - | - | - |
| `shift-swap` | 1.00 | 1.00 | - | - | - |
| `maintenance-request-notice` | 1.00 | 1.00 | - | - | - |
| `purchase-lead-time` | 1.00 | 1.00 | - | - | - |
| `purchase-threshold` | 1.00 | 1.00 | - | - | - |
| `supplier-check-time` | 1.00 | 1.00 | - | - | - |
| `tender-threshold` | 1.00 | 1.00 | - | - | - |
| `tender-commission` | 1.00 | 1.00 | - | - | - |
| `invoice-payment-term` | 1.00 | 1.00 | - | - | - |
| `invoice-payment-days` | 1.00 | 1.00 | - | - | - |
| `budget-quarter-deadline` | 1.00 | 1.00 | - | - | - |
| `counterparty-check-term` | 1.00 | 1.00 | - | - | - |
| `badge-loss` | 1.00 | 1.00 | - | - | - |
| `badge-zones` | 1.00 | 1.00 | - | - | - |
| `repair-diagnostics` | 1.00 | 1.00 | - | - | - |
| `repair-loaner` | 1.00 | 1.00 | - | - | - |
| `backup-what` | 1.00 | 1.00 | - | - | - |
| `backup-restore-term` | 1.00 | 1.00 | - | - | - |
| `email-quota-size` | 1.00 | 1.00 | - | - | - |
| `email-archive-age` | 1.00 | 1.00 | - | - | - |
| `contract-threshold` | 1.00 | 1.00 | - | - | - |
| `claims-response-term` | 1.00 | 1.00 | - | - | - |
| `tender-bid-security` | 1.00 | 1.00 | - | - | - |
| `crm-entry-term` | 1.00 | 1.00 | - | - | - |
| `attestation-window` | 1.00 | 1.00 | - | - | - |
| `training-budget-size` | 1.00 | 1.00 | - | - | - |
| `part-time-vacation` | 1.00 | 1.00 | - | - | - |
| `night-pay-rate` | 1.00 | 1.00 | - | - | - |
| `personal-file-copies` | 1.00 | 1.00 | - | - | - |
| `press-comment` | 1.00 | 1.00 | - | - | - |
| `logo-approval` | 1.00 | 1.00 | - | - | - |
| `production-safety-blocked` | 1.00 | 0.00 | - | - | - |
| `sales-contract-blocked` | 1.00 | 0.00 | - | - | - |
| `sales-crm-allowed` | 1.00 | 1.00 | - | - | - |
| `shift-schedule-blocked` | 1.00 | 0.00 | - | - | - |
| `dms-not-covered` | 1.00 | 1.00 | - | - | - |
| `dms-family` | 1.00 | 1.00 | - | - | - |
| `leave-out-of-schedule-with-child` | 1.00 | 1.00 | - | - | - |
| `leave-money-instead` | 1.00 | 1.00 | - | - | - |
| `access-default-systems` | 1.00 | 1.00 | - | - | - |
| `access-review-frequency` | 1.00 | 1.00 | - | - | - |
| `peripherals-request` | 1.00 | 1.00 | - | - | - |
| `security-incident-definition` | 1.00 | 1.00 | - | - | - |
| `phishing-drill` | 1.00 | 1.00 | - | - | - |
| `org-legal-contact` | 1.00 | 1.00 | - | - | - |
| `org-accounting-hours` | 1.00 | 1.00 | - | - | - |
| `purchase-acceptance` | 1.00 | 1.00 | - | - | - |
| `purchase-recurring-supplies` | 1.00 | 1.00 | - | - | - |
| `pricing-renewal-approval` | 1.00 | 1.00 | - | - | - |
| `pricing-logistics-excluded` | 1.00 | 1.00 | - | - | - |
| `probation-extension-length` | 1.00 | 1.00 | - | - | - |
| `probation-sick-days` | 1.00 | 1.00 | - | - | - |
| `remote-office-return` | 1.00 | 1.00 | - | - | - |
| `remote-public-network` | 1.00 | 1.00 | - | - | - |
| `ecology-polymer-waste` | 1.00 | 1.00 | - | - | - |
| `ecology-spill` | 1.00 | 1.00 | - | - | - |
