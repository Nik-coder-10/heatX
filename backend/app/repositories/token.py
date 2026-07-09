from sqlalchemy.orm import Session
from typing import Optional
from app.models.token import TokenBlacklist
from datetime import datetime

class TokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, token_jti: str, token_type: str, expires_at: datetime) -> TokenBlacklist:
        db_obj = TokenBlacklist(
            token_jti=token_jti,
            token_type=token_type,
            expires_at=expires_at,
        )
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def is_blacklisted(self, token_jti: str) -> bool:
        token = self.db.query(TokenBlacklist).filter(TokenBlacklist.token_jti == token_jti).first()
        if not token:
            return False
        # Check if token has expired
        if token.expires_at < datetime.utcnow():
            # Optionally, delete expired tokens
            self.db.delete(token)
            self.db.commit()
            return False
        return True

    def clean_expired(self) -> int:
        """Delete expired tokens and return count of deleted rows."""
        expired = self.db.query(TokenBlacklist).filter(TokenBlacklist.expires_at < datetime.utcnow()).all()
        count = len(expired)
        for token in expired:
            self.db.delete(token)
        self.db.commit()
        return count