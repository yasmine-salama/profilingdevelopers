import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "app.db"
SAMPLE_DATA_PATH = DATA_DIR / "sample_developers.json"


class Config:
    SECRET_KEY = "dev-secret-key"
    DATABASE_PATH = DATABASE_PATH
    SAMPLE_DATA_PATH = SAMPLE_DATA_PATH
    GITHUB_API_BASE_URL = "https://api.github.com"
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
    REQUEST_TIMEOUT = 15
