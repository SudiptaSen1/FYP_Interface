import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ENG_MODEL_PATH = os.path.join(BASE_DIR, "bert_english_model")
BEN_MODEL_PATH = os.path.join(BASE_DIR, "bangla_bert_model")

MONGO_DETAILS = os.getenv("MONGO_URI") or "mongodb://localhost:27017"

ENG_MAX_LEN = 320
BEN_MAX_LEN = 128
BEN_LABEL_MAP = {0: "Normal", 1: "Depression", 2: "Anxiety"}

# --- Authentication Config ---
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("No SECRET_KEY set for JWT. Please set it in your .env file.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days

# --- Gemini Config ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY is not set in the .env file.")

# Global dictionary to store models and DB connection across the app
model_assets = {}