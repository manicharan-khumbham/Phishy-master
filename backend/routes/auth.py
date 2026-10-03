import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Header, Query
from pydantic import BaseModel, EmailStr, Field
from fastapi.responses import JSONResponse

from database import get_db_connection, hash_password, verify_password

router = APIRouter()
logger = logging.getLogger(__name__)

# Request & Response Models
class UserRegisterRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Password (min 6 chars)")
    full_name: Optional[str] = Field(None, description="Full name")
    role: Optional[str] = Field("user", description="User role (user, admin, analyst)")

class UserLoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="Password")

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    role: str = "user"
    created_at: str
    last_login: Optional[str] = None

class AuthResponse(BaseModel):
    status: str
    message: str
    token: str
    user: UserResponse

@router.post("/register", response_model=AuthResponse)
def register_user(request: UserRegisterRequest):
    """
    Register a new user in SQLite database
    """
    email_clean = request.email.lower().strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT id FROM users WHERE email = ?", (email_clean,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    now = datetime.now(timezone.utc).isoformat()
    pw_hash = hash_password(request.password)
    
    user_role = request.role or "user"
    cursor.execute("""
        INSERT INTO users (email, password_hash, full_name, role, created_at, last_login)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (email_clean, pw_hash, request.full_name or email_clean.split('@')[0].capitalize(), user_role, now, now))
    
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    user_data = UserResponse(
        id=user_id,
        email=email_clean,
        full_name=request.full_name or email_clean.split('@')[0].capitalize(),
        role=user_role,
        created_at=now,
        last_login=now
    )
    
    # Simple bearer token representation
    token = f"phishy-token-{user_id}-{email_clean}"
    
    logger.info(f"Registered new user in SQLite DB: {email_clean} (ID: {user_id})")
    
    return AuthResponse(
        status="success",
        message="Registration successful",
        token=token,
        user=user_data
    )

@router.post("/login", response_model=AuthResponse)
def login_user(request: UserLoginRequest):
    """
    Authenticate user against SQLite database
    """
    email_clean = request.email.lower().strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE email = ?", (email_clean,))
    row = cursor.fetchone()
    
    if not row or not verify_password(request.password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    now = datetime.now(timezone.utc).isoformat()
    cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, row["id"]))
    conn.commit()
    conn.close()
    
    user_data = UserResponse(
        id=row["id"],
        email=row["email"],
        full_name=row["full_name"],
        role=row["role"],
        created_at=row["created_at"],
        last_login=now
    )
    
    token = f"phishy-token-{row['id']}-{row['email']}"
    
    logger.info(f"User logged in from SQLite DB: {email_clean}")
    
    return AuthResponse(
        status="success",
        message="Login successful",
        token=token,
        user=user_data
    )

@router.get("/users")
def get_all_users():
    """
    Get list of all users stored in SQLite database
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, email, full_name, role, created_at, last_login 
        FROM users 
        ORDER BY id ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    
    users = [dict(row) for row in rows]
    return JSONResponse(content={
        "status": "success",
        "total_users": len(users),
        "users": users
    })

@router.get("/me")
def get_current_user_profile(user_email: Optional[str] = Query(None)):
    """
    Get profile for current user or default user
    """
    if not user_email:
        user_email = "john.doe@company.com"
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, full_name, role, created_at, last_login FROM users WHERE email = ?", (user_email.lower().strip(),))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
        
    return JSONResponse(content={
        "status": "success",
        "user": dict(row)
    })

@router.delete("/users/{user_id}")
def delete_user(user_id: int):
    """
    Delete a user from SQLite database
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    return JSONResponse(content={
        "status": "success",
        "message": f"User {user_id} deleted successfully"
    })
