# Glossary

One meaning per term. Code, docs, and prompts use these words and no synonyms.

| Term | Meaning |
|---|---|
| **employee** | A person in the company for whom an onboarding run exists. Identified by `employee_id`. |
| **newcomer** | An employee inside an active onboarding run. A role, not a separate entity. |
| **recruiter** | A person who owns onboarding runs for a hiring pipeline. Sees only their own runs. |
| **hr_admin** | A person who owns the knowledge base, scenarios, and all runs. |
| **scenario** | A versioned, declarative onboarding path: an ordered set of steps with events and timeouts. |
| **scenario_version** | An integer. A run keeps the version it started on; editing a scenario never changes a live run. |
| **run** | One employee's execution of one scenario. `(employee_id, scenario_id, scenario_version)`. |
| **step** | A node in a scenario: a message, a wait, a check, or a terminal state. |
| **step_state** | The persisted position of a run: current step, when it was entered, what was completed. |
| **event** | An input that may move a run: `employee_created`, `message_received`, `button_pressed`, `file_received`, `timeout`. |
| **due reminder** | A timer whose deadline has passed and which must be emitted as an outbox row. |
| **knowledge document** | A file under `knowledge/` with frontmatter; the only allowed source of factual answers. |
| **chunk** | A retrievable slice of one knowledge document. Identified by `chunk_id`, stable across reindexing. |
| **citation** | A reference from an answer to a `chunk_id` that was actually retrieved for that question. |
| **grounded answer** | An answer whose every factual sentence is supported by a citation in the retrieved set. |
| **escalation** | Handing the question to a human, with the reason and the transcript attached. |
| **deflection** | A question resolved by the bot without escalation. The main product metric. |
| **audience** | The access scope of a document or chunk: `all`, `dept:<name>`, `hr_only`. |
| **eval case** | A question with expected behaviour: required facts, required citations, or required escalation. |
| **api** | The process that terminates MAX webhooks, validates them, enqueues events, and serves the admin API. It never calls the model. |
| **worker** | The process that processes queued events: scenarios, retrieval, generation, sending, dispatch, and the reminder tick. |
| **scheduler** | The loop inside the worker that turns due reminders into queued jobs. |
| **outbox** | A table of committed future work. Timers and outgoing messages are rows, not sleeping tasks. |
