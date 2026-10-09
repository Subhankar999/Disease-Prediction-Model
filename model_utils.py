"""
model_utils.py - everything that touches the machine-learning model.
The UI (app.py) only calls the functions below.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

BUNDLE_PATH = Path(__file__).parent / "model" / "model_bundle.joblib"


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_bundle() -> dict:
    """
    Load the trained model bundle.
    If it is missing, or was saved by a different XGBoost version and cannot be
    read ("input stream corrupted"), it is deleted and retrained automatically.
    """
    if BUNDLE_PATH.exists():
        try:
            return joblib.load(BUNDLE_PATH)
        except Exception:
            BUNDLE_PATH.unlink(missing_ok=True)

    import train_model  # local script - trains from data/Training.csv

    train_model.main("cpu")
    return joblib.load(BUNDLE_PATH)


# --------------------------------------------------------------------------- #
# Pretty names
# --------------------------------------------------------------------------- #
def _auto_pretty(raw: str) -> str:
    s = re.sub(r"[_\s]+", " ", raw).strip()
    return s[:1].upper() + s[1:]


def symptom_label(raw: str, cfg: dict) -> str:
    return cfg.get("symptom_names", {}).get(raw) or _auto_pretty(raw)


def disease_label(raw: str, cfg: dict) -> str:
    return cfg.get("disease_names", {}).get(raw) or _auto_pretty(raw)


def symptom_options(bundle: dict, cfg: dict) -> list[str]:
    """Raw symptom keys shown in the UI (hidden / dead columns removed), sorted by label."""
    hidden = set(cfg.get("hidden_symptoms", []))
    opts = [f for f in bundle["features"] if f not in hidden]
    return sorted(opts, key=lambda r: symptom_label(r, cfg).lower())


# --------------------------------------------------------------------------- #
# Prediction
# --------------------------------------------------------------------------- #
def predict(bundle: dict, selected: list[str], top_k: int = 5) -> list[tuple[str, float]]:
    """Return [(disease, probability), ...] sorted high -> low."""
    features = bundle["features"]
    row = {f: 0 for f in features}
    for s in selected:
        if s in row:
            row[s] = 1
    x = pd.DataFrame([row], columns=features)

    proba = bundle["model"].predict_proba(x)[0]
    order = np.argsort(proba)[::-1][:top_k]
    classes = bundle["label_encoder"].inverse_transform(order)
    return [(str(c), float(proba[i])) for c, i in zip(classes, order)]


def explain(bundle: dict, disease: str, selected: list[str], n_missing: int = 6) -> dict:
    """
    Data-driven explanation: compare the user's symptoms with how often each
    symptom occurs for this disease in the training data.
    """
    typical: dict[str, float] = bundle["disease_symptoms"].get(disease, {})
    sel = set(selected)
    matched = [s for s in typical if s in sel]
    not_selected = [s for s in typical if s not in sel][:n_missing]
    unrelated = [s for s in selected if s not in typical]
    return {"matched": matched, "not_selected": not_selected, "unrelated": unrelated}


def confidence_level(p: float, cfg: dict) -> str:
    pc = cfg["prediction"]
    if p >= pc["high_confidence_threshold"]:
        return "high"
    if p >= pc["low_confidence_threshold"]:
        return "mid"
    return "low"


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def build_report(cfg: dict, selected: list[str], results: list[tuple[str, float]]) -> str:
    lines = [
        f"{cfg['app']['page_title']} - symptom analysis report",
        f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
        "",
        "SYMPTOMS ENTERED",
        *[f"  - {symptom_label(s, cfg)}" for s in selected],
        "",
        "MOST LIKELY CONDITIONS (model probability)",
        *[f"  {i}. {disease_label(d, cfg)} - {p * 100:.1f}%" for i, (d, p) in enumerate(results, 1)],
        "",
        "DISCLAIMER",
        " ".join(cfg["app"]["disclaimer"].split()),
    ]
    return "\n".join(lines)
