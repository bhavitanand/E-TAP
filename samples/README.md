# Sample Corpus and Test Data

This folder contains metadata for test email sets and parser fixtures. It does **not** contain the raw `.eml` and `.msg` files referenced in the email dataset manifests; those formats are excluded by the repository's root `.gitignore`.

## What is included

- `email_dataset/set_*/set*_manifest.json` — sample IDs, intended relative paths, format labels and categories. A manifest entry does not mean the referenced raw email file is present in a fresh clone.
- `../docs/parser_fixtures/` — small structured fixture files used by selected parser and forensic tests.
- The two sample emails used by the dashboard's live-pipeline test buttons are embedded as strings in `frontend/src/pages/UploadPage.jsx`; they are sent to the actual `/analyze` API when those buttons are clicked.

## Why raw emails are not committed

Email corpora can contain personal data, sensitive headers, malicious attachments, redistribution restrictions or large payloads. Obtain or create test artifacts only when you have permission to use them. Prefer synthetic, non-sensitive samples for public demos and automated tests.

If you add an approved small fixture to the repository, review its content and licensing first and update `.gitignore` deliberately rather than removing the email-artifact ignore rules globally.
