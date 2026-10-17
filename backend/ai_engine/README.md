# AI Engine — Metadata Triage and Stage G

This module provides a fast XGBoost metadata triage layer plus Gemini-assisted content/final assessment. Stage G combines the available normalized email content with the earlier pipeline evidence.

## Flow

1. The legacy content classifier in `main.py` can classify message content against the configured taxonomy.
2. `triage_model.py` predicts from six metadata features: attachment presence, URL count, sender-domain age when available, SPF result, subject length, and selected urgency indicators.
3. `stage_g.py` uses the evidence context—email content, headers, attachments, IOCs, threat intelligence and correlation—to produce the final interpretation when Gemini is invoked. Before a Gemini request, the pipeline sends a privacy-reduced copy with URL query/fragment details sanitized; the stored forensic evidence remains separate.
4. The pipeline skips Gemini only when the triage model is available, predicts benign at or above `TRIAGE_SAFE_THRESHOLD` (default `0.90`), and no heuristic override forces Stage G. Selected risky keywords and extracted URLs force Stage G.

The bundled XGBoost pickle should be treated as an initial triage aid, not a production-calibrated detection model. Validate false positives and false negatives against representative mail before relying on it for operational decisions. If the model is missing or cannot load, the pipeline fails open to the normal analysis path.

## Entry points

Full Stage G:

```python
from ai_engine.stage_g import analyze_with_stage_g

ai_analysis = analyze_with_stage_g(complete_context)
```

Legacy content-only classifier:

```python
from ai_engine.main import analyze_email

analysis = analyze_email(parsed_email_dict)
```

The main pipeline uses `analyze_with_stage_g()` for the final assessment where Stage G is required.

## Gemini configuration

Store configuration in the repository-root `.env` or the backend host's environment variables:

```dotenv
GEMINI_API_KEY=your-own-key-here
GEMINI_MODEL=gemini-3.5-flash-lite
```

The model setting must be a model identifier available to the configured API key; adjust it if the provider changes availability. Never commit `.env` or hard-code real credentials. If no Gemini key is configured or configured model calls fail, Stage G returns an explicit offline fallback result so the analysis pipeline can still return a report. B11 records provider/fallback state separately from the email verdict. The fallback is not equivalent to a live model assessment.

## Output shape

Stage G results are combined into the final `/analyze` response. Common fields include:

```json
{
  "content_classification": {
    "verdict": "Likely Malicious",
    "content_risk_score": 90,
    "confidence": 0.87,
    "attack_type": "Credential Phishing",
    "categories": [],
    "reasons": [],
    "suspicious_indicators": []
  },
  "final_assessment": {
    "verdict": "HIGH-RISK PHISHING",
    "risk_score": 94,
    "confidence": 0.82,
    "explanation": "...",
    "evidence_assessments": [],
    "supporting_evidence": [],
    "mitre_attack": []
  },
  "mitre_attack": []
}
```

This is illustrative, not a guaranteed literal response; values and optional keys vary with the artifact and fallback path.

## Files

- `prompts.py` — category taxonomy and classification prompts.
- `schemas.py` — Pydantic schemas for analysis output.
- `main.py` — Gemini client/model selection and legacy content classifier.
- `stage_g.py` — evidence synthesis, fallback scoring and MITRE-oriented mapping.
- `triage_model.py` — bundled XGBoost model loading and feature-based triage.
- `train_triage_model.py` — model-training utility; review its expected input data before running it.
