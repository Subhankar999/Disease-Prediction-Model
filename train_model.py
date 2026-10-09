"""
Train the disease-prediction model and save everything the Streamlit app needs.

Usage:
    python train_model.py                 # CPU (default)
    python train_model.py --device cuda   # GPU, like in the original notebook

The model, hyper-parameters and 132-symptom feature layout are identical to the
original notebook (XGBoost, 100 trees, max_depth=9). The only difference is that
everything is bundled into ONE file (model/model_bundle.joblib).
"""
import argparse
from pathlib import Path

import joblib
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import LabelEncoder

ROOT = Path(__file__).parent
N_FEATURES = 132


def main(device: str) -> None:
    train = pd.read_csv(ROOT / "data" / "Training.csv")
    test = pd.read_csv(ROOT / "data" / "Testing.csv")

    features = list(train.columns[:N_FEATURES])
    x_train, x_test = train[features], test[features]

    # strip stray whitespace in labels ("Diabetes ", "Hypertension ")
    y_raw_train = train["prognosis"].str.strip()
    y_raw_test = test["prognosis"].str.strip()

    le = LabelEncoder()
    y_train = le.fit_transform(y_raw_train)
    y_test = le.transform(y_raw_test)

    model = xgb.XGBClassifier(
        n_estimators=100,
        random_state=42,
        device=device,
        max_depth=9,
        tree_method="hist",
        booster="gbtree",
    )
    model.fit(x_train, y_train)

    y_pred = model.predict(x_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Model accuracy on Testing.csv: {acc * 100:.2f}%")

    report = classification_report(
        y_test, y_pred, labels=range(len(le.classes_)),
        target_names=le.classes_, output_dict=True, zero_division=0,
    )

    # For every disease: how often each symptom occurs in the training data.
    # The app uses this to explain a prediction (data-derived, not hand-written).
    freq = (
        pd.concat([x_train, y_raw_train.rename("disease")], axis=1)
        .groupby("disease")[features].mean()
    )
    disease_symptoms = {
        d: freq.loc[d][freq.loc[d] > 0].sort_values(ascending=False).round(3).to_dict()
        for d in freq.index
    }

    bundle = {
        "model": model.set_params(device="cpu"),  # always load on CPU in the app
        "label_encoder": le,
        "features": features,
        "classes": list(le.classes_),
        "test_accuracy": float(acc),
        "n_train_rows": int(len(train)),
        "n_test_rows": int(len(test)),
        "feature_importance": dict(zip(features, map(float, model.feature_importances_))),
        "classification_report": report,
        "disease_symptoms": disease_symptoms,
    }
    out = ROOT / "model" / "model_bundle.joblib"
    joblib.dump(bundle, out, compress=3)
    print(f"Saved -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    main(ap.parse_args().device)
