import secrets
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import AppUser, PasswordResetToken

class AuthService:
    @staticmethod
    def create_reset_token(db: Session, user_id: str) -> str:
        # Generate secure token
        token = secrets.token_urlsafe(32)
        
        # Expire old tokens for this user
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.is_used == False
        ).update({"is_used": True})
        
        # Create new token (expires in 1 hour)
        reset_token = PasswordResetToken(
            id=secrets.token_urlsafe(16),
            user_id=user_id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.add(reset_token)
        db.commit()
        
        return token
    
    @staticmethod
    def verify_reset_token(db: Session, token: str) -> PasswordResetToken | None:
        reset_token = db.query(PasswordResetToken).filter(
            PasswordResetToken.token == token,
            PasswordResetToken.is_used == False,
            PasswordResetToken.expires_at > datetime.utcnow()
        ).first()
        
        return reset_token
