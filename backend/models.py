from pydantic import BaseModel
from typing import Optional
from pydantic import EmailStr

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
    corrected_prediction: Optional[str] = None

class UserCreate(BaseModel):
    name: str
    email: EmailStr  # Validates that it's a proper email format
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    name: str