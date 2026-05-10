import torch
import joblib
from fastapi import FastAPI
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from transformers import BertTokenizer, BertForSequenceClassification
from fastapi.middleware.cors import CORSMiddleware

# Import from our new modules
import config
from routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing system and loading models...")
    
    # --- Connect to MongoDB ---
    try:
        config.model_assets["mongo_client"] = AsyncIOMotorClient(config.MONGO_DETAILS)
        config.model_assets["db"] = config.model_assets["mongo_client"]["fyp_database"]
        await config.model_assets["mongo_client"].admin.command('ping')
        print(f"Connected to MongoDB at {config.MONGO_DETAILS}")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        raise e
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    config.model_assets["device"] = device
    
    # --- Load Models ---
    try:
        print("Loading English BERT...")
        config.model_assets["eng_tok"] = BertTokenizer.from_pretrained(config.ENG_MODEL_PATH)
        config.model_assets["eng_mod"] = BertForSequenceClassification.from_pretrained(config.ENG_MODEL_PATH).to(device)
        config.model_assets["eng_le"] = joblib.load(f"{config.ENG_MODEL_PATH}/label_encoder.joblib")
        config.model_assets["eng_mod"].eval()
        
        print("Loading Bengali BERT...")
        config.model_assets["ben_tok"] = BertTokenizer.from_pretrained(config.BEN_MODEL_PATH)
        config.model_assets["ben_mod"] = BertForSequenceClassification.from_pretrained(config.BEN_MODEL_PATH).to(device)
        config.model_assets["ben_mod"].eval()
        
        print(f"All models loaded successfully on {device}")
    except Exception as e:
        print(f"Error loading models: {e}")
        raise e
    
    yield
    
    # --- Shutdown Cleanup ---
    config.model_assets["mongo_client"].close()
    config.model_assets.clear()
    print("System shut down securely.")

# Initialize App
app = FastAPI(title="Multilingual Text Analysis API", lifespan=lifespan)

# Setup CORS
# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ], 
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (POST, GET, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Register Routes
app.include_router(router)