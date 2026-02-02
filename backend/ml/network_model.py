import pandas as pd
from sklearn.tree import DecisionTreeRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import joblib
import os

# ---------- PATHS (ROBUST) ----------
BASE_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_DIR, "network_buffer_data.csv")
MODEL_PATH = os.path.join(BASE_DIR, "buffer_predictor.pkl")


def train_model():
    # Load dataset
    data = pd.read_csv(DATA_PATH)

    # Features and target
    X = data[
        ["bandwidth_kbps", "latency_ms", "jitter_ms", "packet_loss_pct"]
    ]
    y = data["forward_buffer_chunks"]

    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Train model
    model = DecisionTreeRegressor(
        max_depth=4,
        random_state=42
    )
    model.fit(X_train, y_train)

    # Evaluate
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)

    print(f"[ML] Model trained. MAE: {mae:.2f} chunks")

    # Save model
    joblib.dump(model, MODEL_PATH)
    print(f"[ML] Model saved to {MODEL_PATH}")


def predict_forward_buffer(network_metrics: dict) -> int:
    """
    Predict forward buffer size using trained ML model.
    """

    model = joblib.load(MODEL_PATH)

    import pandas as pd
    features = pd.DataFrame([network_metrics])

    prediction = model.predict(features)[0]

    # Safety bounds
    return max(1, int(round(prediction)))


if __name__ == "__main__":
    train_model()

