# Локальный предпросмотр

`npm run preview:demo` поднимает Vite с dev-API на `/admin/api/*`, поэтому кабинет можно смотреть
без PostgreSQL и без провайдера модели.

- Фикстуры повторяют когорту из `docs/product/demo-script.md`.
- Токены: `dev-recruiter-token` (рекрутёр `rec-1`) и `dev-hr-token` (HR, без скоупа).
- Плагин использует `apply: "serve"` и импортируется только из `vite.config.ts`; `npm run build`
  его никогда не отдаёт.
- Это инструмент ревью дизайна, а не доказательство качества данных. Боевой кабинет по-прежнему
  читает API из `docs/contracts/admin-api.md`.
