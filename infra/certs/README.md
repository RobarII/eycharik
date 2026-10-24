# Russian trusted CA

`russian_trusted_ca.crt` is the Ministry of Digital Development root bundle: the Russian Trusted
Root CA plus its Russian Trusted Sub CA. MAX and GigaChat present chains anchored there, and the
default Python trust store does not contain it.

Source: <https://gu-st.ru/content/Other/doc/russiantrustedca.pem> (downloaded 2026-10-24).
SHA-256: `6d1b66e7c1aa2512ad3abb50d6a6f144c9ee9d80fd7fbe1c9255a39f8e790944`.

The API image installs it into the system store and points `MAX_CA_BUNDLE` at the merged bundle, so
`httpx` trusts both public and Russian roots. Refresh the file from the same URL when the bundle
changes, update the hash here, and rebuild the image.
