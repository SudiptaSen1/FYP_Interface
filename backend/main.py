import os
import torch
import re
import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import BertTokenizer, BertForSequenceClassification
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware

# ==========================================
# 1. ENVIRONMENT CONFIGURATION
# ==========================================
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ENG_MODEL_PATH = os.path.join(BASE_DIR, "bert_english_model")
BEN_MODEL_PATH = os.path.join(BASE_DIR, "bangla_bert_model")

# If MONGO_URI is empty or missing, fallback to localhost
MONGO_DETAILS = os.getenv("MONGO_URI") or "mongodb://localhost:27017"

ENG_MAX_LEN = 320
BEN_MAX_LEN = 128
BEN_LABEL_MAP = {0: "Normal", 1: "Normal", 2: "Depression"}

# Global dictionary to store models and DB connection
model_assets = {}

# ==========================================
# 2. LIFESPAN (STARTUP & SHUTDOWN)
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing system and loading models...")
    
    # --- Connect to MongoDB ---
    try:
        model_assets["mongo_client"] = AsyncIOMotorClient(MONGO_DETAILS)
        model_assets["db"] = model_assets["mongo_client"]["fyp_database"]
        # Trigger a quick command to verify connection
        await model_assets["mongo_client"].admin.command('ping')
        print(f"Connected to MongoDB at {MONGO_DETAILS}")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        raise e
    
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
    
    # --- Shutdown Cleanup ---
    model_assets["mongo_client"].close()
    model_assets.clear()
    print("System shut down securely.")

app = FastAPI(title="Multilingual Text Analysis API", lifespan=lifespan)

# Add this to allow the Next.js frontend to communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # Specifically allow your Next.js port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 3. DATA MODELS (SCHEMAS)
# ==========================================
class TextRequest(BaseModel):
    statement: str

class AnalysisResponse(BaseModel):
    detected_language: str
    prediction: str
    confidence: float

class FeedbackRequest(BaseModel):
    statement: str
    language: str
    original_prediction: str
    feedback_type: str # 'upvote' or 'downvote'
    corrected_prediction: Optional[str] = None # Optional correction

# ==========================================
# 4. HELPER FUNCTIONS
# ==========================================
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

# ==========================================
# 5. API ENDPOINTS
# ==========================================
@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_text(request: TextRequest):
    """Predicts sentiment/mental health status without saving to DB."""
    if not request.statement.strip():
        raise HTTPException(status_code=400, detail="Empty statement provided")

    try:
        lang = "Bengali" if is_bengali(request.statement) else "English"
        device = model_assets["device"]
        
        if lang == "English":
            clean_text = clean_english_text(request.statement)
            tokenizer = model_assets["eng_tok"]
            model = model_assets["eng_mod"]
            max_len = ENG_MAX_LEN
        else:
            clean_text = clean_bengali_text(request.statement)
            tokenizer = model_assets["ben_tok"]
            model = model_assets["ben_mod"]
            max_len = BEN_MAX_LEN
            
        inputs = tokenizer(
            clean_text, add_special_tokens=True, max_length=max_len,
            padding='max_length', truncation=True, return_tensors='pt'
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
            
        return AnalysisResponse(
            detected_language=lang,
            prediction=label,
            confidence=round(float(conf.item()), 4)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Handles user feedback to improve the model dataset."""
    try:
        db = model_assets["db"]
        
        # --- Separate Collections by Language ---
        if request.language.lower() == "english":
            collection_name = "english_predictions"
        elif request.language.lower() == "bengali":
            collection_name = "bengali_predictions"
        else:
            raise HTTPException(status_code=400, detail="Invalid language specified.")
            
        # --- Handle Upvotes ---
        if request.feedback_type.lower() == "upvote":
            document = {
                "statement": request.statement,
                "prediction": request.original_prediction,
                "feedback_type": "upvote",
                "is_user_corrected": False,
                "timestamp": datetime.now(timezone.utc)
            }
            
        # --- Handle Downvotes ---
        elif request.feedback_type.lower() == "downvote":
            # Check if they actually provided text
            has_correction = bool(request.corrected_prediction and request.corrected_prediction.strip())
            
            document = {
                "statement": request.statement,
                "original_prediction": request.original_prediction,
                "feedback_type": "downvote",
                "is_user_corrected": has_correction,
                "timestamp": datetime.now(timezone.utc)
            }
            
            # Only add the corrected_prediction field if they typed something
            if has_correction:
                document["corrected_prediction"] = request.corrected_prediction.strip()
                
        else:
            raise HTTPException(status_code=400, detail="feedback_type must be 'upvote' or 'downvote'")

        # --- Insert into the correct collection ---
        await db[collection_name].insert_one(document)
        
        return {"status": "success", "message": "Feedback recorded successfully."}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Multilingual API is live. Use /analyze to predict, and /feedback to correct."}