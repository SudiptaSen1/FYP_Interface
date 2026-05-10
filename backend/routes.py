from fastapi import APIRouter, HTTPException
from models import TextRequest, AnalysisResponse, FeedbackRequest
import controllers
from models import UserCreate, UserLogin, Token

router = APIRouter()

@router.get("/")
async def root():
    return {"message": "Multilingual API is live. Use /analyze to predict, and /feedback to correct."}

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_text(request: TextRequest):
    if not request.statement.strip():
        raise HTTPException(status_code=400, detail="Empty statement provided")
    try:
        result = await controllers.process_analysis(request.statement)
        return AnalysisResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    try:
        await controllers.process_feedback(request)
        return {"status": "success", "message": "Feedback recorded successfully."}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# ... (existing routes)

@router.post("/signup")
async def signup(user: UserCreate):
    return await controllers.create_user(user)

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    return await controllers.authenticate_user(credentials)

@router.post("/logout")
async def logout():
    """
    JWT is stateless. To log out, the frontend simply deletes the token 
    from local storage. This endpoint acts as a confirmation signal.
    """
    return {"message": "Successfully logged out. Please clear your local token."}