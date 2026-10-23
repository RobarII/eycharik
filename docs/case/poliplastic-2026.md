# Case: POLIPLASTIK onboarding assistant in MAX

A transcript of the hackathon brief (Moscow, October 2026), kept so that every product claim has a
source in the repository. The deck is a scan without a text layer; this file is the transcription.
Russian fragments are verbatim quotes of the brief and of the client's spreadsheet. Everything else
is a summary.

## Source files

| File | What it is |
|---|---|
| `КЕЙС_ПОЛИПЛАСТИК.pdf` | 13-slide brief: problem, tasks, roles, requirements, checkpoints, criteria |
| `Финал. ТЗ. Чат-бот Корсик- 15.09.xlsx` | the client's scenario of the existing Telegram bot, step by step |
| `Правила внутреннего трудового распорядка П 3.11-07 Издание 1.pdf` | HR regulation, candidate knowledge source |
| `Положение о коммерческой тайне.pptx` | internal policy, candidate knowledge source |
| `Антикоррупционная политика.pptx` | internal policy, candidate knowledge source |
| `Политика в области качества и экологии.pptx` | internal policy, candidate knowledge source |

Tags of the brief: `МАКС · ML · AI · RAG`.

## Problem

> Основная проблема: невозможность безопасного использования Telegram в корпоративном контуре и
> отсутствие ИИ-слоя для обработки неструктурированных данных и эмоций сотрудников.

The client already runs a Telegram bot, «Корсик», for onboarding. It is a hard-coded button menu:
it cannot answer free text, cannot read the sentiment of survey answers, and every change needs a
developer. Telegram itself is not allowed inside the corporate perimeter, hence the move to MAX.

Secondary problems named in the brief:

| Problem | Quote |
|---|---|
| Manual HR load | «HR-специалисты тратят до 40% времени на разбор текстовых ответов в опросах и ответы на типовые вопросы, выходящие за рамки кнопочного меню» |
| No predictive analytics | «текущий бот фиксирует только свершившиеся факты (например, увольнение сотрудника), но не анализирует причины и эмоциональный фон на ранних этапах» |
| Scaling cost | «логика Telegram-бота требует привлечения разработчиков для добавления новых филиалов или изменения регламентов» |

Declared value: up to 70% less routine HR work, faster time to productivity, one communication
standard inside MAX, and in perspective a reusable product for large corporations.

## Tasks

1. **Migration to MAX.** Move the bot to the corporate MAX while keeping the proactive timeline
   (from offer to the end of probation) and personalization for each production site.
2. **Answers to questions.** Integrate a RAG module for unstructured questions in natural language.
3. **Sentiment analysis.** The model analyses free-text answers in pulse surveys, finds hidden
   problems (conflicts in the team, unclear tasks) and escalates red flags to HR.
4. **Accuracy and escalation.** Control hallucinations and provide seamless escalation to a live
   recruiter through the MAX API.

Expected result: «ИИ-ассистент (чат-бот) и интеграционный слой для мессенджера «МАКС»».

## Roles

| Role | What the role does in the product |
|---|---|
| New employee | asks the bot in MAX, for example «Подскажи, как получить доступ к корпоративному порталу?», and gets a step-by-step instruction with links |
| HR manager | gets a summary of where each newcomer is in onboarding and which topics cause trouble, based on request tags; joins the dialog only in non-standard cases |
| Head of department | sees the adaptation status of a new subordinate and receives push notifications about a needed personal meeting |
| Head of the recruitment department | receives a weekly digest «Настроения в коллективе новичков»: the model clusters free-text survey answers («проблемы с доступами», «конфликт с наставником») and highlights risk zones, so HR works ahead of crises |

## Requirements

| Area | Requirement |
|---|---|
| Integration | adapt to MAX API limits, in particular a CRON task planner for proactive sends, interactive cards and attachments (PDF maps, images), escalation buttons |
| AI architecture | RAG over the knowledge base plus an NLP sentiment module for survey answers |
| Safety | strict hallucination control; no invented answers to HR and legal questions; mandatory escalation to an HR specialist |
| Tone | answers follow the corporate communication style |
| UX | friendly interface that supports both text input and a hybrid flow: button menu plus free dialog |
| Scale | rollout to all new employees, up to 100%, with the option to replicate to subsidiaries |

UX detail from the role slide: the employee can either type or press, and the bot must not lose the
thread when the employee deviates from the menu.

## Channels and checkpoints

- Chat in MAX is the product; MTS Link is the platform for the defense.
- Three checkpoints: **23.10 18:00**, **24.10 11:00**, **24.10 18:00** (Moscow time). A team that
  misses two checkpoints is out of the competition. Teams must join their own slot; the link is in
  the participant cabinet, tab «Чек-поинты».
- Defense starts **25.10 at 12:00**; upload deadline **25.10 10:00**. The defense slot and the link
  are in the cabinet, tab «Защита». Other teams' defenses are open to watch.
- After the first checkpoint the team must publish a link where experts can view the solution, even
  if it is still empty. All mandatory artifacts and a `README` must be attached to the cabinet.

## Judging criteria

1. **Prototype** — does the actual functionality match what the team claims?
2. **Solves the main problem** — does the product remove the stated blocker?
3. **Build and rollout** — does the effect justify the cost of development and adoption?
4. **Novel ideas** — own features or a new approach, not a copy of existing solutions.
5. **UI/UX** — how well the interface is designed.
6. **Secondary problems** — are the named, and any noticed, secondary problems solved?
7. **Analytics** — depth of analysis of the target audience, UX problems, and comparable digital
   products.

## Baseline bot «Корсик» (Telegram)

The spreadsheet describes the current product that must be migrated and upgraded. Its shape:

- A named persona, «Корсик», speaks informally, uses emoji and postcards, and lets the employee
  choose «ты» or «вы» at the start.
- The journey runs from 2–3 days before the first working day to the last day of probation; every
  message has a trigger time and a site tag: `GrPP`, `Luzhniki`, `GTP`.
- Messages are button-driven. Branching exists only inside a step: every survey answer has a
  prepared reply, and negative answers offer «передать проблему в отдел подбора персонала через
  Корсика» or «связаться с рекрутером».
- Content includes documents checklist, transport routes, territory and floor maps, lunch places,
  contacts book, corporate presentation, gym, corporate events and photo archive, movie and book
  lists, music playlist, and postcards as image attachments.
- Surveys: first day, third day (3 questions), two weeks (9 scale questions, any score below 8 asks
  for a reason), two months (3 questions), end of probation (3 questions plus 9 scale questions).
- Reminders: a survey that is not completed within one day is reminded the next day and the day
  after.
- A free question outside the scenario answers: «Какие-то вопросы слишком сложные, чтобы я мог
  решить их самостоятельно. Я посоветуюсь с коллегами из подбора персонала и вернусь с ответом!»

### Timeline of the spreadsheet

| When | What the client sends |
|---|---|
| 2–3 days before day one | bot introduction and capabilities, «ты/вы» choice, documents checklist, corporate transport by site, company facts, goodbye |
| Day before | first-day readiness question, documents reminder |
| Day one 10:00 | congratulations, access and equipment |
| Day one 11:00 | territory map, office floor map |
| Day one 12:00 | access check with «Да, все есть» / «Нет» |
| Day one 12:01 | postcard |
| Day one 12:30 | where to have lunch |
| Day one 13:00 | contacts book link, warning about the corporate network |
| Day one 15:00 | corporate presentation, mission |
| Day one 18:00 | end of the first day |
| Day two | recruiter-triggered introduction post with a photo |
| Day three 09:00 | adaptation plan from the manager |
| Day three 11:00 | gym |
| Day three 17:30 | three-question survey with branching and escalation buttons |
| Day ten | corporate events and photo archive |
| Two weeks | nine-question check-in: clear tasks, information, manager availability and feedback, colleagues, IT support, access timing, HR support |
| Month two, day one | congratulations, adaptation plan progress |
| Month two plus two weeks | reminder of the meeting with the recruiter, movie list |
| Month two plus three weeks | postcard, three-question survey (mood, who helps, what would speed up adaptation) |
| Month three, day one | finish line, book list |
| Month three plus two weeks | postcard |
| Last day of probation | three-question survey, nine scale questions, playlist, farewell with postcard |

Tags `GrPP` and `Luzhniki` share office copy; `GTP` has its own transport, contacts (`http://ats/`)
and gym texts. The surveys differ between office sites and the plant: the plant variant omits the
remote-work option.

## Notes for the implementation

Recorded here so that the transcript is not later read as a promise:

- The brief asks for a CRON planner; our worker currently ticks reminders itself.
- The brief asks for PDF and image attachments and escalation buttons; the MAX adapter today sends
  text plus an inline keyboard, and file upload is a known gap in
  [contracts/max-api.md](../contracts/max-api.md).
- The brief asks HR to upload regulations without code; ingestion today is a CLI command.
- The 70% figure is the client's expectation, not our measurement. Any number we publish needs a
  command, an environment and a commit under [measurements/](../measurements/TEMPLATE.md).
