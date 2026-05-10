import os
import torch
import re
import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import BertTokenizer, BertForSequenceClassification
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# --- Fixed Import ---
from datetime import datetime, timezone 
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

# --- Configuration ---
ENG_MODEL_PATH = "./bert_english_model"
BEN_MODEL_PATH = "./bangla_bert_model"

MONGO_DETAILS = os.getenv("MONGO_URI", "mongodb://localhost:27017")

ENG_MAX_LEN = 320
BEN_MAX_LEN = 128

BEN_LABEL_MAP = {0: "Normal", 1: "Normal", 2: "Depression"}

model_assets = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing system and loading models...")
    
    # --- Connect to MongoDB ---
    model_assets["mongo_client"] = AsyncIOMotorClient(MONGO_DETAILS)
    model_assets["db"] = model_assets["mongo_client"]["fyp_database"]
    print("Connected to MongoDB!")
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model_assets["device"] = device
    
    try:
        print("Loading English BERT...")
        model_assets["eng_tok"] = BertTokenizer.from_pretrained(ENG_MODEL_PATH)
        model_assets["eng_mod"] = BertForSequenceClassification.from_pretrained(ENG_MODEL_PATH).to(device)
        model_assets["eng_le"] = joblib.load(f"{ENG_MODEL_PATH}/label_encoder.joblib")
        model_assets["eng_mod"].eval()
        
        print("Loading Bengali BERT...")
        model_assets["ben_tok"] = BertTokenizer.from_pretrained(BEN_MODEL_PATH)
        model_assets["ben_mod"] = BertForSequenceClassification.from_pretrained(BEN_MODEL_PATH).to(device)
        model_assets["ben_mod"].eval()
        
        print(f"All models loaded successfully on {device}")
    except Exception as e:
        print(f"Error loading models: {e}")
        raise e
    
    yield
    model_assets["mongo_client"].close()
    model_assets.clear()

app = FastAPI(title="Multilingual Text Analysis API", lifespan=lifespan)

# --- Data Models ---
class TextRequest(BaseModel):
    statement: str

class AnalysisResponse(BaseModel):
    detected_language: str
    prediction: str
    confidence: float

# --- Helper Functions ---
def is_bengali(text: str) -> bool:
    return bool(re.search(r'[\u0980-\u09FF]', text))

def clean_english_text(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def clean_bengali_text(text: str) -> str:
    text = str(text)
    text = re.sub(r'http\S+|www\S+', '', text)
    text = re.sub(r'[A-Za-z0-9]', '', text) 
    text = re.sub(r'[^\u0980-\u09FF\s]', '', text) 
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# --- API Endpoints ---
@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_text(request: TextRequest):
    if not request.statement.strip():
        raise HTTPException(status_code=400, detail="Empty statement provided")

    try:
        lang = "Bengali" if is_bengali(request.statement) else "English"
        
        # --- FIX: Grab device and db from global state ---
        device = model_assets["device"]
        db = model_assets["db"] 
        
        if lang == "English":
            clean_text = clean_english_text(request.statement)
            tokenizer = model_assets["eng_tok"]
            model = model_assets["eng_mod"]
            max_len = ENG_MAX_LEN
            collection_name = "english_predictions" # --- FIX: Set collection name
            
        else:
            clean_text = clean_bengali_text(request.statement)
            tokenizer = model_assets["ben_tok"]
            model = model_assets["ben_mod"]
            max_len = BEN_MAX_LEN
            collection_name = "bengali_predictions" # --- FIX: Set collection name
            
        inputs = tokenizer(
            clean_text,
            add_special_tokens=True,
            max_length=max_len,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        ).to(device)
        
        with torch.no_grad():
            outputs = model(input_ids=inputs['input_ids'], attention_mask=inputs['attention_mask'])
            probs = torch.nn.functional.softmax(outputs.logits, dim=1)
            conf, pred_idx = torch.max(probs, dim=1)
            
        idx = pred_idx.item()
        
        if lang == "English":
            label = model_assets["eng_le"].inverse_transform([idx])[0]
        else:
            label = BEN_LABEL_MAP.get(idx, "Unknown")
            
        document = {
            "statement": request.statement,
            "prediction": label,
            "confidence": round(float(conf.item()), 4),
            "timestamp": datetime.now(timezone.utc)
        }
        
        # --- FIX: Insert into the correct dynamic collection ---
        await db[collection_name].insert_one(document)
            
        return AnalysisResponse(
            detected_language=lang,
            prediction=label,
            confidence=round(float(conf.item()), 4)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Multilingual API is live. Send a POST request to /analyze."}