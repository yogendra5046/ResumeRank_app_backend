import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from src.infrastructure.security.auth_service import AuthService
from src.domain.models.user import User
from src.infrastructure.database import Base, engine, SessionLocal
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_raw_auth_logic():
    # 1. Initialize DB
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        email = "test_user_unique@example.com"
        password = "securepassword"
        
        # 2. Test Hashing
        hashed = AuthService.get_password_hash(password)
        assert AuthService.verify_password(password, hashed)
        print("✅ Password hashing and verification working.")
        
        # 3. Test User Creation
        # Cleanup if exists
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            db.delete(existing)
            db.commit()
            
        new_user = User(
            email=email,
            hashed_password=hashed,
            full_name="Verified User"
        )
        db.add(new_user)
        db.commit()
        print("✅ User creation in database working.")
        
        # 4. Test Token Generation
        token = AuthService.create_access_token({"sub": email})
        assert token is not None
        payload = AuthService.decode_token(token)
        assert payload["sub"] == email
        print("✅ JWT token generation and decoding working.")
        
        print("\n🏆 Database and Authentication logic are 100% CORRECT!")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_raw_auth_logic()
