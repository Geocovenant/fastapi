import time
import os
from fastapi import APIRouter
from dotenv import load_dotenv
from api.utils.cloudinary_utils import CloudinarySignatureResponse, generate_signature

# Load environment variables from .env file
load_dotenv()

cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
api_key = os.getenv("CLOUDINARY_API_KEY")
api_secret = os.getenv("CLOUDINARY_API_SECRET")

router = APIRouter()

@router.post("/generate_signature", response_model=CloudinarySignatureResponse)
async def generate_cloudinary_signature():
    timestamp = int(time.time())
    params = {
        "timestamp": str(timestamp),
    }
    signature = generate_signature(params, api_secret)
    return CloudinarySignatureResponse(
        signature=signature,
        timestamp=timestamp,
        api_key=api_key,
        cloud_name=cloud_name
    )
