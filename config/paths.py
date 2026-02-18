from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
MODELS_DIR = DATA_DIR / "models"

PRODUCTS_JSON = INPUT_DIR / "products.json"
CTR_DATASET_PATH = INPUT_DIR / "ctr_dataset.json"
RF_CTR_MODEL_PATH = MODELS_DIR / "rf_ctr_model.pkl"
FEATURE_COLUMNS_PATH = MODELS_DIR / "feature_columns.pkl"

def ensure_directories():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
