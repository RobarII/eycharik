# Eval 2026-10-24 — PASS

- command: `python -m onboarding.evals.acl --write`
- commit: `332d88b`
- model: `n/a`
- environment: `local`
- embed provider: `openai`
- artifact: `2026-10-24-eval-retrieval-acl-matrix.jsonl`
- note: every (viewer, document) pair; recall is over-restriction, leak_rate is disclosure
- cases: 345
- generated answers: False

| metric | value | gate |
|---|---|---|
| `recall_at_5` | 1.000 | >= 0.90 |
| `mrr` | 0.993 | >= 0.75 |
| `leak_rate` | 0.000 | <= 0.00 |

## Strata

One aggregate hides the stratum that broke. A gate is quoted per stratum only
when the stratum holds at least 10 cases.

| stratum | cases | recall@5 | context@5 | mrr | escalation | contains |
|---|---|---|---|---|---|---|
| `acl` | 345 | 1.00 | - | 0.99 | - | - |

## Cases

| case | stratum | recall@5 | ctx@5 | rr | leaked | escalated | reason | missing | forbidden |
|---|---|---|---|---|---|---|---|---|---|
| `acl-all-company-about` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-company-anti-corruption` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-company-code-of-conduct` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-company-commercial-secret` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-company-media-requests` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-company-org-structure` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-company-personal-data` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-company-quality-ecology` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-company-speak-up` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-company-trademark-use` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-company-workspace-rules` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-finance-budget-request` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-finance-counterparty-check` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-finance-invoice-processing` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-attestation` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-benefits-dms` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-benefits-meals` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-business-trip` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-dismissal-agreement` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-donor-day` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-exit` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-expenses` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-internal-transfer` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-leave-policy-2025` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-all-hr-leave-policy` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-leave-schedule` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-maternity-leave` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-night-pay` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-onboarding-first-day` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-overtime` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-part-time` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-payroll` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-personal-file` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-probation` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-referral` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-relocation` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-remote-work` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-salary-bands` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-all-hr-sick-leave-notification` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-sick-leave-pay` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-sick-leave` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-all-hr-study-leave` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-training-budget` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-hr-unpaid-leave` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-it-access-and-equipment` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-it-account-lifecycle` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-it-backup-policy` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-it-email-quota` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-it-hardware-repair` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-it-incident-runbook` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-all-it-office-network` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-it-password-reset` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-it-security` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-it-software-licenses` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-it-vpn-setup` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-procurement-purchase-request` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-procurement-supplier-onboarding` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-procurement-tender-rules` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-production-equipment-maintenance` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-all-production-quality-control` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-all-production-safety-briefing` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-all-production-shift-schedule` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-all-sales-contract-approval` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-all-sales-crm-rules` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-all-sales-customer-claims` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-all-sales-kp-rules` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-all-sales-pricing-approval` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-all-sales-tender-participation` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-all-security-badge-access` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-company-about` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-company-anti-corruption` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-company-code-of-conduct` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-company-commercial-secret` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-company-media-requests` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-company-org-structure` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-company-personal-data` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-company-quality-ecology` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-company-speak-up` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-company-trademark-use` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-company-workspace-rules` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-finance-budget-request` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-finance-counterparty-check` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-finance-invoice-processing` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-attestation` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-benefits-dms` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-benefits-meals` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-business-trip` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-dismissal-agreement` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-donor-day` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-exit` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-expenses` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-internal-transfer` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-leave-policy-2025` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-hr_only-hr-leave-policy` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-leave-schedule` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-maternity-leave` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-night-pay` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-onboarding-first-day` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-overtime` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-part-time` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-payroll` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-personal-file` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-probation` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-referral` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-relocation` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-remote-work` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-salary-bands` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-sick-leave-notification` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-sick-leave-pay` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-sick-leave` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-study-leave` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-training-budget` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-hr-unpaid-leave` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-it-access-and-equipment` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-it-account-lifecycle` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-it-backup-policy` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-it-email-quota` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-it-hardware-repair` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-it-incident-runbook` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-hr_only-it-office-network` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-it-password-reset` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-it-security` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-it-software-licenses` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-it-vpn-setup` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-procurement-purchase-request` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-procurement-supplier-onboarding` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-procurement-tender-rules` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-production-equipment-maintenance` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-hr_only-production-quality-control` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-hr_only-production-safety-briefing` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-hr_only-production-shift-schedule` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-hr_only-sales-contract-approval` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-hr_only-sales-crm-rules` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-hr_only-sales-customer-claims` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-hr_only-sales-kp-rules` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-hr_only-sales-pricing-approval` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-hr_only-sales-tender-participation` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-hr_only-security-badge-access` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-company-about` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-company-anti-corruption` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-company-code-of-conduct` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-company-commercial-secret` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-company-media-requests` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-company-org-structure` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-company-personal-data` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-company-quality-ecology` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-company-speak-up` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-company-trademark-use` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-company-workspace-rules` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-finance-budget-request` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-finance-counterparty-check` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-finance-invoice-processing` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-attestation` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-benefits-dms` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-benefits-meals` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-business-trip` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-dismissal-agreement` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-donor-day` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-exit` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-expenses` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-internal-transfer` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-leave-policy-2025` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-it-hr-leave-policy` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-leave-schedule` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-maternity-leave` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-night-pay` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-onboarding-first-day` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-overtime` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-part-time` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-payroll` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-personal-file` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-probation` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-referral` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-relocation` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-remote-work` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-salary-bands` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-it-hr-sick-leave-notification` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-sick-leave-pay` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-sick-leave` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-it-hr-study-leave` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-training-budget` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-hr-unpaid-leave` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-it-access-and-equipment` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-it-account-lifecycle` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-it-backup-policy` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-it-email-quota` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-it-hardware-repair` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-it-incident-runbook` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-it-office-network` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-it-password-reset` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-it-security` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-it-software-licenses` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-it-vpn-setup` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-procurement-purchase-request` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-procurement-supplier-onboarding` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-procurement-tender-rules` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-production-equipment-maintenance` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-it-production-quality-control` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-it-production-safety-briefing` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-it-production-shift-schedule` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-it-sales-contract-approval` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-it-sales-crm-rules` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-it-sales-customer-claims` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-it-sales-kp-rules` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-it-sales-pricing-approval` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-it-sales-tender-participation` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-it-security-badge-access` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-company-about` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-company-anti-corruption` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-company-code-of-conduct` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-company-commercial-secret` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-company-media-requests` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-company-org-structure` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-company-personal-data` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-company-quality-ecology` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-company-speak-up` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-company-trademark-use` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-company-workspace-rules` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-finance-budget-request` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-finance-counterparty-check` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-finance-invoice-processing` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-attestation` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-benefits-dms` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-benefits-meals` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-business-trip` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-dismissal-agreement` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-donor-day` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-exit` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-expenses` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-internal-transfer` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-leave-policy-2025` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-sales-hr-leave-policy` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-leave-schedule` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-maternity-leave` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-night-pay` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-onboarding-first-day` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-overtime` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-part-time` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-payroll` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-personal-file` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-probation` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-referral` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-relocation` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-remote-work` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-salary-bands` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-sales-hr-sick-leave-notification` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-sick-leave-pay` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-sick-leave` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-sales-hr-study-leave` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-training-budget` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-hr-unpaid-leave` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-it-access-and-equipment` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-it-account-lifecycle` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-it-backup-policy` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-it-email-quota` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-it-hardware-repair` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-it-incident-runbook` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-sales-it-office-network` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-it-password-reset` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-it-security` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-it-software-licenses` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-it-vpn-setup` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-procurement-purchase-request` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-procurement-supplier-onboarding` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-procurement-tender-rules` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-production-equipment-maintenance` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-sales-production-quality-control` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-production-safety-briefing` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-sales-production-shift-schedule` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-sales-sales-contract-approval` | `acl` | 1.00 | - | 0.33 | - | - | - | - | - |
| `acl-dept-sales-sales-crm-rules` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-sales-customer-claims` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-sales-kp-rules` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-sales-pricing-approval` | `acl` | 1.00 | - | 0.20 | - | - | - | - | - |
| `acl-dept-sales-sales-tender-participation` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-sales-security-badge-access` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-company-about` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-company-anti-corruption` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-company-code-of-conduct` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-company-commercial-secret` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-company-media-requests` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-company-org-structure` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-company-personal-data` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-company-quality-ecology` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-company-speak-up` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-company-trademark-use` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-company-workspace-rules` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-finance-budget-request` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-finance-counterparty-check` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-finance-invoice-processing` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-attestation` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-benefits-dms` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-benefits-meals` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-business-trip` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-dismissal-agreement` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-donor-day` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-exit` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-expenses` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-internal-transfer` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-leave-policy-2025` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-production-hr-leave-policy` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-leave-schedule` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-maternity-leave` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-night-pay` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-onboarding-first-day` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-overtime` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-part-time` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-payroll` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-personal-file` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-probation` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-referral` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-relocation` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-remote-work` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-salary-bands` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-production-hr-sick-leave-notification` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-sick-leave-pay` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-sick-leave` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-production-hr-study-leave` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-training-budget` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-hr-unpaid-leave` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-it-access-and-equipment` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-it-account-lifecycle` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-it-backup-policy` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-it-email-quota` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-it-hardware-repair` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-it-incident-runbook` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-production-it-office-network` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-it-password-reset` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-it-security` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-it-software-licenses` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-it-vpn-setup` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-procurement-purchase-request` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-procurement-supplier-onboarding` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-procurement-tender-rules` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-production-equipment-maintenance` | `acl` | 1.00 | - | 0.33 | - | - | - | - | - |
| `acl-dept-production-production-quality-control` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-production-safety-briefing` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-production-shift-schedule` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |
| `acl-dept-production-sales-contract-approval` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-production-sales-crm-rules` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-production-sales-customer-claims` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-production-sales-kp-rules` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-production-sales-pricing-approval` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-production-sales-tender-participation` | `acl` | 1.00 | - | 0.00 | - | - | - | - | - |
| `acl-dept-production-security-badge-access` | `acl` | 1.00 | - | 1.00 | - | - | - | - | - |

## Failures in detail

A failing gate needs the answer that failed it, not just the count: the same number
can mean a wrong fact, a wrong format, or a confidently answered question that should
have escalated.

### `acl-all-company-about` — «Группа ПОЛИПЛАСТИК» — производитель полимерных трубопроводных систем в России и странах СНГ.

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/about, company/quality-ecology, company/anti-corruption, finance/counterparty-check
- context: -

```
<no answer>
```

### `acl-all-company-anti-corruption` — Зачем нужна политика

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/anti-corruption, company/code-of-conduct, company/org-structure, finance/counterparty-check, company/media-requests
- context: -

```
<no answer>
```

### `acl-all-company-code-of-conduct` — Кодекс делового поведения

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/code-of-conduct, company/anti-corruption, company/commercial-secret
- context: -

```
<no answer>
```

### `acl-all-company-commercial-secret` — Какие данные считаются закрытыми

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/commercial-secret, company/personal-data, it/security, company/anti-corruption
- context: -

```
<no answer>
```

### `acl-all-company-media-requests` — Общение с прессой

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/media-requests, company/trademark-use, company/speak-up, it/email-quota, company/org-structure
- context: -

```
<no answer>
```

### `acl-all-company-org-structure` — Контакты и подразделения

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/org-structure, hr/onboarding-first-day, it/access-and-equipment, company/speak-up, it/email-quota
- context: -

```
<no answer>
```

### `acl-all-company-personal-data` — Персональные данные сотрудника

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/personal-data, hr/personal-file, company/workspace-rules, company/org-structure, hr/payroll
- context: -

```
<no answer>
```

### `acl-all-company-quality-ecology` — Повышать качество жизни людей и эффективность экономики, создавая надёжную и безопасную

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/quality-ecology, company/about, company/org-structure, company/speak-up, hr/remote-work
- context: -

```
<no answer>
```

### `acl-all-company-speak-up` — Горячая линия и сообщения о нарушениях

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/speak-up, company/org-structure, it/security, company/anti-corruption
- context: -

```
<no answer>
```

### `acl-all-company-trademark-use` — Использование бренда и логотипа

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/trademark-use, company/commercial-secret, procurement/purchase-request, it/office-network, hr/expenses
- context: -

```
<no answer>
```

### `acl-all-company-workspace-rules` — Рабочее место освобождается по окончании дня: бумаги с персональными данными не остаются на

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/workspace-rules, hr/personal-file, hr/exit, company/personal-data, it/account-lifecycle
- context: -

```
<no answer>
```

### `acl-all-finance-budget-request` — Бюджет и заявка на расходы

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: finance/budget-request, hr/training-budget, procurement/purchase-request, company/org-structure, hr/expenses
- context: -

```
<no answer>
```

### `acl-all-finance-counterparty-check` — Проверка контрагента перед сделкой

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: finance/counterparty-check, company/anti-corruption, procurement/supplier-onboarding, procurement/purchase-request
- context: -

```
<no answer>
```

### `acl-all-finance-invoice-processing` — Счёт передаётся в бухгалтерию с подписью руководителя и ссылкой на заявку. Счёт без основания

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: finance/invoice-processing, finance/budget-request, hr/business-trip, procurement/purchase-request, hr/expenses
- context: -

```
<no answer>
```

### `acl-all-hr-attestation` — Аттестация проводится ежегодно, с февраля по март. Сотрудники, работающие меньше шести месяцев,

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/attestation, hr/probation, hr/training-budget, it/account-lifecycle, hr/study-leave
- context: -

```
<no answer>
```

### `acl-all-hr-benefits-dms` — ДМС и льготы

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/benefits-dms, company/org-structure, hr/expenses, hr/business-trip
- context: -

```
<no answer>
```

### `acl-all-hr-benefits-meals` — Питание в офисе

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/benefits-meals, company/workspace-rules, hr/remote-work, company/org-structure, company/code-of-conduct
- context: -

```
<no answer>
```

### `acl-all-hr-business-trip` — Когда нужна командировка

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/business-trip, hr/sick-leave-notification, hr/remote-work, hr/expenses, hr/probation
- context: -

```
<no answer>
```

### `acl-all-hr-dismissal-agreement` — Расторжение по соглашению сторон

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/dismissal-agreement, procurement/purchase-request, company/trademark-use, hr/exit, company/org-structure
- context: -

```
<no answer>
```

### `acl-all-hr-donor-day` — За каждый день сдачи крови сотрудник получает два оплачиваемых дня отдыха: день сдачи и один

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/donor-day, hr/overtime, hr/benefits-meals, hr/payroll, hr/maternity-leave
- context: -

```
<no answer>
```

### `acl-all-hr-exit` — Увольнение и обходной лист

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/exit, it/account-lifecycle, security/badge-access, hr/leave-policy, company/workspace-rules
- context: -

```
<no answer>
```

### `acl-all-hr-expenses` — Компания возмещает расходы, понесённые в интересах компании и согласованные заранее:

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/expenses, hr/relocation, hr/training-budget, hr/benefits-meals, hr/business-trip
- context: -

```
<no answer>
```

### `acl-all-hr-internal-transfer` — Перевод внутри компании

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/internal-transfer, hr/payroll, company/org-structure, hr/expenses, finance/invoice-processing
- context: -

```
<no answer>
```

### `acl-all-hr-leave-policy-2025` — Отпуска и отгулы (редакция 2025)

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/leave-policy, hr/leave-schedule, hr/payroll, hr/unpaid-leave, hr/study-leave
- context: -

```
<no answer>
```

### `acl-all-hr-leave-policy` — Отпуска и отгулы

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/leave-policy, company/org-structure, hr/payroll, hr/unpaid-leave, hr/donor-day
- context: -

```
<no answer>
```

### `acl-all-hr-leave-schedule` — График отпусков на следующий календарный год утверждается до 17 декабря текущего года. Проект

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/leave-schedule, hr/leave-policy, hr/payroll, hr/unpaid-leave, hr/maternity-leave
- context: -

```
<no answer>
```

### `acl-all-hr-maternity-leave` — Отпуск по беременности и родам, уход за ребёнком

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/maternity-leave, hr/leave-policy, hr/part-time, hr/unpaid-leave, hr/study-leave
- context: -

```
<no answer>
```

### `acl-all-hr-night-pay` — Доплата за ночную работу

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/night-pay, hr/overtime, hr/payroll, hr/donor-day, hr/benefits-meals
- context: -

```
<no answer>
```

### `acl-all-hr-onboarding-first-day` — Первый рабочий день

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/onboarding-first-day, hr/sick-leave-notification, it/account-lifecycle, hr/remote-work, hr/leave-policy
- context: -

```
<no answer>
```

### `acl-all-hr-overtime` — Переработки и работа в выходные

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/overtime, hr/night-pay, hr/leave-policy, hr/payroll, hr/part-time
- context: -

```
<no answer>
```

### `acl-all-hr-part-time` — Неполный день или неделя оформляются по согласованию с руководителем: после отпуска по уходу за

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/part-time, hr/maternity-leave, hr/leave-policy, hr/unpaid-leave, hr/remote-work
- context: -

```
<no answer>
```

### `acl-all-hr-payroll` — Заработная плата и выплаты

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/payroll, company/org-structure, finance/invoice-processing, hr/sick-leave-pay, hr/benefits-meals
- context: -

```
<no answer>
```

### `acl-all-hr-personal-file` — Личное дело сотрудника

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/personal-file, it/email-quota, hr/unpaid-leave, company/org-structure, company/personal-data
- context: -

```
<no answer>
```

### `acl-all-hr-probation` — Испытательный срок и наставник

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/probation, hr/remote-work, hr/internal-transfer, hr/onboarding-first-day, it/account-lifecycle
- context: -

```
<no answer>
```

### `acl-all-hr-referral` — Как это работает

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/referral, hr/remote-work, it/account-lifecycle, hr/onboarding-first-day, company/workspace-rules
- context: -

```
<no answer>
```

### `acl-all-hr-relocation` — Релокация и переезд

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/relocation, company/workspace-rules, it/account-lifecycle, hr/internal-transfer, hr/business-trip
- context: -

```
<no answer>
```

### `acl-all-hr-remote-work` — Удалённая работа и гибридный график

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/remote-work, company/org-structure, it/account-lifecycle, it/vpn-setup
- context: -

```
<no answer>
```

### `acl-all-hr-salary-bands` — Грейды и вилки окладов

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/payroll, company/org-structure, hr/referral, hr/benefits-meals, hr/expenses
- context: -

```
<no answer>
```

### `acl-all-hr-sick-leave-notification` — Как сообщить о больничном

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/sick-leave-notification, hr/business-trip, hr/sick-leave-pay, hr/leave-policy, hr/payroll
- context: -

```
<no answer>
```

### `acl-all-hr-sick-leave-pay` — Пособие рассчитывается по среднему заработку за два календарных года, предшествующих году

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/sick-leave-pay, hr/payroll, hr/donor-day, hr/maternity-leave, hr/benefits-dms
- context: -

```
<no answer>
```

### `acl-all-hr-sick-leave` — Больничные: внутренняя инструкция для HR

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/sick-leave-notification, company/org-structure, hr/business-trip, hr/sick-leave-pay, hr/payroll
- context: -

```
<no answer>
```

### `acl-all-hr-study-leave` — Сотрудникам, которые впервые получают образование соответствующего уровня в организации с

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/study-leave, hr/onboarding-first-day, hr/training-budget, hr/probation, hr/referral
- context: -

```
<no answer>
```

### `acl-all-hr-training-budget` — Обучение и компенсация курсов

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/training-budget, hr/study-leave, hr/expenses, hr/probation, it/software-licenses
- context: -

```
<no answer>
```

### `acl-all-hr-unpaid-leave` — Отпуск без сохранения заработной платы

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/unpaid-leave, hr/leave-policy, hr/study-leave, hr/part-time
- context: -

```
<no answer>
```

### `acl-all-it-access-and-equipment` — Доступы и оборудование

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/access-and-equipment, hr/onboarding-first-day, company/org-structure, hr/remote-work, hr/exit
- context: -

```
<no answer>
```

### `acl-all-it-account-lifecycle` — Учётные записи и блокировка доступов

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/account-lifecycle, it/password-reset, hr/exit, company/org-structure, it/access-and-equipment
- context: -

```
<no answer>
```

### `acl-all-it-backup-policy` — Резервные копии и восстановление

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/backup-policy, it/hardware-repair, it/email-quota, it/security, company/org-structure
- context: -

```
<no answer>
```

### `acl-all-it-email-quota` — Почтовый ящик и архивы

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/email-quota, company/org-structure, it/security, it/backup-policy, hr/personal-file
- context: -

```
<no answer>
```

### `acl-all-it-hardware-repair` — Ремонт техники и подменный ноутбук

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/hardware-repair, it/access-and-equipment, it/vpn-setup, it/backup-policy
- context: -

```
<no answer>
```

### `acl-all-it-incident-runbook` — Регламент дежурства в ИТ

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/access-and-equipment, company/org-structure, hr/remote-work, it/security, hr/onboarding-first-day
- context: -

```
<no answer>
```

### `acl-all-it-office-network` — Сеть, печать и гостевой Wi-Fi

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/office-network, it/access-and-equipment, company/workspace-rules, it/vpn-setup, it/account-lifecycle
- context: -

```
<no answer>
```

### `acl-all-it-password-reset` — Сброс пароля и блокировка учётной записи

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/password-reset, it/account-lifecycle, it/security, company/org-structure, it/email-quota
- context: -

```
<no answer>
```

### `acl-all-it-security` — Минимальная длина пароля — 12 символов. Пароли нельзя повторять в личных сервисах, передавать

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/security, it/password-reset, it/account-lifecycle, it/vpn-setup
- context: -

```
<no answer>
```

### `acl-all-it-software-licenses` — Программное обеспечение и лицензии

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/software-licenses, it/access-and-equipment, company/org-structure, it/backup-policy
- context: -

```
<no answer>
```

### `acl-all-it-vpn-setup` — Подключение к VPN

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/vpn-setup, it/office-network, it/access-and-equipment, hr/remote-work
- context: -

```
<no answer>
```

### `acl-all-procurement-purchase-request` — Заявка на закупку

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/purchase-request, it/software-licenses, company/org-structure, finance/budget-request, procurement/supplier-onboarding
- context: -

```
<no answer>
```

### `acl-all-procurement-supplier-onboarding` — Поставщик заполняет анкету: реквизиты, виды продукции, опыт работы, производственные мощности.

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/supplier-onboarding, procurement/purchase-request, company/anti-corruption, finance/counterparty-check, procurement/tender-rules
- context: -

```
<no answer>
```

### `acl-all-procurement-tender-rules` — Тендеры на закупку

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/tender-rules, procurement/purchase-request, procurement/supplier-onboarding, company/anti-corruption, it/software-licenses
- context: -

```
<no answer>
```

### `acl-all-production-equipment-maintenance` — Материал для производственных подразделений.

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/quality-ecology, company/commercial-secret, company/org-structure, company/about, production/quality-control
- context: -

```
<no answer>
```

### `acl-all-production-quality-control` — Контроль качества продукции

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: production/quality-control, company/anti-corruption, procurement/supplier-onboarding, procurement/purchase-request, finance/counterparty-check
- context: -

```
<no answer>
```

### `acl-all-production-safety-briefing` — Инструктажи по охране труда

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/onboarding-first-day, security/badge-access, it/security, hr/probation, company/org-structure
- context: -

```
<no answer>
```

### `acl-all-production-shift-schedule` — Материал для производственных подразделений.

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/quality-ecology, company/commercial-secret, company/org-structure, company/about, production/quality-control
- context: -

```
<no answer>
```

### `acl-all-sales-contract-approval` — Материал для подразделения продаж.

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/commercial-secret, company/org-structure, procurement/purchase-request, finance/budget-request, hr/expenses
- context: -

```
<no answer>
```

### `acl-all-sales-crm-rules` — Работа в CRM

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/org-structure, it/account-lifecycle, hr/remote-work, it/email-quota, it/access-and-equipment
- context: -

```
<no answer>
```

### `acl-all-sales-customer-claims` — Претензии и рекламации клиентов

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/purchase-request, company/org-structure, company/anti-corruption, company/trademark-use, hr/expenses
- context: -

```
<no answer>
```

### `acl-all-sales-kp-rules` — Коммерческое предложение: правила оформления

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/supplier-onboarding, procurement/purchase-request, company/anti-corruption, company/trademark-use, company/code-of-conduct
- context: -

```
<no answer>
```

### `acl-all-sales-pricing-approval` — Материал для подразделения продаж.

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/commercial-secret, company/org-structure, procurement/purchase-request, finance/budget-request, hr/expenses
- context: -

```
<no answer>
```

### `acl-all-sales-tender-participation` — Участие в тендерах клиентов

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/tender-rules, procurement/purchase-request, procurement/supplier-onboarding, company/anti-corruption, finance/counterparty-check
- context: -

```
<no answer>
```

### `acl-all-security-badge-access` — Пропуска и физический доступ

- stratum: `acl`
- audience: `all`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: security/badge-access, it/account-lifecycle, it/access-and-equipment, it/security, company/workspace-rules
- context: -

```
<no answer>
```

### `acl-hr_only-company-about` — «Группа ПОЛИПЛАСТИК» — производитель полимерных трубопроводных систем в России и странах СНГ.

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/about, company/quality-ecology, company/anti-corruption, finance/counterparty-check
- context: -

```
<no answer>
```

### `acl-hr_only-company-anti-corruption` — Зачем нужна политика

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/anti-corruption, company/code-of-conduct, company/org-structure, finance/counterparty-check, company/media-requests
- context: -

```
<no answer>
```

### `acl-hr_only-company-code-of-conduct` — Кодекс делового поведения

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/code-of-conduct, hr/salary-bands, company/anti-corruption
- context: -

```
<no answer>
```

### `acl-hr_only-company-commercial-secret` — Какие данные считаются закрытыми

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/commercial-secret, company/personal-data, it/security, company/anti-corruption
- context: -

```
<no answer>
```

### `acl-hr_only-company-media-requests` — Общение с прессой

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/media-requests, company/trademark-use, company/speak-up, company/org-structure, company/workspace-rules
- context: -

```
<no answer>
```

### `acl-hr_only-company-org-structure` — Контакты и подразделения

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/org-structure, hr/onboarding-first-day, it/access-and-equipment, company/speak-up, it/email-quota
- context: -

```
<no answer>
```

### `acl-hr_only-company-personal-data` — Персональные данные сотрудника

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/personal-data, hr/personal-file, company/workspace-rules, company/org-structure, hr/payroll
- context: -

```
<no answer>
```

### `acl-hr_only-company-quality-ecology` — Повышать качество жизни людей и эффективность экономики, создавая надёжную и безопасную

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/quality-ecology, company/about, company/org-structure, company/speak-up, hr/remote-work
- context: -

```
<no answer>
```

### `acl-hr_only-company-speak-up` — Горячая линия и сообщения о нарушениях

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/speak-up, company/org-structure, it/security, company/anti-corruption
- context: -

```
<no answer>
```

### `acl-hr_only-company-trademark-use` — Использование бренда и логотипа

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/trademark-use, company/commercial-secret, procurement/purchase-request, it/office-network, hr/expenses
- context: -

```
<no answer>
```

### `acl-hr_only-company-workspace-rules` — Рабочее место освобождается по окончании дня: бумаги с персональными данными не остаются на

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/workspace-rules, hr/personal-file, hr/exit, company/personal-data, it/account-lifecycle
- context: -

```
<no answer>
```

### `acl-hr_only-finance-budget-request` — Бюджет и заявка на расходы

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: finance/budget-request, hr/training-budget, procurement/purchase-request, company/org-structure, hr/expenses
- context: -

```
<no answer>
```

### `acl-hr_only-finance-counterparty-check` — Проверка контрагента перед сделкой

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: finance/counterparty-check, company/anti-corruption, procurement/supplier-onboarding, procurement/purchase-request
- context: -

```
<no answer>
```

### `acl-hr_only-finance-invoice-processing` — Счёт передаётся в бухгалтерию с подписью руководителя и ссылкой на заявку. Счёт без основания

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: finance/invoice-processing, finance/budget-request, hr/business-trip, procurement/purchase-request, hr/expenses
- context: -

```
<no answer>
```

### `acl-hr_only-hr-attestation` — Аттестация проводится ежегодно, с февраля по март. Сотрудники, работающие меньше шести месяцев,

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/attestation, hr/probation, hr/training-budget, it/account-lifecycle, hr/salary-bands
- context: -

```
<no answer>
```

### `acl-hr_only-hr-benefits-dms` — ДМС и льготы

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/benefits-dms, hr/expenses, company/org-structure, hr/sick-leave
- context: -

```
<no answer>
```

### `acl-hr_only-hr-benefits-meals` — Питание в офисе

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/benefits-meals, company/workspace-rules, company/org-structure, hr/remote-work, company/code-of-conduct
- context: -

```
<no answer>
```

### `acl-hr_only-hr-business-trip` — Когда нужна командировка

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/business-trip, hr/sick-leave-notification, hr/remote-work, hr/expenses, hr/probation
- context: -

```
<no answer>
```

### `acl-hr_only-hr-dismissal-agreement` — Расторжение по соглашению сторон

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/dismissal-agreement, procurement/purchase-request, company/trademark-use, hr/exit, company/org-structure
- context: -

```
<no answer>
```

### `acl-hr_only-hr-donor-day` — За каждый день сдачи крови сотрудник получает два оплачиваемых дня отдыха: день сдачи и один

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/donor-day, hr/overtime, hr/benefits-meals, hr/payroll, hr/maternity-leave
- context: -

```
<no answer>
```

### `acl-hr_only-hr-exit` — Увольнение и обходной лист

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/exit, it/account-lifecycle, security/badge-access, hr/leave-policy, company/workspace-rules
- context: -

```
<no answer>
```

### `acl-hr_only-hr-expenses` — Компания возмещает расходы, понесённые в интересах компании и согласованные заранее:

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/expenses, hr/relocation, hr/training-budget, hr/business-trip, hr/benefits-meals
- context: -

```
<no answer>
```

### `acl-hr_only-hr-internal-transfer` — Перевод внутри компании

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/internal-transfer, hr/payroll, company/org-structure, hr/expenses, it/account-lifecycle
- context: -

```
<no answer>
```

### `acl-hr_only-hr-leave-policy-2025` — Отпуска и отгулы (редакция 2025)

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/leave-policy, hr/leave-schedule, hr/payroll, hr/unpaid-leave, hr/study-leave
- context: -

```
<no answer>
```

### `acl-hr_only-hr-leave-policy` — Отпуска и отгулы

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/leave-policy, company/org-structure, hr/payroll, hr/unpaid-leave, hr/donor-day
- context: -

```
<no answer>
```

### `acl-hr_only-hr-leave-schedule` — График отпусков на следующий календарный год утверждается до 17 декабря текущего года. Проект

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/leave-schedule, hr/leave-policy, hr/payroll, hr/unpaid-leave, hr/maternity-leave
- context: -

```
<no answer>
```

### `acl-hr_only-hr-maternity-leave` — Отпуск по беременности и родам, уход за ребёнком

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/maternity-leave, hr/leave-policy, hr/part-time, hr/unpaid-leave, hr/study-leave
- context: -

```
<no answer>
```

### `acl-hr_only-hr-night-pay` — Доплата за ночную работу

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/night-pay, hr/overtime, hr/payroll, hr/donor-day, hr/benefits-meals
- context: -

```
<no answer>
```

### `acl-hr_only-hr-onboarding-first-day` — Первый рабочий день

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/onboarding-first-day, hr/sick-leave-notification, it/account-lifecycle, hr/remote-work, hr/leave-policy
- context: -

```
<no answer>
```

### `acl-hr_only-hr-overtime` — Переработки и работа в выходные

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/overtime, hr/night-pay, hr/leave-policy, hr/payroll, hr/remote-work
- context: -

```
<no answer>
```

### `acl-hr_only-hr-part-time` — Неполный день или неделя оформляются по согласованию с руководителем: после отпуска по уходу за

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/part-time, hr/maternity-leave, hr/leave-policy, hr/unpaid-leave, hr/remote-work
- context: -

```
<no answer>
```

### `acl-hr_only-hr-payroll` — Заработная плата и выплаты

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/payroll, company/org-structure, finance/invoice-processing, hr/sick-leave-pay, hr/sick-leave
- context: -

```
<no answer>
```

### `acl-hr_only-hr-personal-file` — Личное дело сотрудника

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/personal-file, it/email-quota, hr/unpaid-leave, company/org-structure, company/personal-data
- context: -

```
<no answer>
```

### `acl-hr_only-hr-probation` — Испытательный срок и наставник

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/probation, hr/remote-work, hr/internal-transfer, hr/onboarding-first-day, it/account-lifecycle
- context: -

```
<no answer>
```

### `acl-hr_only-hr-referral` — Как это работает

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/referral, hr/remote-work, it/account-lifecycle, hr/onboarding-first-day, company/workspace-rules
- context: -

```
<no answer>
```

### `acl-hr_only-hr-relocation` — Релокация и переезд

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/relocation, company/workspace-rules, it/account-lifecycle, hr/internal-transfer, hr/business-trip
- context: -

```
<no answer>
```

### `acl-hr_only-hr-remote-work` — Удалённая работа и гибридный график

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/remote-work, company/org-structure, it/account-lifecycle, it/vpn-setup
- context: -

```
<no answer>
```

### `acl-hr_only-hr-salary-bands` — Грейды и вилки окладов

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/salary-bands, hr/payroll, company/org-structure, hr/referral, hr/benefits-meals
- context: -

```
<no answer>
```

### `acl-hr_only-hr-sick-leave-notification` — Как сообщить о больничном

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/sick-leave-notification, hr/business-trip, hr/sick-leave, hr/sick-leave-pay, hr/leave-policy
- context: -

```
<no answer>
```

### `acl-hr_only-hr-sick-leave-pay` — Пособие рассчитывается по среднему заработку за два календарных года, предшествующих году

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/sick-leave-pay, hr/sick-leave, hr/payroll, hr/donor-day, hr/maternity-leave
- context: -

```
<no answer>
```

### `acl-hr_only-hr-sick-leave` — Больничные: внутренняя инструкция для HR

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/sick-leave, hr/sick-leave-notification, company/org-structure, hr/business-trip, hr/sick-leave-pay
- context: -

```
<no answer>
```

### `acl-hr_only-hr-study-leave` — Сотрудникам, которые впервые получают образование соответствующего уровня в организации с

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/study-leave, hr/onboarding-first-day, hr/training-budget, hr/probation, hr/referral
- context: -

```
<no answer>
```

### `acl-hr_only-hr-training-budget` — Обучение и компенсация курсов

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/training-budget, hr/study-leave, hr/expenses, hr/probation, it/software-licenses
- context: -

```
<no answer>
```

### `acl-hr_only-hr-unpaid-leave` — Отпуск без сохранения заработной платы

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/unpaid-leave, hr/leave-policy, hr/study-leave, hr/part-time
- context: -

```
<no answer>
```

### `acl-hr_only-it-access-and-equipment` — Доступы и оборудование

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/access-and-equipment, hr/onboarding-first-day, company/org-structure, hr/remote-work, hr/exit
- context: -

```
<no answer>
```

### `acl-hr_only-it-account-lifecycle` — Учётные записи и блокировка доступов

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/account-lifecycle, it/password-reset, hr/exit, company/org-structure, it/security
- context: -

```
<no answer>
```

### `acl-hr_only-it-backup-policy` — Резервные копии и восстановление

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/backup-policy, it/hardware-repair, it/email-quota, it/security, company/org-structure
- context: -

```
<no answer>
```

### `acl-hr_only-it-email-quota` — Почтовый ящик и архивы

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/email-quota, company/org-structure, it/security, it/backup-policy, hr/personal-file
- context: -

```
<no answer>
```

### `acl-hr_only-it-hardware-repair` — Ремонт техники и подменный ноутбук

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/hardware-repair, it/access-and-equipment, it/vpn-setup, it/backup-policy
- context: -

```
<no answer>
```

### `acl-hr_only-it-incident-runbook` — Регламент дежурства в ИТ

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/access-and-equipment, company/org-structure, hr/remote-work, it/security, hr/onboarding-first-day
- context: -

```
<no answer>
```

### `acl-hr_only-it-office-network` — Сеть, печать и гостевой Wi-Fi

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/office-network, it/access-and-equipment, company/workspace-rules, it/vpn-setup, it/account-lifecycle
- context: -

```
<no answer>
```

### `acl-hr_only-it-password-reset` — Сброс пароля и блокировка учётной записи

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/password-reset, it/account-lifecycle, it/security, company/org-structure, it/email-quota
- context: -

```
<no answer>
```

### `acl-hr_only-it-security` — Минимальная длина пароля — 12 символов. Пароли нельзя повторять в личных сервисах, передавать

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/security, it/password-reset, it/account-lifecycle, it/vpn-setup
- context: -

```
<no answer>
```

### `acl-hr_only-it-software-licenses` — Программное обеспечение и лицензии

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/software-licenses, it/access-and-equipment, company/org-structure, it/backup-policy
- context: -

```
<no answer>
```

### `acl-hr_only-it-vpn-setup` — Подключение к VPN

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/vpn-setup, it/office-network, it/access-and-equipment, hr/remote-work
- context: -

```
<no answer>
```

### `acl-hr_only-procurement-purchase-request` — Заявка на закупку

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/purchase-request, it/software-licenses, company/org-structure, finance/budget-request, procurement/supplier-onboarding
- context: -

```
<no answer>
```

### `acl-hr_only-procurement-supplier-onboarding` — Поставщик заполняет анкету: реквизиты, виды продукции, опыт работы, производственные мощности.

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/supplier-onboarding, procurement/purchase-request, company/anti-corruption, finance/counterparty-check, procurement/tender-rules
- context: -

```
<no answer>
```

### `acl-hr_only-procurement-tender-rules` — Тендеры на закупку

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/tender-rules, procurement/purchase-request, procurement/supplier-onboarding, company/anti-corruption, it/software-licenses
- context: -

```
<no answer>
```

### `acl-hr_only-production-equipment-maintenance` — Материал для производственных подразделений.

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/quality-ecology, company/commercial-secret, company/org-structure, company/about, production/quality-control
- context: -

```
<no answer>
```

### `acl-hr_only-production-quality-control` — Контроль качества продукции

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: production/quality-control, company/anti-corruption, procurement/supplier-onboarding, procurement/purchase-request, finance/counterparty-check
- context: -

```
<no answer>
```

### `acl-hr_only-production-safety-briefing` — Инструктажи по охране труда

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/onboarding-first-day, security/badge-access, it/security, hr/probation, hr/sick-leave
- context: -

```
<no answer>
```

### `acl-hr_only-production-shift-schedule` — Материал для производственных подразделений.

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/quality-ecology, company/commercial-secret, company/org-structure, company/about, production/quality-control
- context: -

```
<no answer>
```

### `acl-hr_only-sales-contract-approval` — Материал для подразделения продаж.

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/commercial-secret, company/org-structure, procurement/purchase-request, finance/budget-request, hr/expenses
- context: -

```
<no answer>
```

### `acl-hr_only-sales-crm-rules` — Работа в CRM

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/org-structure, it/account-lifecycle, hr/remote-work, it/email-quota, it/access-and-equipment
- context: -

```
<no answer>
```

### `acl-hr_only-sales-customer-claims` — Претензии и рекламации клиентов

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/purchase-request, company/org-structure, company/anti-corruption, company/trademark-use, hr/expenses
- context: -

```
<no answer>
```

### `acl-hr_only-sales-kp-rules` — Коммерческое предложение: правила оформления

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/supplier-onboarding, procurement/purchase-request, company/anti-corruption, company/trademark-use, company/code-of-conduct
- context: -

```
<no answer>
```

### `acl-hr_only-sales-pricing-approval` — Материал для подразделения продаж.

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/commercial-secret, company/org-structure, procurement/purchase-request, finance/budget-request, hr/expenses
- context: -

```
<no answer>
```

### `acl-hr_only-sales-tender-participation` — Участие в тендерах клиентов

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/tender-rules, procurement/purchase-request, procurement/supplier-onboarding, company/anti-corruption, finance/counterparty-check
- context: -

```
<no answer>
```

### `acl-hr_only-security-badge-access` — Пропуска и физический доступ

- stratum: `acl`
- audience: `hr_only`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: security/badge-access, it/account-lifecycle, it/access-and-equipment, it/security, it/office-network
- context: -

```
<no answer>
```

### `acl-dept-it-company-about` — «Группа ПОЛИПЛАСТИК» — производитель полимерных трубопроводных систем в России и странах СНГ.

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/about, company/quality-ecology, company/anti-corruption, finance/counterparty-check
- context: -

```
<no answer>
```

### `acl-dept-it-company-anti-corruption` — Зачем нужна политика

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/anti-corruption, company/code-of-conduct, company/org-structure, finance/counterparty-check, company/media-requests
- context: -

```
<no answer>
```

### `acl-dept-it-company-code-of-conduct` — Кодекс делового поведения

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/code-of-conduct, company/anti-corruption, company/commercial-secret
- context: -

```
<no answer>
```

### `acl-dept-it-company-commercial-secret` — Какие данные считаются закрытыми

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/commercial-secret, company/personal-data, it/security, company/anti-corruption
- context: -

```
<no answer>
```

### `acl-dept-it-company-media-requests` — Общение с прессой

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/media-requests, company/trademark-use, company/speak-up, company/org-structure, company/workspace-rules
- context: -

```
<no answer>
```

### `acl-dept-it-company-org-structure` — Контакты и подразделения

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/org-structure, hr/onboarding-first-day, it/access-and-equipment, company/speak-up, company/workspace-rules
- context: -

```
<no answer>
```

### `acl-dept-it-company-personal-data` — Персональные данные сотрудника

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/personal-data, hr/personal-file, company/workspace-rules, company/org-structure, hr/payroll
- context: -

```
<no answer>
```

### `acl-dept-it-company-quality-ecology` — Повышать качество жизни людей и эффективность экономики, создавая надёжную и безопасную

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/quality-ecology, company/about, company/org-structure, company/speak-up, hr/remote-work
- context: -

```
<no answer>
```

### `acl-dept-it-company-speak-up` — Горячая линия и сообщения о нарушениях

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/speak-up, company/org-structure, it/security, company/anti-corruption
- context: -

```
<no answer>
```

### `acl-dept-it-company-trademark-use` — Использование бренда и логотипа

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/trademark-use, company/commercial-secret, procurement/purchase-request, it/office-network, hr/expenses
- context: -

```
<no answer>
```

### `acl-dept-it-company-workspace-rules` — Рабочее место освобождается по окончании дня: бумаги с персональными данными не остаются на

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/workspace-rules, hr/personal-file, hr/exit, company/personal-data, it/account-lifecycle
- context: -

```
<no answer>
```

### `acl-dept-it-finance-budget-request` — Бюджет и заявка на расходы

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: finance/budget-request, hr/training-budget, procurement/purchase-request, company/org-structure, hr/expenses
- context: -

```
<no answer>
```

### `acl-dept-it-finance-counterparty-check` — Проверка контрагента перед сделкой

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: finance/counterparty-check, company/anti-corruption, procurement/supplier-onboarding, procurement/purchase-request
- context: -

```
<no answer>
```

### `acl-dept-it-finance-invoice-processing` — Счёт передаётся в бухгалтерию с подписью руководителя и ссылкой на заявку. Счёт без основания

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: finance/invoice-processing, finance/budget-request, hr/business-trip, procurement/purchase-request, hr/expenses
- context: -

```
<no answer>
```

### `acl-dept-it-hr-attestation` — Аттестация проводится ежегодно, с февраля по март. Сотрудники, работающие меньше шести месяцев,

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/attestation, hr/probation, hr/training-budget, it/account-lifecycle, company/personal-data
- context: -

```
<no answer>
```

### `acl-dept-it-hr-benefits-dms` — ДМС и льготы

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/benefits-dms, company/org-structure, hr/expenses, hr/business-trip
- context: -

```
<no answer>
```

### `acl-dept-it-hr-benefits-meals` — Питание в офисе

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/benefits-meals, company/workspace-rules, hr/remote-work, company/org-structure, company/code-of-conduct
- context: -

```
<no answer>
```

### `acl-dept-it-hr-business-trip` — Когда нужна командировка

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/business-trip, hr/sick-leave-notification, hr/remote-work, hr/expenses, hr/probation
- context: -

```
<no answer>
```

### `acl-dept-it-hr-dismissal-agreement` — Расторжение по соглашению сторон

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/dismissal-agreement, procurement/purchase-request, company/trademark-use, company/org-structure, hr/exit
- context: -

```
<no answer>
```

### `acl-dept-it-hr-donor-day` — За каждый день сдачи крови сотрудник получает два оплачиваемых дня отдыха: день сдачи и один

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/donor-day, hr/overtime, hr/benefits-meals, hr/payroll, hr/maternity-leave
- context: -

```
<no answer>
```

### `acl-dept-it-hr-exit` — Увольнение и обходной лист

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/exit, it/account-lifecycle, security/badge-access, hr/leave-policy, company/workspace-rules
- context: -

```
<no answer>
```

### `acl-dept-it-hr-expenses` — Компания возмещает расходы, понесённые в интересах компании и согласованные заранее:

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/expenses, hr/relocation, hr/training-budget, hr/benefits-meals, hr/business-trip
- context: -

```
<no answer>
```

### `acl-dept-it-hr-internal-transfer` — Перевод внутри компании

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/internal-transfer, hr/payroll, company/org-structure, hr/expenses, it/account-lifecycle
- context: -

```
<no answer>
```

### `acl-dept-it-hr-leave-policy-2025` — Отпуска и отгулы (редакция 2025)

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/leave-policy, hr/leave-schedule, hr/payroll, hr/unpaid-leave, hr/study-leave
- context: -

```
<no answer>
```

### `acl-dept-it-hr-leave-policy` — Отпуска и отгулы

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/leave-policy, company/org-structure, hr/payroll, hr/unpaid-leave, hr/donor-day
- context: -

```
<no answer>
```

### `acl-dept-it-hr-leave-schedule` — График отпусков на следующий календарный год утверждается до 17 декабря текущего года. Проект

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/leave-schedule, hr/leave-policy, hr/payroll, hr/unpaid-leave, hr/maternity-leave
- context: -

```
<no answer>
```

### `acl-dept-it-hr-maternity-leave` — Отпуск по беременности и родам, уход за ребёнком

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/maternity-leave, hr/leave-policy, hr/part-time, hr/unpaid-leave, hr/study-leave
- context: -

```
<no answer>
```

### `acl-dept-it-hr-night-pay` — Доплата за ночную работу

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/night-pay, hr/overtime, hr/payroll, hr/donor-day, hr/benefits-meals
- context: -

```
<no answer>
```

### `acl-dept-it-hr-onboarding-first-day` — Первый рабочий день

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/onboarding-first-day, hr/sick-leave-notification, it/account-lifecycle, hr/remote-work, hr/leave-policy
- context: -

```
<no answer>
```

### `acl-dept-it-hr-overtime` — Переработки и работа в выходные

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/overtime, hr/night-pay, hr/leave-policy, hr/payroll, hr/part-time
- context: -

```
<no answer>
```

### `acl-dept-it-hr-part-time` — Неполный день или неделя оформляются по согласованию с руководителем: после отпуска по уходу за

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/part-time, hr/maternity-leave, hr/leave-policy, hr/unpaid-leave, hr/remote-work
- context: -

```
<no answer>
```

### `acl-dept-it-hr-payroll` — Заработная плата и выплаты

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/payroll, company/org-structure, finance/invoice-processing, hr/sick-leave-pay, hr/benefits-meals
- context: -

```
<no answer>
```

### `acl-dept-it-hr-personal-file` — Личное дело сотрудника

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/personal-file, it/email-quota, hr/unpaid-leave, company/org-structure, company/personal-data
- context: -

```
<no answer>
```

### `acl-dept-it-hr-probation` — Испытательный срок и наставник

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/probation, hr/remote-work, hr/internal-transfer, hr/onboarding-first-day, it/account-lifecycle
- context: -

```
<no answer>
```

### `acl-dept-it-hr-referral` — Как это работает

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/referral, hr/remote-work, it/account-lifecycle, hr/onboarding-first-day, company/workspace-rules
- context: -

```
<no answer>
```

### `acl-dept-it-hr-relocation` — Релокация и переезд

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/relocation, company/workspace-rules, it/account-lifecycle, hr/internal-transfer, hr/business-trip
- context: -

```
<no answer>
```

### `acl-dept-it-hr-remote-work` — Удалённая работа и гибридный график

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/remote-work, company/org-structure, it/account-lifecycle, it/vpn-setup
- context: -

```
<no answer>
```

### `acl-dept-it-hr-salary-bands` — Грейды и вилки окладов

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/payroll, company/org-structure, hr/referral, hr/benefits-meals, hr/expenses
- context: -

```
<no answer>
```

### `acl-dept-it-hr-sick-leave-notification` — Как сообщить о больничном

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/sick-leave-notification, hr/business-trip, hr/sick-leave-pay, hr/leave-policy, hr/payroll
- context: -

```
<no answer>
```

### `acl-dept-it-hr-sick-leave-pay` — Пособие рассчитывается по среднему заработку за два календарных года, предшествующих году

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/sick-leave-pay, hr/payroll, hr/maternity-leave, hr/donor-day, hr/benefits-dms
- context: -

```
<no answer>
```

### `acl-dept-it-hr-sick-leave` — Больничные: внутренняя инструкция для HR

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/sick-leave-notification, company/org-structure, hr/business-trip, hr/sick-leave-pay, hr/payroll
- context: -

```
<no answer>
```

### `acl-dept-it-hr-study-leave` — Сотрудникам, которые впервые получают образование соответствующего уровня в организации с

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/study-leave, hr/onboarding-first-day, hr/training-budget, hr/probation, hr/referral
- context: -

```
<no answer>
```

### `acl-dept-it-hr-training-budget` — Обучение и компенсация курсов

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/training-budget, hr/study-leave, hr/expenses, hr/probation, it/software-licenses
- context: -

```
<no answer>
```

### `acl-dept-it-hr-unpaid-leave` — Отпуск без сохранения заработной платы

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/unpaid-leave, hr/leave-policy, hr/part-time, hr/study-leave
- context: -

```
<no answer>
```

### `acl-dept-it-it-access-and-equipment` — Доступы и оборудование

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/access-and-equipment, hr/onboarding-first-day, company/org-structure, hr/remote-work, hr/exit
- context: -

```
<no answer>
```

### `acl-dept-it-it-account-lifecycle` — Учётные записи и блокировка доступов

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/account-lifecycle, it/password-reset, hr/exit, company/org-structure, it/access-and-equipment
- context: -

```
<no answer>
```

### `acl-dept-it-it-backup-policy` — Резервные копии и восстановление

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/backup-policy, it/hardware-repair, it/email-quota, it/security, company/org-structure
- context: -

```
<no answer>
```

### `acl-dept-it-it-email-quota` — Почтовый ящик и архивы

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/email-quota, company/org-structure, it/backup-policy, it/security, hr/personal-file
- context: -

```
<no answer>
```

### `acl-dept-it-it-hardware-repair` — Ремонт техники и подменный ноутбук

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/hardware-repair, it/access-and-equipment, it/vpn-setup, it/backup-policy
- context: -

```
<no answer>
```

### `acl-dept-it-it-incident-runbook` — Регламент дежурства в ИТ

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/incident-runbook, it/access-and-equipment, company/org-structure, hr/remote-work, hr/onboarding-first-day
- context: -

```
<no answer>
```

### `acl-dept-it-it-office-network` — Сеть, печать и гостевой Wi-Fi

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/office-network, it/access-and-equipment, company/workspace-rules, it/vpn-setup, it/account-lifecycle
- context: -

```
<no answer>
```

### `acl-dept-it-it-password-reset` — Сброс пароля и блокировка учётной записи

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/password-reset, it/account-lifecycle, it/security, company/org-structure, it/email-quota
- context: -

```
<no answer>
```

### `acl-dept-it-it-security` — Минимальная длина пароля — 12 символов. Пароли нельзя повторять в личных сервисах, передавать

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/security, it/password-reset, it/account-lifecycle, it/vpn-setup
- context: -

```
<no answer>
```

### `acl-dept-it-it-software-licenses` — Программное обеспечение и лицензии

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/software-licenses, it/access-and-equipment, company/org-structure, it/backup-policy
- context: -

```
<no answer>
```

### `acl-dept-it-it-vpn-setup` — Подключение к VPN

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/vpn-setup, it/office-network, it/access-and-equipment, hr/remote-work
- context: -

```
<no answer>
```

### `acl-dept-it-procurement-purchase-request` — Заявка на закупку

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/purchase-request, it/software-licenses, company/org-structure, finance/budget-request, procurement/supplier-onboarding
- context: -

```
<no answer>
```

### `acl-dept-it-procurement-supplier-onboarding` — Поставщик заполняет анкету: реквизиты, виды продукции, опыт работы, производственные мощности.

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/supplier-onboarding, procurement/purchase-request, company/anti-corruption, finance/counterparty-check, procurement/tender-rules
- context: -

```
<no answer>
```

### `acl-dept-it-procurement-tender-rules` — Тендеры на закупку

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/tender-rules, procurement/purchase-request, procurement/supplier-onboarding, company/anti-corruption, it/software-licenses
- context: -

```
<no answer>
```

### `acl-dept-it-production-equipment-maintenance` — Материал для производственных подразделений.

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/quality-ecology, company/commercial-secret, company/org-structure, company/about, production/quality-control
- context: -

```
<no answer>
```

### `acl-dept-it-production-quality-control` — Контроль качества продукции

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: production/quality-control, company/anti-corruption, procurement/supplier-onboarding, procurement/purchase-request, finance/counterparty-check
- context: -

```
<no answer>
```

### `acl-dept-it-production-safety-briefing` — Инструктажи по охране труда

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/onboarding-first-day, security/badge-access, it/security, hr/probation, company/org-structure
- context: -

```
<no answer>
```

### `acl-dept-it-production-shift-schedule` — Материал для производственных подразделений.

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/quality-ecology, company/commercial-secret, company/org-structure, company/about, production/quality-control
- context: -

```
<no answer>
```

### `acl-dept-it-sales-contract-approval` — Материал для подразделения продаж.

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/commercial-secret, company/org-structure, procurement/purchase-request, finance/budget-request, hr/expenses
- context: -

```
<no answer>
```

### `acl-dept-it-sales-crm-rules` — Работа в CRM

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/org-structure, it/account-lifecycle, hr/remote-work, it/email-quota, it/access-and-equipment
- context: -

```
<no answer>
```

### `acl-dept-it-sales-customer-claims` — Претензии и рекламации клиентов

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/purchase-request, company/org-structure, company/anti-corruption, company/trademark-use, hr/expenses
- context: -

```
<no answer>
```

### `acl-dept-it-sales-kp-rules` — Коммерческое предложение: правила оформления

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/supplier-onboarding, procurement/purchase-request, company/anti-corruption, company/trademark-use, company/code-of-conduct
- context: -

```
<no answer>
```

### `acl-dept-it-sales-pricing-approval` — Материал для подразделения продаж.

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/commercial-secret, company/org-structure, procurement/purchase-request, finance/budget-request, hr/expenses
- context: -

```
<no answer>
```

### `acl-dept-it-sales-tender-participation` — Участие в тендерах клиентов

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/tender-rules, procurement/purchase-request, procurement/supplier-onboarding, company/anti-corruption, finance/counterparty-check
- context: -

```
<no answer>
```

### `acl-dept-it-security-badge-access` — Пропуска и физический доступ

- stratum: `acl`
- audience: `dept:it`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: security/badge-access, it/account-lifecycle, it/access-and-equipment, it/security, it/office-network
- context: -

```
<no answer>
```

### `acl-dept-sales-company-about` — «Группа ПОЛИПЛАСТИК» — производитель полимерных трубопроводных систем в России и странах СНГ.

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/about, company/quality-ecology, company/anti-corruption, finance/counterparty-check
- context: -

```
<no answer>
```

### `acl-dept-sales-company-anti-corruption` — Зачем нужна политика

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/anti-corruption, company/code-of-conduct, company/org-structure, finance/counterparty-check, company/media-requests
- context: -

```
<no answer>
```

### `acl-dept-sales-company-code-of-conduct` — Кодекс делового поведения

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/code-of-conduct, company/anti-corruption, sales/kp-rules
- context: -

```
<no answer>
```

### `acl-dept-sales-company-commercial-secret` — Какие данные считаются закрытыми

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/commercial-secret, company/personal-data, it/security, company/anti-corruption
- context: -

```
<no answer>
```

### `acl-dept-sales-company-media-requests` — Общение с прессой

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/media-requests, company/trademark-use, sales/crm-rules, company/speak-up, company/org-structure
- context: -

```
<no answer>
```

### `acl-dept-sales-company-org-structure` — Контакты и подразделения

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/org-structure, hr/onboarding-first-day, sales/crm-rules, it/access-and-equipment, company/speak-up
- context: -

```
<no answer>
```

### `acl-dept-sales-company-personal-data` — Персональные данные сотрудника

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/personal-data, hr/personal-file, company/workspace-rules, company/org-structure, hr/payroll
- context: -

```
<no answer>
```

### `acl-dept-sales-company-quality-ecology` — Повышать качество жизни людей и эффективность экономики, создавая надёжную и безопасную

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/quality-ecology, company/about, company/org-structure, company/speak-up, hr/remote-work
- context: -

```
<no answer>
```

### `acl-dept-sales-company-speak-up` — Горячая линия и сообщения о нарушениях

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/speak-up, company/org-structure, it/security, company/anti-corruption
- context: -

```
<no answer>
```

### `acl-dept-sales-company-trademark-use` — Использование бренда и логотипа

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/trademark-use, sales/kp-rules, sales/contract-approval, sales/pricing-approval, company/commercial-secret
- context: -

```
<no answer>
```

### `acl-dept-sales-company-workspace-rules` — Рабочее место освобождается по окончании дня: бумаги с персональными данными не остаются на

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/workspace-rules, hr/personal-file, hr/exit, company/personal-data, it/account-lifecycle
- context: -

```
<no answer>
```

### `acl-dept-sales-finance-budget-request` — Бюджет и заявка на расходы

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: finance/budget-request, hr/training-budget, procurement/purchase-request, company/org-structure, hr/expenses
- context: -

```
<no answer>
```

### `acl-dept-sales-finance-counterparty-check` — Проверка контрагента перед сделкой

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: finance/counterparty-check, company/anti-corruption, procurement/supplier-onboarding, sales/contract-approval
- context: -

```
<no answer>
```

### `acl-dept-sales-finance-invoice-processing` — Счёт передаётся в бухгалтерию с подписью руководителя и ссылкой на заявку. Счёт без основания

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: finance/invoice-processing, finance/budget-request, hr/business-trip, procurement/purchase-request, sales/contract-approval
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-attestation` — Аттестация проводится ежегодно, с февраля по март. Сотрудники, работающие меньше шести месяцев,

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/attestation, hr/probation, hr/training-budget, it/account-lifecycle, company/personal-data
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-benefits-dms` — ДМС и льготы

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/benefits-dms, company/org-structure, hr/expenses, hr/business-trip
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-benefits-meals` — Питание в офисе

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/benefits-meals, company/workspace-rules, hr/remote-work, company/org-structure, company/code-of-conduct
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-business-trip` — Когда нужна командировка

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/business-trip, hr/sick-leave-notification, hr/expenses, hr/remote-work, hr/exit
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-dismissal-agreement` — Расторжение по соглашению сторон

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/dismissal-agreement, procurement/purchase-request, sales/contract-approval, company/trademark-use, sales/pricing-approval
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-donor-day` — За каждый день сдачи крови сотрудник получает два оплачиваемых дня отдыха: день сдачи и один

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/donor-day, hr/overtime, hr/benefits-meals, hr/payroll, hr/maternity-leave
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-exit` — Увольнение и обходной лист

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/exit, it/account-lifecycle, security/badge-access, hr/leave-policy, company/workspace-rules
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-expenses` — Компания возмещает расходы, понесённые в интересах компании и согласованные заранее:

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/expenses, hr/relocation, hr/training-budget, hr/business-trip, hr/benefits-meals
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-internal-transfer` — Перевод внутри компании

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/internal-transfer, hr/payroll, company/org-structure, hr/expenses, finance/invoice-processing
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-leave-policy-2025` — Отпуска и отгулы (редакция 2025)

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/leave-policy, hr/leave-schedule, hr/payroll, hr/unpaid-leave, hr/study-leave
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-leave-policy` — Отпуска и отгулы

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/leave-policy, company/org-structure, hr/payroll, hr/unpaid-leave, hr/donor-day
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-leave-schedule` — График отпусков на следующий календарный год утверждается до 17 декабря текущего года. Проект

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/leave-schedule, hr/leave-policy, hr/payroll, hr/unpaid-leave, hr/maternity-leave
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-maternity-leave` — Отпуск по беременности и родам, уход за ребёнком

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/maternity-leave, hr/leave-policy, hr/part-time, hr/unpaid-leave, hr/study-leave
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-night-pay` — Доплата за ночную работу

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/night-pay, hr/overtime, hr/payroll, hr/donor-day, hr/benefits-meals
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-onboarding-first-day` — Первый рабочий день

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/onboarding-first-day, hr/sick-leave-notification, it/account-lifecycle, hr/remote-work, sales/crm-rules
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-overtime` — Переработки и работа в выходные

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/overtime, hr/night-pay, hr/payroll, hr/leave-policy, hr/remote-work
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-part-time` — Неполный день или неделя оформляются по согласованию с руководителем: после отпуска по уходу за

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/part-time, hr/maternity-leave, hr/leave-policy, hr/remote-work, hr/unpaid-leave
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-payroll` — Заработная плата и выплаты

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/payroll, company/org-structure, finance/invoice-processing, hr/sick-leave-pay, hr/benefits-meals
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-personal-file` — Личное дело сотрудника

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/personal-file, it/email-quota, hr/unpaid-leave, company/org-structure, company/personal-data
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-probation` — Испытательный срок и наставник

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/probation, hr/remote-work, hr/internal-transfer, hr/onboarding-first-day, it/account-lifecycle
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-referral` — Как это работает

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/referral, hr/remote-work, it/account-lifecycle, hr/onboarding-first-day, company/workspace-rules
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-relocation` — Релокация и переезд

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/relocation, company/workspace-rules, it/account-lifecycle, hr/internal-transfer, hr/business-trip
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-remote-work` — Удалённая работа и гибридный график

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/remote-work, company/org-structure, it/vpn-setup, it/account-lifecycle
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-salary-bands` — Грейды и вилки окладов

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/payroll, company/org-structure, sales/pricing-approval, hr/referral, hr/benefits-meals
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-sick-leave-notification` — Как сообщить о больничном

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/sick-leave-notification, hr/business-trip, hr/sick-leave-pay, hr/leave-policy, hr/payroll
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-sick-leave-pay` — Пособие рассчитывается по среднему заработку за два календарных года, предшествующих году

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/sick-leave-pay, hr/payroll, hr/donor-day, hr/maternity-leave, hr/benefits-dms
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-sick-leave` — Больничные: внутренняя инструкция для HR

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/sick-leave-notification, company/org-structure, hr/business-trip, hr/sick-leave-pay, hr/payroll
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-study-leave` — Сотрудникам, которые впервые получают образование соответствующего уровня в организации с

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/study-leave, hr/onboarding-first-day, hr/training-budget, hr/probation, hr/referral
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-training-budget` — Обучение и компенсация курсов

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/training-budget, hr/study-leave, hr/expenses, hr/probation, sales/kp-rules
- context: -

```
<no answer>
```

### `acl-dept-sales-hr-unpaid-leave` — Отпуск без сохранения заработной платы

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/unpaid-leave, hr/leave-policy, hr/part-time, hr/study-leave
- context: -

```
<no answer>
```

### `acl-dept-sales-it-access-and-equipment` — Доступы и оборудование

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/access-and-equipment, hr/onboarding-first-day, company/org-structure, hr/remote-work, hr/exit
- context: -

```
<no answer>
```

### `acl-dept-sales-it-account-lifecycle` — Учётные записи и блокировка доступов

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/account-lifecycle, it/password-reset, hr/exit, company/org-structure, it/access-and-equipment
- context: -

```
<no answer>
```

### `acl-dept-sales-it-backup-policy` — Резервные копии и восстановление

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/backup-policy, it/hardware-repair, it/email-quota, it/security, company/org-structure
- context: -

```
<no answer>
```

### `acl-dept-sales-it-email-quota` — Почтовый ящик и архивы

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/email-quota, company/org-structure, it/security, it/backup-policy, hr/personal-file
- context: -

```
<no answer>
```

### `acl-dept-sales-it-hardware-repair` — Ремонт техники и подменный ноутбук

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/hardware-repair, it/access-and-equipment, it/vpn-setup, it/backup-policy
- context: -

```
<no answer>
```

### `acl-dept-sales-it-incident-runbook` — Регламент дежурства в ИТ

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/access-and-equipment, company/org-structure, hr/remote-work, hr/onboarding-first-day, it/security
- context: -

```
<no answer>
```

### `acl-dept-sales-it-office-network` — Сеть, печать и гостевой Wi-Fi

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/office-network, it/access-and-equipment, company/workspace-rules, it/vpn-setup, it/account-lifecycle
- context: -

```
<no answer>
```

### `acl-dept-sales-it-password-reset` — Сброс пароля и блокировка учётной записи

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/password-reset, it/account-lifecycle, it/security, company/org-structure, it/email-quota
- context: -

```
<no answer>
```

### `acl-dept-sales-it-security` — Минимальная длина пароля — 12 символов. Пароли нельзя повторять в личных сервисах, передавать

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/security, it/password-reset, it/account-lifecycle, it/vpn-setup
- context: -

```
<no answer>
```

### `acl-dept-sales-it-software-licenses` — Программное обеспечение и лицензии

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/software-licenses, it/access-and-equipment, company/org-structure, it/backup-policy
- context: -

```
<no answer>
```

### `acl-dept-sales-it-vpn-setup` — Подключение к VPN

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/vpn-setup, it/office-network, it/access-and-equipment, hr/remote-work
- context: -

```
<no answer>
```

### `acl-dept-sales-procurement-purchase-request` — Заявка на закупку

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/purchase-request, it/software-licenses, finance/budget-request, company/org-structure, procurement/supplier-onboarding
- context: -

```
<no answer>
```

### `acl-dept-sales-procurement-supplier-onboarding` — Поставщик заполняет анкету: реквизиты, виды продукции, опыт работы, производственные мощности.

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/supplier-onboarding, procurement/purchase-request, sales/kp-rules, company/anti-corruption, finance/counterparty-check
- context: -

```
<no answer>
```

### `acl-dept-sales-procurement-tender-rules` — Тендеры на закупку

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/tender-rules, procurement/purchase-request, sales/tender-participation, procurement/supplier-onboarding, sales/pricing-approval
- context: -

```
<no answer>
```

### `acl-dept-sales-production-equipment-maintenance` — Материал для производственных подразделений.

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/quality-ecology, company/commercial-secret, company/org-structure, company/about, production/quality-control
- context: -

```
<no answer>
```

### `acl-dept-sales-production-quality-control` — Контроль качества продукции

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: production/quality-control, sales/customer-claims, company/anti-corruption, sales/kp-rules, procurement/supplier-onboarding
- context: -

```
<no answer>
```

### `acl-dept-sales-production-safety-briefing` — Инструктажи по охране труда

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/onboarding-first-day, security/badge-access, it/security, hr/probation, company/org-structure
- context: -

```
<no answer>
```

### `acl-dept-sales-production-shift-schedule` — Материал для производственных подразделений.

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/quality-ecology, company/commercial-secret, company/org-structure, company/about, production/quality-control
- context: -

```
<no answer>
```

### `acl-dept-sales-sales-contract-approval` — Материал для подразделения продаж.

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: sales/crm-rules, sales/kp-rules, sales/contract-approval, sales/tender-participation, sales/pricing-approval
- context: -

```
<no answer>
```

### `acl-dept-sales-sales-crm-rules` — Работа в CRM

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: sales/crm-rules, company/org-structure, sales/kp-rules, it/account-lifecycle, sales/pricing-approval
- context: -

```
<no answer>
```

### `acl-dept-sales-sales-customer-claims` — Претензии и рекламации клиентов

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: sales/customer-claims, sales/kp-rules, sales/pricing-approval, procurement/purchase-request, company/org-structure
- context: -

```
<no answer>
```

### `acl-dept-sales-sales-kp-rules` — Коммерческое предложение: правила оформления

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: sales/kp-rules, sales/pricing-approval, procurement/supplier-onboarding, procurement/purchase-request, sales/tender-participation
- context: -

```
<no answer>
```

### `acl-dept-sales-sales-pricing-approval` — Материал для подразделения продаж.

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: sales/crm-rules, sales/kp-rules, sales/contract-approval, sales/tender-participation, sales/pricing-approval
- context: -

```
<no answer>
```

### `acl-dept-sales-sales-tender-participation` — Участие в тендерах клиентов

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: sales/tender-participation, procurement/tender-rules, sales/kp-rules, procurement/purchase-request, sales/pricing-approval
- context: -

```
<no answer>
```

### `acl-dept-sales-security-badge-access` — Пропуска и физический доступ

- stratum: `acl`
- audience: `dept:sales`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: security/badge-access, it/account-lifecycle, it/access-and-equipment, it/security, it/office-network
- context: -

```
<no answer>
```

### `acl-dept-production-company-about` — «Группа ПОЛИПЛАСТИК» — производитель полимерных трубопроводных систем в России и странах СНГ.

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/about, company/quality-ecology, company/anti-corruption, finance/counterparty-check
- context: -

```
<no answer>
```

### `acl-dept-production-company-anti-corruption` — Зачем нужна политика

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/anti-corruption, company/code-of-conduct, company/org-structure, finance/counterparty-check, company/media-requests
- context: -

```
<no answer>
```

### `acl-dept-production-company-code-of-conduct` — Кодекс делового поведения

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/code-of-conduct, company/anti-corruption, company/commercial-secret
- context: -

```
<no answer>
```

### `acl-dept-production-company-commercial-secret` — Какие данные считаются закрытыми

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/commercial-secret, company/personal-data, it/security, company/anti-corruption
- context: -

```
<no answer>
```

### `acl-dept-production-company-media-requests` — Общение с прессой

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/media-requests, company/trademark-use, company/speak-up, company/org-structure, it/email-quota
- context: -

```
<no answer>
```

### `acl-dept-production-company-org-structure` — Контакты и подразделения

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/org-structure, hr/onboarding-first-day, it/access-and-equipment, company/speak-up, company/workspace-rules
- context: -

```
<no answer>
```

### `acl-dept-production-company-personal-data` — Персональные данные сотрудника

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/personal-data, hr/personal-file, company/workspace-rules, company/org-structure, hr/payroll
- context: -

```
<no answer>
```

### `acl-dept-production-company-quality-ecology` — Повышать качество жизни людей и эффективность экономики, создавая надёжную и безопасную

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/quality-ecology, company/about, company/org-structure, company/speak-up, hr/remote-work
- context: -

```
<no answer>
```

### `acl-dept-production-company-speak-up` — Горячая линия и сообщения о нарушениях

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/speak-up, company/org-structure, it/security, company/anti-corruption
- context: -

```
<no answer>
```

### `acl-dept-production-company-trademark-use` — Использование бренда и логотипа

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/trademark-use, company/commercial-secret, procurement/purchase-request, it/office-network, hr/expenses
- context: -

```
<no answer>
```

### `acl-dept-production-company-workspace-rules` — Рабочее место освобождается по окончании дня: бумаги с персональными данными не остаются на

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/workspace-rules, hr/personal-file, hr/exit, company/personal-data, it/account-lifecycle
- context: -

```
<no answer>
```

### `acl-dept-production-finance-budget-request` — Бюджет и заявка на расходы

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: finance/budget-request, hr/training-budget, procurement/purchase-request, company/org-structure, hr/expenses
- context: -

```
<no answer>
```

### `acl-dept-production-finance-counterparty-check` — Проверка контрагента перед сделкой

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: finance/counterparty-check, company/anti-corruption, procurement/supplier-onboarding, procurement/purchase-request
- context: -

```
<no answer>
```

### `acl-dept-production-finance-invoice-processing` — Счёт передаётся в бухгалтерию с подписью руководителя и ссылкой на заявку. Счёт без основания

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: finance/invoice-processing, finance/budget-request, hr/business-trip, procurement/purchase-request, hr/expenses
- context: -

```
<no answer>
```

### `acl-dept-production-hr-attestation` — Аттестация проводится ежегодно, с февраля по март. Сотрудники, работающие меньше шести месяцев,

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/attestation, hr/probation, hr/training-budget, it/account-lifecycle, company/personal-data
- context: -

```
<no answer>
```

### `acl-dept-production-hr-benefits-dms` — ДМС и льготы

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/benefits-dms, company/org-structure, hr/expenses, hr/business-trip
- context: -

```
<no answer>
```

### `acl-dept-production-hr-benefits-meals` — Питание в офисе

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/benefits-meals, company/workspace-rules, hr/remote-work, company/org-structure, company/code-of-conduct
- context: -

```
<no answer>
```

### `acl-dept-production-hr-business-trip` — Когда нужна командировка

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/business-trip, hr/sick-leave-notification, hr/remote-work, hr/expenses, hr/probation
- context: -

```
<no answer>
```

### `acl-dept-production-hr-dismissal-agreement` — Расторжение по соглашению сторон

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/dismissal-agreement, procurement/purchase-request, company/trademark-use, hr/exit, company/org-structure
- context: -

```
<no answer>
```

### `acl-dept-production-hr-donor-day` — За каждый день сдачи крови сотрудник получает два оплачиваемых дня отдыха: день сдачи и один

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/donor-day, hr/overtime, hr/benefits-meals, hr/payroll, hr/maternity-leave
- context: -

```
<no answer>
```

### `acl-dept-production-hr-exit` — Увольнение и обходной лист

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/exit, it/account-lifecycle, security/badge-access, hr/leave-policy, company/workspace-rules
- context: -

```
<no answer>
```

### `acl-dept-production-hr-expenses` — Компания возмещает расходы, понесённые в интересах компании и согласованные заранее:

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/expenses, hr/relocation, hr/training-budget, hr/business-trip, hr/benefits-meals
- context: -

```
<no answer>
```

### `acl-dept-production-hr-internal-transfer` — Перевод внутри компании

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/internal-transfer, hr/payroll, company/org-structure, hr/expenses, finance/invoice-processing
- context: -

```
<no answer>
```

### `acl-dept-production-hr-leave-policy-2025` — Отпуска и отгулы (редакция 2025)

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/leave-policy, hr/leave-schedule, hr/payroll, hr/unpaid-leave, hr/study-leave
- context: -

```
<no answer>
```

### `acl-dept-production-hr-leave-policy` — Отпуска и отгулы

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/leave-policy, company/org-structure, hr/payroll, hr/unpaid-leave, hr/donor-day
- context: -

```
<no answer>
```

### `acl-dept-production-hr-leave-schedule` — График отпусков на следующий календарный год утверждается до 17 декабря текущего года. Проект

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/leave-schedule, hr/leave-policy, hr/payroll, hr/unpaid-leave, hr/maternity-leave
- context: -

```
<no answer>
```

### `acl-dept-production-hr-maternity-leave` — Отпуск по беременности и родам, уход за ребёнком

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/maternity-leave, hr/leave-policy, hr/part-time, hr/unpaid-leave, hr/study-leave
- context: -

```
<no answer>
```

### `acl-dept-production-hr-night-pay` — Доплата за ночную работу

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/night-pay, hr/overtime, hr/payroll, production/shift-schedule, hr/donor-day
- context: -

```
<no answer>
```

### `acl-dept-production-hr-onboarding-first-day` — Первый рабочий день

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/onboarding-first-day, it/account-lifecycle, hr/sick-leave-notification, hr/remote-work, hr/leave-policy
- context: -

```
<no answer>
```

### `acl-dept-production-hr-overtime` — Переработки и работа в выходные

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/overtime, hr/night-pay, production/shift-schedule, hr/leave-policy, hr/payroll
- context: -

```
<no answer>
```

### `acl-dept-production-hr-part-time` — Неполный день или неделя оформляются по согласованию с руководителем: после отпуска по уходу за

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/part-time, hr/maternity-leave, hr/leave-policy, hr/unpaid-leave, hr/remote-work
- context: -

```
<no answer>
```

### `acl-dept-production-hr-payroll` — Заработная плата и выплаты

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/payroll, company/org-structure, finance/invoice-processing, hr/sick-leave-pay, hr/benefits-meals
- context: -

```
<no answer>
```

### `acl-dept-production-hr-personal-file` — Личное дело сотрудника

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/personal-file, it/email-quota, hr/unpaid-leave, company/org-structure, company/personal-data
- context: -

```
<no answer>
```

### `acl-dept-production-hr-probation` — Испытательный срок и наставник

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/probation, hr/remote-work, hr/internal-transfer, hr/onboarding-first-day, it/account-lifecycle
- context: -

```
<no answer>
```

### `acl-dept-production-hr-referral` — Как это работает

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/referral, hr/remote-work, it/account-lifecycle, hr/onboarding-first-day, company/workspace-rules
- context: -

```
<no answer>
```

### `acl-dept-production-hr-relocation` — Релокация и переезд

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/relocation, company/workspace-rules, it/account-lifecycle, hr/internal-transfer, hr/business-trip
- context: -

```
<no answer>
```

### `acl-dept-production-hr-remote-work` — Удалённая работа и гибридный график

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/remote-work, production/shift-schedule, company/org-structure, it/account-lifecycle
- context: -

```
<no answer>
```

### `acl-dept-production-hr-salary-bands` — Грейды и вилки окладов

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/payroll, company/org-structure, hr/referral, hr/benefits-meals, hr/expenses
- context: -

```
<no answer>
```

### `acl-dept-production-hr-sick-leave-notification` — Как сообщить о больничном

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/sick-leave-notification, hr/business-trip, hr/sick-leave-pay, hr/leave-policy, hr/payroll
- context: -

```
<no answer>
```

### `acl-dept-production-hr-sick-leave-pay` — Пособие рассчитывается по среднему заработку за два календарных года, предшествующих году

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/sick-leave-pay, hr/payroll, hr/donor-day, hr/maternity-leave, hr/benefits-dms
- context: -

```
<no answer>
```

### `acl-dept-production-hr-sick-leave` — Больничные: внутренняя инструкция для HR

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/sick-leave-notification, company/org-structure, hr/business-trip, hr/sick-leave-pay, hr/payroll
- context: -

```
<no answer>
```

### `acl-dept-production-hr-study-leave` — Сотрудникам, которые впервые получают образование соответствующего уровня в организации с

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/study-leave, hr/onboarding-first-day, production/safety-briefing, hr/training-budget, hr/probation
- context: -

```
<no answer>
```

### `acl-dept-production-hr-training-budget` — Обучение и компенсация курсов

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/training-budget, hr/study-leave, hr/expenses, hr/probation, production/safety-briefing
- context: -

```
<no answer>
```

### `acl-dept-production-hr-unpaid-leave` — Отпуск без сохранения заработной платы

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: hr/unpaid-leave, hr/leave-policy, hr/part-time, hr/study-leave
- context: -

```
<no answer>
```

### `acl-dept-production-it-access-and-equipment` — Доступы и оборудование

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/access-and-equipment, hr/onboarding-first-day, company/org-structure, hr/remote-work, hr/exit
- context: -

```
<no answer>
```

### `acl-dept-production-it-account-lifecycle` — Учётные записи и блокировка доступов

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/account-lifecycle, it/password-reset, hr/exit, company/org-structure, it/access-and-equipment
- context: -

```
<no answer>
```

### `acl-dept-production-it-backup-policy` — Резервные копии и восстановление

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/backup-policy, it/hardware-repair, it/email-quota, it/security, company/org-structure
- context: -

```
<no answer>
```

### `acl-dept-production-it-email-quota` — Почтовый ящик и архивы

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/email-quota, company/org-structure, it/security, it/backup-policy, hr/personal-file
- context: -

```
<no answer>
```

### `acl-dept-production-it-hardware-repair` — Ремонт техники и подменный ноутбук

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/hardware-repair, it/access-and-equipment, it/vpn-setup, it/backup-policy
- context: -

```
<no answer>
```

### `acl-dept-production-it-incident-runbook` — Регламент дежурства в ИТ

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/access-and-equipment, company/org-structure, hr/remote-work, it/security, hr/onboarding-first-day
- context: -

```
<no answer>
```

### `acl-dept-production-it-office-network` — Сеть, печать и гостевой Wi-Fi

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/office-network, it/access-and-equipment, company/workspace-rules, it/vpn-setup, it/account-lifecycle
- context: -

```
<no answer>
```

### `acl-dept-production-it-password-reset` — Сброс пароля и блокировка учётной записи

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/password-reset, it/account-lifecycle, it/security, company/org-structure, it/email-quota
- context: -

```
<no answer>
```

### `acl-dept-production-it-security` — Минимальная длина пароля — 12 символов. Пароли нельзя повторять в личных сервисах, передавать

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/security, it/password-reset, it/account-lifecycle, it/vpn-setup
- context: -

```
<no answer>
```

### `acl-dept-production-it-software-licenses` — Программное обеспечение и лицензии

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/software-licenses, it/access-and-equipment, company/org-structure, it/backup-policy
- context: -

```
<no answer>
```

### `acl-dept-production-it-vpn-setup` — Подключение к VPN

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: it/vpn-setup, it/office-network, it/access-and-equipment, hr/remote-work
- context: -

```
<no answer>
```

### `acl-dept-production-procurement-purchase-request` — Заявка на закупку

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/purchase-request, it/software-licenses, company/org-structure, finance/budget-request, procurement/supplier-onboarding
- context: -

```
<no answer>
```

### `acl-dept-production-procurement-supplier-onboarding` — Поставщик заполняет анкету: реквизиты, виды продукции, опыт работы, производственные мощности.

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/supplier-onboarding, procurement/purchase-request, company/anti-corruption, finance/counterparty-check, procurement/tender-rules
- context: -

```
<no answer>
```

### `acl-dept-production-procurement-tender-rules` — Тендеры на закупку

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/tender-rules, procurement/purchase-request, procurement/supplier-onboarding, company/anti-corruption, it/software-licenses
- context: -

```
<no answer>
```

### `acl-dept-production-production-equipment-maintenance` — Материал для производственных подразделений.

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: production/shift-schedule, production/safety-briefing, production/equipment-maintenance, company/quality-ecology, company/commercial-secret
- context: -

```
<no answer>
```

### `acl-dept-production-production-quality-control` — Контроль качества продукции

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: production/quality-control, company/anti-corruption, procurement/supplier-onboarding, procurement/purchase-request, finance/counterparty-check
- context: -

```
<no answer>
```

### `acl-dept-production-production-safety-briefing` — Инструктажи по охране труда

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: production/safety-briefing, hr/onboarding-first-day, security/badge-access, it/security, hr/probation
- context: -

```
<no answer>
```

### `acl-dept-production-production-shift-schedule` — Материал для производственных подразделений.

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: production/shift-schedule, production/safety-briefing, production/equipment-maintenance, company/quality-ecology, company/commercial-secret
- context: -

```
<no answer>
```

### `acl-dept-production-sales-contract-approval` — Материал для подразделения продаж.

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/commercial-secret, production/equipment-maintenance, company/org-structure, procurement/purchase-request, finance/budget-request
- context: -

```
<no answer>
```

### `acl-dept-production-sales-crm-rules` — Работа в CRM

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/org-structure, it/account-lifecycle, hr/remote-work, it/email-quota, it/access-and-equipment
- context: -

```
<no answer>
```

### `acl-dept-production-sales-customer-claims` — Претензии и рекламации клиентов

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/purchase-request, company/org-structure, company/anti-corruption, company/trademark-use, hr/expenses
- context: -

```
<no answer>
```

### `acl-dept-production-sales-kp-rules` — Коммерческое предложение: правила оформления

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/supplier-onboarding, procurement/purchase-request, company/anti-corruption, company/trademark-use, company/code-of-conduct
- context: -

```
<no answer>
```

### `acl-dept-production-sales-pricing-approval` — Материал для подразделения продаж.

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: company/commercial-secret, production/equipment-maintenance, company/org-structure, procurement/purchase-request, finance/budget-request
- context: -

```
<no answer>
```

### `acl-dept-production-sales-tender-participation` — Участие в тендерах клиентов

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: procurement/tender-rules, procurement/purchase-request, procurement/supplier-onboarding, company/anti-corruption, finance/counterparty-check
- context: -

```
<no answer>
```

### `acl-dept-production-security-badge-access` — Пропуска и физический доступ

- stratum: `acl`
- audience: `dept:production`
- escalated: None (expected False)
- escalation reason: - (expected -)
- missing fragments: -
- forbidden fragments: -
- retrieved: security/badge-access, it/access-and-equipment, it/account-lifecycle, it/security, company/workspace-rules
- context: -

```
<no answer>
```

