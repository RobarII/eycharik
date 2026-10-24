# Доверенный российский CA

`russian_trusted_ca.crt` — корневой бандл Минцифры: Russian Trusted Root CA плюс его Russian
Trusted Sub CA. MAX и GigaChat предъявляют цепочки с якорем доверия там, а в стандартном хранилище
доверия Python его нет.

Источник: <https://gu-st.ru/content/Other/doc/russiantrustedca.pem> (скачано 2026-10-24).
SHA-256: `6d1b66e7c1aa2512ad3abb50d6a6f144c9ee9d80fd7fbe1c9255a39f8e790944`.

Образ API ставит его в системное хранилище и указывает `MAX_CA_BUNDLE` на объединённый бандл,
поэтому `httpx` доверяет и публичным, и российским корням. Когда бандл меняется, обновите файл по
тому же URL, обновите хеш здесь и пересоберите образ.
