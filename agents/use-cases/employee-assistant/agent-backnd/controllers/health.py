from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def get():
    """
    Health check endpoint to verify if the service is running.
    
    Returns:
        str: A simple "ok" message indicating the service is healthy.
    """
    return "ok"
