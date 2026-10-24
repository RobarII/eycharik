# Runbook: 152-ФЗ evidence pack

An engineering checklist for handling personal data in this product, written so that the operator's
DPO can attach evidence to their own register. It is **not legal advice** and it does not decide the
lawful basis: the operating company is the data operator, its DPO signs, its counsel approves.

The product stores employee conversations in MAX, onboarding progress, and free-text survey answers.
That is personal data under 152-ФЗ even when no name is stored, because the chat identifies a person.

## 1. Data map

| Data | Table | Retention control | Contains personal data |
|---|---|---|---|
| Employee ↔ chat identity | `chats`, `employees` | delete on offboarding | yes |
| Outbound message text | `messages` | `DATA_RETENTION_DAYS` after `sent_at` | yes |
| Audit evidence, quotes, questions | `audit_log.fields` | nulled after `DATA_RETENTION_DAYS`, row stays | yes |
| Runs, risk signals, jobs, events | `runs`, `risk_*`, `jobs`, `events` | not purged, ids only | no free text |
| Knowledge corpus | `kb_*` | versioned by `valid_from` / `valid_to` | not personal data |
| Prompts, answers sent to a vendor | provider side | provider contract | yes, in transit |

Retention mechanics are in [retention.md](retention.md). The numeric window is a policy value the
client owns; `DATA_RETENTION_DAYS` ships as 365 and is not a legal statement.

## 2. Localisation (art. 18 part 5)

- [ ] Postgres, object storage, and backups physically in Russia.
- [ ] Model vendor processes the data inside Russia. For managed APIs that means an internal-only
      model: Cloud.ru Foundation Models marks each model internal or external, and external models
      call out of the country. Source: [vendor comparison](../product/vendor-comparison.md).
- [ ] OCR runs in-process (PP-OCRv5 over ONNX Runtime), so scans never leave the host.
- [ ] Embeddings are computed by a model inside the same contour as the text.
- [ ] No fallback that silently routes a request abroad when the primary vendor fails. Today a
      vendor failure escalates to a human instead, which is the correct default.

## 3. Errand of processing (art. 6 part 3)

For every vendor that touches personal data, the operator needs a written errand with: the list of
data, the purpose, the duration, the security measures, and the ban on using the data for anything
else.

- [ ] Errand of processing signed with the model vendor.
- [ ] Written confirmation that training on the client's data is **off** by default.
- [ ] Written confirmation of where the data is stored and for how long on the vendor side.
- [ ] Sub-processors listed. A gateway that forwards to a third country is a sub-processor.
- [ ] The vendor's attestation covers the **service**, not only the cloud. An UZ-1 attestation for a
      cloud platform says nothing about a model endpoint running on it; ask for the service-level
      document, or accept the risk in writing.

## 4. Security measures (постановление 1119, приказ ФСТЭК 21)

- [ ] Attestation level declared by the operator: UZ-1 is the usual target for an HR system.
- [ ] Attestation document names the segment (availability zone) actually used.
- [ ] Access control: admin tokens are per-role, `ADMIN_TOKENS` is not shared between people,
      `METRICS_TOKEN` is separate.
- [ ] Transport: TLS only, `MAX_CA_BUNDLE` points at the Russian Trusted CA bundle for MAX.
- [ ] Secrets: bot token, provider keys, webhook secret live in the deployment environment, never in
      git, never echoed in an error message ([`.env.production.example`](../../.env.production.example)).
- [ ] Encryption at rest on the database volume and on backups.
- [ ] Backups restorable: [backup.md](backup.md) and [restore.sh](../../scripts/restore.sh) prove it.
- [ ] Audit log of admin actions in the cabinet (`audit_log`), retained per policy.
- [ ] Log hygiene: application logs carry ids, not message text.

## 5. Rights of the data subject

- [ ] Offboarding deletes every row for the employee's chats immediately, including audit fields.
- [ ] A subject request can be answered from the database: what is stored, where, for how long.
- [ ] Survey free text is purged on the same window as messages, not kept "for analytics".

## 6. Incident

- [ ] The operator's DPO is the notification owner; the engineering side provides the timeline.
- [ ] Notification deadline and channel are written in the operator's internal regulation, not in
      this repository.
- [ ] The incident template lives in [incidents/](../incidents/) and states: what leaked, which
      subjects, when discovered, what was fixed, how the fix was proven.

## 7. Evidence pack for the DPO

1. Data map above, signed by the engineer who owns the schema.
2. Retention runbook and the `DATA_RETENTION_DAYS` value in production.
3. Vendor contracts: errand of processing, training-off clause, sub-processor list.
4. Attestation documents for the segment used.
5. Backup and restore drill record.
6. Access matrix: who holds which token.
7. This checklist, with dates and owners.

## What is still open in this repository

- `DATA_RETENTION_DAYS` is a placeholder until the client's policy fixes it.
- The demo host is outside Russia and holds no personal data; the pilot host must be chosen before
  the first real employee is onboarded ([deploy.md](deploy.md)).
- No vendor quote is attached yet; the comparison lists what to request.
