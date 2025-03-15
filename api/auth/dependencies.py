import os
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select
from api.database import get_session
from api.public.user.models import User, Session as UserSession
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from jose import jwt, jwe
import json
from datetime import datetime

AUTHJS_SECRET = os.getenv("AUTHJS_SECRET")
AUTHJS_SALT = os.getenv("AUTHJS_SALT")

# Configure HTTPBearer to extract the token from the Authorization header
security = HTTPBearer()

def get_derived_encryption_key(secret: str, salt: str) -> bytes:
    """
    Derives a 64-byte encryption key using HKDF for A256CBC-HS512.
    
    Args:
        secret (str): The Auth.js secret (AUTHJS_SECRET).
        salt (str): The salt, typically the cookie name.
    
    Returns:
        bytes: 64-byte derived key.
    """
    salt_bytes = salt.encode('utf-8')
    info_string = f"Auth.js Generated Encryption Key ({salt})".encode('utf-8')
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=64,  # 64 bytes for A256CBC-HS512
        salt=salt_bytes,
        info=info_string
    )
    key = hkdf.derive(secret.encode('utf-8'))
    return key

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_session)
):
    token = credentials.credentials
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No token provided")

    try:
        # Derive the encryption key
        derived_key = get_derived_encryption_key(AUTHJS_SECRET, AUTHJS_SALT)

        # Decrypt the JWE with the derived key
        decrypted_token = jwe.decrypt(token, derived_key)
        print('decrypted_token', decrypted_token)
        
        token_data = json.loads(decrypted_token.decode('utf-8'))
        
        email = token_data.get("email")
        
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: email not found")
        
        user = db.exec(select(User).where(User.email == email)).first()
        
        if not user:
            print(f"Creating new user with email: {email}")
            
            name = token_data.get("name")
            picture = token_data.get("picture")
            
            new_user = User(
                email=email,
                name=name,
                image=picture,
                emailVerified=datetime.now(),
                created_at=datetime.now(),
                updated_at=datetime.now(),
                last_login=datetime.now()
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            user = new_user
            
        return user
    except (jwe.JWEError, jwt.JWTError, json.JSONDecodeError) as e:
        print("Error al procesar el token:", str(e))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

async def get_current_user_optional(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_session)
) -> User | None:
    if not authorization:
        return None
    
    # Crear un objeto HTTPAuthorizationCredentials simulado
    try:
        # Extraer el token de Bearer <token>
        token = authorization.split(" ")[1] if authorization.startswith("Bearer ") else authorization
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        
        # Llamar a get_current_user con el objeto credentials
        return await get_current_user(credentials=credentials, db=db)
    except (IndexError, HTTPException, AttributeError):
        return None
