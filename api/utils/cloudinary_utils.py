import hashlib
import hmac
from sqlmodel import SQLModel

class CloudinarySignatureResponse(SQLModel):
    signature: str
    timestamp: int
    api_key: str
    cloud_name: str


def generate_signature(params: dict, api_secret: str) -> str:
    # Sort the parameters alphabetically
    sorted_params = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    # Add the api_secret at the end of the string
    string_to_sign = f"{sorted_params}{api_secret}"
    # Generate the SHA-1 signature
    signature = hashlib.sha1(string_to_sign.encode('utf-8')).hexdigest()
    return signature