# Attachment Forensics (Stage B2)

`attachment_forensics.py` analyzes attachment records produced by the email parser. It does static inspection; this module does **not** dynamically execute or detonate attachments in a sandbox.

## Input shape

Each attachment is expected to include a filename, declared MIME type and base64-encoded content. The current parser uses `content_bytes_b64`; common aliases are accepted by the helper functions.

```json
{
  "filename": "invoice.pdf",
  "content_type": "application/pdf",
  "content_bytes_b64": "..."
}
```

## Output

The module returns one result per attachment, including fields such as `filename`, `declared_type`, `sha256`, `size_bytes`, `actual_type`, `type_mismatch`, `has_macro`, `macro_behavior`, `suspicious`, `flags`, `ocr_text`, and `qr_urls`. Some fields can be empty or `null` when evidence is unavailable or the corresponding type of analysis does not apply.

## Checks performed

- SHA-256 hash and size calculation.
- Actual file type detection from file signatures, with optional `python-magic`/libmagic support and a built-in signature fallback.
- Comparison between declared and detected file types, with allowances for common Office-format variations.
- Double file extensions and executable content disguised under another extension.
- Static analysis of Office macro content through `oletools` where applicable. It looks for auto-execution entry points, suspicious API usage, and referenced indicators; it does not run the macro.
- Image OCR and QR-code extraction through the image-forensics module when dependencies/system libraries are available. Extracted text and URLs can contribute to later analysis stages.

A finding is evidence to review, not a definitive proof of maliciousness. File-type detectors have limits, and macro presence alone does not establish that a document will cause harm.

## Dependencies

The standard backend dependencies are installed with:

```powershell
python -m pip install -r requirements.txt
```

The Dockerfile installs `tesseract-ocr`, English OCR data and `libzbar0` for OCR/QR support. `python-magic` is optional and is not in `requirements.txt`; on systems with libmagic it can improve signature detection, but the built-in fallback remains available. Do not use `--break-system-packages` inside the project's virtual environment.

## Related code and tests

- `file_signatures.py` — signature detection and type-mismatch decisions.
- `macro_scan.py` — macro presence and static behavioral analysis.
- `image_forensics.py` — OCR/QR analysis.
- `attachment_forensics.py` — Stage B2 entry point (`analyze_attachments`).
- `../tests/test_attachment_forensics.py` — attachment type and filename cases.
- `../tests/test_macro_behavior.py` — macro-analysis behavior and output wiring.
- `../tests/test_image_forensics.py` — image-analysis tests.
- `../tests/test_b2_against_krish_fixture.py` — parser/attachment integration fixture test; the fixture is test data, not a production email corpus.

The current test suite covers synthetic cases and selected fixtures. Do not interpret this as comprehensive validation against every real-world attachment format.
