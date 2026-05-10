import re
import torch
import bcrypt
from datetime import datetime, timezone
from config import model_assets, ENG_MAX_LEN, BEN_MAX_LEN, BEN_LABEL_MAP
# Add these imports at the top
from passlib.context import CryptContext
import jwt
from datetime import timedelta
from fastapi import HTTPException
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
import google.generativeai as genai
from config import GEMINI_API_KEY

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    
# Define the AI's personality and safety boundaries
SYSTEM_INSTRUCTION = """
You are MindFlow, a highly compassionate, empathetic, and supportive mental health AI assistant.
Your goal is to provide a safe space for users to chat, offer healthy coping mechanisms, and provide a listening ear.

CRITICAL RULES:
1. You are NOT a licensed medical professional, therapist, or psychiatrist. You cannot diagnose conditions or prescribe medication.
2. If a user asks for medical advice, gently remind them of your AI nature and suggest speaking to a professional.
3. If the user indicates severe depression, self-harm, or suicidal thoughts, you MUST immediately express deep concern and strongly advise them to consult a doctor, call an emergency hotline, or reach out to a trusted loved one. 
4. Keep your responses conversational, concise, and warm. Avoid sounding like a textbook.
"""

# Set up the password hasher
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str):
    # bcrypt requires bytes, so we encode the strings
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )

def get_password_hash(password: str):
    # Generate a salt and hash the password
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    
    # Decode back to a string so MongoDB can save it properly
    return hashed_password.decode('utf-8')

def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

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

# --- Core Business Logic ---
async def process_analysis(statement: str):
    """Handles the ML inference logic."""
    lang = "Bengali" if is_bengali(statement) else "English"
    device = model_assets["device"]
    
    if lang == "English":
        clean_text = clean_english_text(statement)
        tokenizer = model_assets["eng_tok"]
        model = model_assets["eng_mod"]
        max_len = ENG_MAX_LEN
    else:
        clean_text = clean_bengali_text(statement)
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
        
    return {
        "detected_language": lang,
        "prediction": label,
        "confidence": round(float(conf.item()), 4)
    }

async def process_feedback(feedback_data):
    """Handles saving feedback to MongoDB."""
    db = model_assets["db"]
    
    if feedback_data.language.lower() == "english":
        collection_name = "english_predictions"
    elif feedback_data.language.lower() == "bengali":
        collection_name = "bengali_predictions"
    else:
        raise ValueError("Invalid language specified.")
        
    if feedback_data.feedback_type.lower() == "upvote":
        document = {
            "statement": feedback_data.statement,
            "prediction": feedback_data.original_prediction,
            "feedback_type": "upvote",
            "is_user_corrected": False,
            "timestamp": datetime.now(timezone.utc)
        }
    elif feedback_data.feedback_type.lower() == "downvote":
        has_correction = bool(feedback_data.corrected_prediction and feedback_data.corrected_prediction.strip())
        document = {
            "statement": feedback_data.statement,
            "original_prediction": feedback_data.original_prediction,
            "feedback_type": "downvote",
            "is_user_corrected": has_correction,
            "timestamp": datetime.now(timezone.utc)
        }
        if has_correction:
            document["corrected_prediction"] = feedback_data.corrected_prediction.strip()
    else:
        raise ValueError("feedback_type must be 'upvote' or 'downvote'")

    await db[collection_name].insert_one(document)
    

# --- Add these New Authentication Controllers at the bottom ---

async def create_user(user_data):
    """Handles User Registration."""
    db = model_assets["db"]
    users_collection = db["users"]
    
    # 1. Check if user already exists
    existing_user = await users_collection.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    # 2. Hash the password and save
    hashed_password = get_password_hash(user_data.password)
    new_user = {
        "name": user_data.name,
        "email": user_data.email,
        "password": hashed_password,
        "created_at": datetime.now(timezone.utc)
    }
    await users_collection.insert_one(new_user)
    return {"message": "User created successfully"}

async def authenticate_user(login_data):
    """Handles User Login and Token Generation."""
    db = model_assets["db"]
    users_collection = db["users"]
    
    # 1. Find user by email
    user = await users_collection.find_one({"email": login_data.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    # 2. Verify password
    if not verify_password(login_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    # 3. Generate JWT Token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]}, 
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "name": user["name"]
    }
    
# --- Add this new Chat Controller at the bottom ---
async def process_chat(chat_data):
    """Handles the conversation with Gemini."""
    if not GEMINI_API_KEY:
        raise ValueError("Gemini API key is not configured on the server.")

    # Initialize the model with our specific instructions
    chat_model = genai.GenerativeModel(
        model_name="gemini-3-flash-preview", 
        system_instruction=SYSTEM_INSTRUCTION
    )

    formatted_history = []
    
    # THE FIX: Gemini requires the history to START with a 'user' message. 
    # If the frontend passes the MindFlow greeting first ('model'), 
    # we prepend a hidden user message to satisfy Gemini's strict rules.
    if chat_data.history and chat_data.history[0].role == "model":
        formatted_history.append({
            "role": "user",
            "parts": ["Hello, I need someone to talk to."]
        })

    # Convert our Pydantic history format into the format Gemini expects
    for msg in chat_data.history:
        formatted_history.append({
            "role": msg.role,
            "parts": [msg.content]
        })

    try:
        # Start the chat session with the valid history
        chat_session = chat_model.start_chat(history=formatted_history)
        
        # Send the new message
        response = chat_session.send_message(chat_data.message)
        
        return {"reply": response.text}
    except Exception as e:
        # Print the actual error to your terminal so we can see it if it fails again!
        print(f"GEMINI ERROR: {str(e)}") 
        raise Exception(f"Failed to communicate with Gemini: {str(e)}")