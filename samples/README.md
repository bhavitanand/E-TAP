# Test Corpus

This folder holds raw email samples used for testing/training across the pipeline
(Stage A parser fixtures, Stage C classifier, Stage B2 attachment forensics).

**Nothing under `samples/raw/` is committed to git** (see root `.gitignore`) —
only the empty folder structure (via `.gitkeep` files) is tracked, so everyone
gets the same layout when they clone the repo, but has to download the actual
files themselves.

```

## Why not commit the files

- **Repo bloat** — 100+ emails with attachments can hit hundreds of MB fast.
- **Legal/ethical gray area** — some public phishing corpora contain real
  malicious payloads; redistributing them inside our own repo is bad practice,
  especially once the repo may go public post-hackathon.
- **License terms** — some corpora (Enron, CIC) don't clearly permit
  redistribution.

```
