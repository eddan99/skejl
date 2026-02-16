from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
MODELS_DIR = DATA_DIR / "models"

PRODUCTS_JSON = INPUT_DIR / "products.json"
CTR_DATASET_PATH = INPUT_DIR / "ctr_dataset.json"
RF_CTR_MODEL_PATH = MODELS_DIR / "rf_ctr_model.pkl"
CONVERSION_DB_JSON = DATA_DIR / "conversion_db.json"

RF_MODEL_PATH = MODELS_DIR / "rf_model.pkl"
LABEL_ENCODERS_PATH = MODELS_DIR / "label_encoders.pkl"
FEATURE_NAMES_PATH = MODELS_DIR / "feature_names.pkl"
FEATURE_COLUMNS_PATH = MODELS_DIR / "feature_columns.pkl"
METADATA_PATH = MODELS_DIR / "metadata.json"

def ensure_directories():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
