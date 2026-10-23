import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { fetchKnowledge, uploadKnowledge } from "../api";
import { EmptyState, ErrorNote, SkeletonRows } from "../components/States";
import { useUnauthorized } from "../useUnauthorized";
import { formatDateTime } from "../format";

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
        <div>
          <h1>База знаний</h1>
          <p className="muted">
            HR загружает документ с frontmatter, ассистент сразу отвечает по нему со ссылкой.
            Изменения фиксируются в аудите.
          </p>
        </div>
        <div className="page-count" aria-live="polite">
          {query.isSuccess ? `${query.data.items.length} документов` : "…"}
        </div>
      </header>

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
        <textarea
          id="knowledge-text"
          className="upload-area"
          value={text}
          placeholder={TEMPLATE}
          onChange={(event) => setText(event.target.value)}
          rows={12}
          spellCheck={false}
        />
        <div className="upload-actions">
          <button type="button" className="link-button" onClick={() => setText(TEMPLATE)}>
            Вставить шаблон
          </button>
          <button type="submit" className="button button-primary" disabled={upload.isPending || text.length < 20}>
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

      <h2 className="section-title">Загруженные документы</h2>
      {query.isLoading ? <SkeletonRows rows={4} /> : null}
      {query.isError ? (
        <ErrorNote message={query.error.message} onRetry={() => void query.refetch()} />
      ) : null}
      {query.isSuccess && query.data.items.length === 0 ? (
        <EmptyState title="База пуста">Загрузите первый документ или выполните make ingest.</EmptyState>
      ) : null}
      {query.isSuccess && query.data.items.length > 0 ? (
        <ul className="knowledge">
          {query.data.items.map((item) => (
            <li key={item.id} className="knowledge-row">
              <div>
                <strong>{item.title}</strong>
                <p className="digest-meta">
                  <code>{item.id}</code> · {item.audience.join(", ")} · owner {item.owner}
                </p>
              </div>
              <span className="digest-meta">{formatDateTime(item.updated_at)}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
