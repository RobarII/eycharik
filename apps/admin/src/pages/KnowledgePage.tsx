import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { fetchKnowledge, uploadKnowledge } from "../api";
import { ErrorNote } from "../components/States";
import { useUnauthorized } from "../useUnauthorized";
import { useSession } from "../session";
import { countLabel, formatDateTime } from "../format";

const TEMPLATE = `---
id: hr/new-policy
title: Название документа
type: knowledge
status: active
owner: hr
audience: [all]
valid_from: 2026-10-01
---

## Раздел

Текст, из которого ассистент сможет отвечать.`;

export function KnowledgePage({ onUnauthorized }: { onUnauthorized: () => void }) {
  const queryClient = useQueryClient();
  const { can } = useSession();
  const canWrite = can("knowledge.write");
  const [text, setText] = useState("");
  const query = useQuery({
    queryKey: ["knowledge"],
    queryFn: fetchKnowledge,
    refetchInterval: 30_000,
  });
  const upload = useMutation({
    mutationFn: uploadKnowledge,
    onSuccess: () => {
      setText("");
      void queryClient.invalidateQueries({ queryKey: ["knowledge"] });
    },
  });

  useUnauthorized(query.error ?? upload.error, onUnauthorized);

  return (
    <section className="page">
      <header className="page-head">
        <div className="page-head-text">
          <p className="eyebrow">Документы</p>
          <h1>База знаний</h1>
          <p className="muted">
            HR загружает документ с frontmatter, ассистент сразу отвечает по нему со ссылкой.
            Изменения фиксируются в аудите.
          </p>
        </div>
        <div className="page-count" aria-live="polite">
          {query.isSuccess
            ? countLabel(query.data.items.length, "документ", "документа", "документов")
            : "…"}
        </div>
      </header>

      <div className={canWrite ? "knowledge-layout" : "knowledge-layout knowledge-layout-read"}>
        {canWrite ? (
        <section className="card">
          <div className="card-head">
            <h2>Новый документ</h2>
            <span className="card-note">Индексируется сразу</span>
          </div>
          <form
            className="upload"
            onSubmit={(event) => {
              event.preventDefault();
              upload.mutate(text);
            }}
          >
            <label className="upload-label" htmlFor="knowledge-text">
              Markdown с frontmatter
            </label>
            <p className="upload-hint">
              Поля id, title, type, status, owner, audience и valid_from проверяются по схеме до
              записи. Загружать может только HR-администратор.
            </p>
            <textarea
              id="knowledge-text"
              className="upload-area"
              value={text}
              placeholder="Вставьте markdown с frontmatter. Поля проверяются по схеме doc.schema.json. Или нажмите «Вставить шаблон»."
              onChange={(event) => setText(event.target.value)}
              rows={14}
              spellCheck={false}
            />
            <div className="upload-actions">
              <button
                type="button"
                className="button button-quiet"
                onClick={() => setText(TEMPLATE)}
              >
                Вставить шаблон
              </button>
              <button
                type="submit"
                className="button button-primary"
                disabled={upload.isPending || text.length < 20}
              >
                {upload.isPending ? "Индексируем…" : "Загрузить и проиндексировать"}
              </button>
            </div>
            {upload.isError ? <ErrorNote message={upload.error.message} /> : null}
            {upload.isSuccess ? (
              <p className="note note-ok" role="status">
                «{upload.data.title}» проиндексирован: {upload.data.chunks} фрагментов, id{" "}
                <code>{upload.data.id}</code>.
              </p>
            ) : null}
          </form>
        </section>
        ) : null}

        <section className="card">
          <div className="card-head">
            <h2>{canWrite ? "Активные документы" : "Что ассистент знает"}</h2>
            <span className="card-note">
              {query.isSuccess ? `${query.data.items.length} в индексе` : "…"}
            </span>
          </div>
          {query.isPending ? <p className="empty-inline">Загружаем документы…</p> : null}
          {query.isError ? (
            <ErrorNote message={query.error.message} onRetry={() => void query.refetch()} />
          ) : null}
          {query.isSuccess && query.data.items.length === 0 ? (
            <p className="empty-inline">
              База пуста. Загрузите первый документ или выполните make ingest.
            </p>
          ) : null}
          {query.isSuccess && query.data.items.length > 0 ? (
            <ul className="knowledge">
              {query.data.items.map((item) => (
                <li key={item.id} className="knowledge-row">
                  <div className="knowledge-main">
                    <strong>{item.title}</strong>
                    <p className="digest-meta">
                      <code>{item.id}</code>
                      <span aria-hidden="true">·</span>
                      <span>{item.audience.join(", ")}</span>
                      <span aria-hidden="true">·</span>
                      <span>owner {item.owner}</span>
                    </p>
                  </div>
                  <span className="digest-meta">{formatDateTime(item.updated_at)}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      </div>
    </section>
  );
}
