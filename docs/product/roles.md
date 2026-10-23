# Roles and access

| Capability | employee | recruiter | manager | hr_admin |
|---|---|---|---|---|
| Chat with the bot | own | own | own | own |
| See own onboarding run | yes | yes | yes | yes |
| See other employees' runs | no | own pipeline | own department | all |
| See the risk digest | no | own pipeline | own department | all |
| Send a manual message | no | own pipeline | no | all |
| Resolve an escalation | no | own pipeline | own department | all |
| Read `audience: hr_only` documents | no | no | no | yes |
| Upload knowledge documents | no | no | no | yes |
| Edit scenarios and prompts | no | no | no | via review only |
| Read metrics | no | own pipeline | own department | all |

## Rules

1. Audience is enforced twice: in the retrieval SQL filter and in the admin API query.
2. A recruiter's token carries `recruiter_id`; a mismatch answers `404`, never `403`.
   A manager's token carries the department name as its subject, so the same SQL predicate becomes
   `employees.department = :subject`. A department head sees the digest and the numbers, not the
   conversation text and not the ability to write to the base.
3. The bot runs with a service identity that has read access to `audience: all` and
   `dept:*` chunks for the employee's department, and no access to `hr_only`.
4. Every manual message and escalation resolution writes an audit row with the actor.
5. Removing an employee from the directory ends the run and deletes transcripts per retention
   policy; the audit row survives without personal data.
