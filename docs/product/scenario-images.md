# Scenario images

The onboarding bot uses one mascot, «Корсик», drawn on the corporate blue. The client supplied 16
square postcards in the `Korsiki_kartinki` handover bundle; the repository keeps resized copies in
`apps/api/onboarding/assets/scenario/`.

The source names arrived mojibake-encoded as `1080Â1080_<n>.jpg`. Each source is 1620 × 1620; the
checked-in copy is 1080 × 1080 JPEG at quality 80, which is below the MAX limit and small enough
for the container image. The caption is part of the bitmap, so the scenario text must not repeat
it verbatim.

| Source | Asset | Caption on the image | Used by |
|---|---|---|---|
| `1080x1080_1.jpg` | `questions.jpg` | «Обращайся, если есть вопросы!» | third-day and two-week surveys |
| `1080x1080_2.jpg` | `hello.jpg` | «ПРИВЕТ!» | spare welcome variant |
| `1080x1080_3.jpg` | `documents.jpg` | «Возьми с собой в первый рабочий день:» | `documents_checklist` |
| `1080x1080_4.jpg` | `welcome.jpg` | «Добро пожаловать в команду!» | `welcome` |
| `1080x1080_5.jpg` | `lunch.jpg` | «Держи список локаций, где вкусно!» | `lunch` |
| `1080x1080_6.jpg` | `contacts.jpg` | «Помогу найти любой контакт!» | `contacts` |
| `1080x1080_7.jpg` | `support.jpg` | «Я всегда на связи!» | `access_check` |
| `1080x1080_8.jpg` | `progress.jpg` | «Первый этап пройден!» | `first_day_end` |
| `1080x1080_9.jpg` | `thanks.jpg` | «Так мило, что ты с нами!» | probation survey |
| `1080x1080_10.jpg` | `congrats.jpg` | «ПОЗДРАВЛЯЕМ!» | `month_two_plan` |
| `1080x1080_11.jpg` | `party.jpg` | no text, party hat | `first_day` |
| `1080x1080_12.jpg` | `reminder.jpg` | «Спешу тебе напомнить...» | `day_before`, `probation_reminder`, reminders |
| `1080x1080_13.jpg` | `error.jpg` | «Что-то пошло не так...» | `access_help` |
| `1080x1080_14.jpg` | `calm.jpg` | no text, arms open | `day_three_plan`, `week_two_plan` |
| `1080x1080_15.jpg` | `formal_hello.jpg` | «Приветствую!» | spare formal welcome variant |
| `1080x1080_16.jpg` | `goodbye.jpg` | «Удачи!!!» | `done` |

The map and the plant variant share the same image names; there is no separate plant artwork. The
two spare welcome variants exist because the first step asks «ты» or «вы» and a later revision may
choose the image from the run tone.

Source: client handover, 2026-10-23. The captions are quoted as supplied; they are Russian
user-facing copy.
