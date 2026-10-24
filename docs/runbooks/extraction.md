---
title: Документ не дошёл до корпуса
summary: Где искать загруженный файл, что значит каждый отказ извлечения и как перечитать его с другим профилем.
kind: прогон
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Прогон: загруженный документ не дошёл до корпуса

Извлечение идёт в воркере (ADR 0015). Файл сохраняется, попадает в очередь, извлекается, получает
решение и только потом индексируется. Каждый шаг оставляет строку, поэтому отказ диагностируется
без логов.

## 1. Где файл?

```bash
psql "$DATABASE_URL" -c "select id, filename, media_type, size, created_at from kb_files order by created_at desc limit 10"
psql "$DATABASE_URL" -c "select status, reason, engine, route, pages, min_confidence, document_id, updated_at from kb_extractions where content_hash = '<hash>'"
psql "$DATABASE_URL" -c "select id, kind, attempts, last_error from jobs where kind = 'extract_document' order by id desc limit 10"
```

Кабинет показывает то же самое: `GET /admin/api/knowledge/files/{hash}`. Строки нет вообще — задача
ещё не шла; проверьте, что воркер поднят (`make logs`).

## 2. Прочитайте причину

| `reason` | Значение | Что делать |
|---|---|---|
| `unsupported` | формат не PDF и не PPTX, или объявленным типом не владеет ни один ридер | конвертировать в PDF |
| `encrypted` | PDF требует пароль | загрузить расшифрованную копию |
| `no_pages` | парсер не нашёл страниц: файл битый или обрезанный | переэкспортировать из источника |
| `too_many_pages` | больше `EXTRACTION_MAX_PAGES` | разделить документ или поднять лимит |
| `low_dpi` | растр меньше `quality.min_dpi` | загрузить оригинал, а не фото распечатки |
| `blurry` | высокочастотная детализация ниже `quality.min_edge_energy` (по умолчанию не задан) | держать камеру устойчивее, использовать приложение сканера |
| `unreadable` | растр не декодируется как изображение | переэкспортировать страницу |
| `low_confidence` | страница набрала меньше `acceptance.min_confidence`: блик, печать или рукопись | переснять эту страницу или взять профиль посильнее |
| `too_short` | принятый текст меньше `acceptance.min_chars` | файл не документ |
| `empty` | ни одна страница не дала текста | то же |

Отказ — не ошибка: задача завершилась. Ничего не проиндексировано и ничего не повторяется, потому
что ответ был бы тем же.

## 3. Перечитайте тот же файл с лучшим профилем

Кэш ключуется по `(content_hash, profile_hash)`, поэтому смена `EXTRACTION_PROFILE` и перезапуск
воркера перечитывает те же байты без новой загрузки:

```bash
EXTRACTION_PROFILE=doc-scan uv run python -m onboarding.cli extract --file regulation.pdf
```

Этот dry-run печатает маршрут, движок, число страниц и вердикт и не трогает базу. Если он принимает
файл, переключите воркер на тот же профиль и поставьте файл в очередь заново:

```bash
psql "$DATABASE_URL" -c "insert into jobs (kind, payload) values ('extract_document', jsonb_build_object('blob_id','<hash>','filename','regulation.pdf','media_type','application/pdf','metadata','{}'::jsonb))"
```

Для настоящей загрузки используйте кабинет или `curl -F` на `POST /admin/api/knowledge/files` с
частью metadata; пустой `metadata` контракт отвергает, так и задумано.

## 4. Включите распознавание

Распознавание — необязательная надстройка. Без него профиль `native` отвергает любой скан с
`unsupported`, а цифровые файлы не страдают.

```bash
uv sync --extra ocr            # rapidocr + onnxruntime, CPU, no Paddle runtime
EXTRACTION_PROFILE=doc-scan make up
```

Первая задача ничего не скачивает: RapidOCR везёт веса PP-OCRv5 внутри wheel. Apple Silicon
поддерживается; GPU не нужен и не используется.

## 5. Перекалибруйте порог

Пороги предварительные, пока не измерены. Прокси размытия — средняя абсолютная высокочастотная
детализация растра, и она зависит от разрешения и плотности заливки, поэтому сравнивать её можно
только внутри одного ридера и одного профиля. Оценки блика нет намеренно: доля насыщенных пикселей
~0,96 на идеально чистой странице, так что она отвергла бы любой документ.

```bash
make eval-ocr                  # character error rate and refusal correctness on docs/evals/ocr.yaml
```

Меняйте порог только с файлом измерения в `docs/measurements/`, где названы команда, окружение и
коммит. `fingerprint()` профиля меняется вместе с порогами, поэтому кэш инвалидируется сам — руками
чистить не нужно.

## 6. Байты пропадают после окна хранения

`RetentionPurger` удаляет строки `kb_files` старше `DATA_RETENTION_DAYS`. Принятый markdown уже
документ в `kb_documents`, поэтому текст выживает; удаляются только исходные байты. Кэшированную
запись извлечения без её файла перечитать нельзя — в этом случае загрузите файл снова.
