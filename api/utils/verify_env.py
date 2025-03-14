import os
import sys
from typing import List

def check_required_env_vars():
    """Checks that all required environment variables are present."""
    required_vars: List[str] = [
        "DATABASE_URL",
        "CLOUDINARY_CLOUD_NAME", 
        "CLOUDINARY_API_KEY", 
        "CLOUDINARY_API_SECRET"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"Error: The following environment variables are required: {', '.join(missing_vars)}")
        print("Please configure these variables in the .env file or in the system environment.")
        sys.exit(1)