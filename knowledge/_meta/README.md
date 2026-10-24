---
id: _meta/readme
title: Метаданные базы знаний
type: knowledge
status: active
owner: hr-team
audience: [all]
valid_from: 2026-01-01
valid_to: null
source_of_truth: knowledge/_meta/README.md
related: []
---

# Метаданные базы знаний

Отдельного файла ACL нет. Единственный источник правды — frontmatter каждого документа:

- `audience` — кто может найти документ: `all`, `dept:<name>`, `hr_only`.
- `valid_from` / `valid_to` — окно действия; просроченные документы не находятся никогда.
- `owner` — кто проверяет документ; отчёт об устаревании группирует по owner.
- `status` — `draft` не индексируется, `deprecated` не индексируется, `active` индексируется.

Добавить документ — значит добавить строку в очередь проверки его owner. Задача индексации проверяет
каждый файл по `docs/contracts/doc.schema.json` и роняет всю пачку на одном невалидном файле, поэтому
наполовину проиндексированного корпуса не бывает.
