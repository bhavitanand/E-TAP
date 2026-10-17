# Email Dataset Manifests

The `set_01/` through `set_05/` directories currently contain JSON manifests. Each manifest describes the intended test messages by ID, expected relative path, format (`eml` or `msg`), label, category and approximate size.

The referenced raw email files are not included in this repository. The root `.gitignore` excludes `.eml` and `.msg` files, so a manifest is metadata for a curated corpus—not a guarantee that every listed file exists in a fresh clone. Any scripts that need those messages require you to supply authorized local test files separately.

The manifests aim to cover benign, phishing and spam cases across multiple scenarios and edge cases. They should be used as test labels, not as a claim that the corpus is representative of all real-world email.
