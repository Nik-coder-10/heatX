"""Authentication service — login, registration, token management."""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ExpiredToken, InvalidPassword, InvalidToken, TokenRevoked
from app.core.jwt import _create_token, create_access_token, create_refresh_token, decode_token
from app.core.password import get_password_hash, verify_password
from app.core.token_blacklist import add_token as blacklist_add
from app.models.user import User
from app.repositories.audit_repository import AuditLogRepository
from app.repositories.base import NotFoundError
from app.repositories.role_repository import RoleRepository
from app.repositories.token import TokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import Token
from app.schemas.user import UserCreate

logger = logging.getLogger("app.services.auth")


class AuthService:
    """Coordinates authentication workflows across repositories.

    Every sensitive action is audited. Passwords are never logged.
    Tokens are never logged.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.token_repo = TokenRepository(db)
        self.audit_repo = AuditLogRepository(db)
        self.role_repo = RoleRepository(db)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_user(
        self,
        user_in: UserCreate,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> User:
        """Register a new user account.

        Flow:
            1. Validate email uniqueness
            2. Validate username uniqueness
            3. Validate phone uniqueness (if provided)
            4. Hash the password
            5. Create the user record
            6. Assign default role (viewer)
            7. Audit log
            8. Return the user

        Returns:
            The created User ORM object.

        Raises:
            DuplicateError: If email, username, or phone already exists.
        """
        if self.user_repo.get_by_email(user_in.email):
            from app.repositories.base import DuplicateError
            raise DuplicateError(f"Email '{user_in.email}' is already registered")

        if self.user_repo.get_by_username(user_in.username):
            from app.repositories.base import DuplicateError
            raise DuplicateError(f"Username '{user_in.username}' is already taken")

        if user_in.phone:
            existing = self.user_repo.first(phone=user_in.phone)
            if existing:
                from app.repositories.base import DuplicateError
                raise DuplicateError(f"Phone '{user_in.phone}' is already registered")

        hashed = get_password_hash(user_in.password)
        user = self.user_repo.create({
            "email": user_in.email,
            "username": user_in.username,
            "hashed_password": hashed,
            "first_name": user_in.first_name,
            "last_name": user_in.last_name,
            "phone": user_in.phone,
            "is_active": True,
            "is_verified": False,
        })

        default_role = self.role_repo.get_by_name("viewer")
        if default_role:
            self.user_repo.assign_role(user.id, default_role.id)

        self.audit_repo.log_event(
            user_id=user.id,
            action="user.register",
            resource="auth",
            ip_address=ip_address,
            user_agent=user_agent,
            details={"email": user_in.email},
        )
        logger.info("User registered", extra={"user_id": str(user.id), "email": user_in.email})
        return user

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate_user(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
    ) -> User:
        """Authenticate a user by email and password.

        Flow:
            1. Lookup user by email
            2. Verify password
            3. Check user is not soft-deleted
            4. Check user is active
            5. Check user is verified (configurable)
            6. Update last_login
            7. Audit log success/failure
            8. Return user

        Raises:
            NotFoundError: If email is not found.
            InvalidPassword: If password is wrong.
            SecurityError: If account is disabled/deleted/unverified.
        """
        from app.core.exceptions import SecurityError

        user = self.user_repo.get_by_email(email, include_deleted=False)
        if not user:
            self.audit_repo.log_event(
                user_id=None,
                action="user.login.failed",
                resource="auth",
                ip_address=ip_address,
                details={"reason": "email_not_found", "email": email},
            )
            raise NotFoundError(f"No account found with email '{email}'")

        if not verify_password(password, user.hashed_password):
            self.audit_repo.log_event(
                user_id=user.id,
                action="user.login.failed",
                resource="auth",
                ip_address=ip_address,
                details={"reason": "wrong_password"},
            )
            raise InvalidPassword("Incorrect password")

        if user.deleted_at is not None:
            self.audit_repo.log_event(
                user_id=user.id,
                action="user.login.failed",
                resource="auth",
                ip_address=ip_address,
                details={"reason": "account_deleted"},
            )
            raise SecurityError("This account has been deactivated")

        if not user.is_active:
            self.audit_repo.log_event(
                user_id=user.id,
                action="user.login.failed",
                resource="auth",
                ip_address=ip_address,
                details={"reason": "account_inactive"},
            )
            raise SecurityError("This account has been deactivated")

        if not user.is_verified:
            self.audit_repo.log_event(
                user_id=user.id,
                action="user.login.failed",
                resource="auth",
                ip_address=ip_address,
                details={"reason": "email_not_verified"},
            )
            raise SecurityError("Email not verified. Please verify your email before logging in")

        self.user_repo.update_last_login(user.id)

        self.audit_repo.log_event(
            user_id=user.id,
            action="user.login",
            resource="auth",
            ip_address=ip_address,
            details={"email": email},
        )
        logger.info("User authenticated", extra={"user_id": str(user.id)})
        return user

    def login(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Token:
        """Authenticate and return token pair.

        Flow:
            1. authenticate_user() — validates credentials and account state
            2. Generate access token
            3. Generate refresh token
            4. Return Token schema

        Returns:
            Token with access_token, refresh_token, token_type.

        Raises:
            Same as authenticate_user().
        """
        user = self.authenticate_user(email, password, ip_address)

        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))

        logger.info("User logged in", extra={"user_id": str(user.id)})
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    def logout(
        self,
        access_token: str,
        refresh_token: str,
        user_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Log out a user by blacklisting both tokens.

        Flow:
            1. Decode access token to get exp claim
            2. Decode refresh token to get exp claim
            3. Blacklist both tokens
            4. Audit log

        Note:
            Token decode failures are silently ignored — the tokens
            are still considered logged out from the client perspective.
        """
        try:
            access_payload = decode_token(access_token)
            jti = access_payload.get("jti")
            exp = access_payload.get("exp")
            if jti and exp:
                expires_in = max(1, int(exp - datetime.now(timezone.utc).timestamp()))
                blacklist_add(jti, expires_in=expires_in)
        except (InvalidToken, ExpiredToken, TokenRevoked):
            pass

        try:
            refresh_payload = decode_token(refresh_token)
            jti = refresh_payload.get("jti")
            exp = refresh_payload.get("exp")
            if jti and exp:
                expires_in = max(1, int(exp - datetime.now(timezone.utc).timestamp()))
                blacklist_add(jti, expires_in=expires_in)

            if user_id is None and refresh_payload.get("sub"):
                user_id = uuid.UUID(refresh_payload["sub"])
        except (InvalidToken, ExpiredToken, TokenRevoked):
            pass

        self.audit_repo.log_event(
            user_id=user_id,
            action="user.logout",
            resource="auth",
            ip_address=ip_address,
            details={"method": "token_blacklist"},
        )
        logger.info("User logged out", extra={"user_id": str(user_id) if user_id else "unknown"})

    # ------------------------------------------------------------------
    # Token refresh
    # ------------------------------------------------------------------

    def refresh_access_token(
        self,
        refresh_token: str,
        ip_address: Optional[str] = None,
    ) -> Token:
        """Issue a new token pair from a valid refresh token.

        Flow:
            1. Decode and validate the refresh token
            2. Check token type is "refresh"
            3. Lookup user
            4. Verify user is active and not deleted
            5. Blacklist the old refresh token (rotation)
            6. Generate new access + refresh tokens
            7. Audit log
            8. Return new Token

        Raises:
            InvalidToken: If token type is wrong or token is malformed.
            ExpiredToken: If token has expired.
            TokenRevoked: If token is blacklisted.
            NotFoundError: If user no longer exists.
            SecurityError: If user is inactive or deleted.
        """
        from app.core.exceptions import SecurityError

        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise InvalidToken("Provided token is not a refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise InvalidToken("Token missing subject claim")

        user = self.user_repo.get_by_id(uuid.UUID(user_id))
        if not user:
            raise NotFoundError("User not found")

        if user.deleted_at is not None:
            raise SecurityError("Account has been deactivated")
        if not user.is_active:
            raise SecurityError("Account is inactive")

        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            expires_in = max(1, int(exp - datetime.now(timezone.utc).timestamp()))
            blacklist_add(jti, expires_in=expires_in)

        new_access = create_access_token(subject=str(user.id))
        new_refresh = create_refresh_token(subject=str(user.id))

        self.audit_repo.log_event(
            user_id=user.id,
            action="user.token.refresh",
            resource="auth",
            ip_address=ip_address,
        )
        logger.info("Access token refreshed", extra={"user_id": str(user.id)})
        return Token(
            access_token=new_access,
            refresh_token=new_refresh,
            token_type="bearer",
        )

    # ------------------------------------------------------------------
    # Password change
    # ------------------------------------------------------------------

    def change_password(
        self,
        user_id: uuid.UUID,
        old_password: str,
        new_password: str,
        ip_address: Optional[str] = None,
    ) -> None:
        """Change the user's password after verifying the current one.

        Flow:
            1. Lookup user
            2. Verify old password
            3. Hash new password
            4. Update password hash
            5. Audit log

        Raises:
            NotFoundError: If user does not exist.
            InvalidPassword: If old password is incorrect.

        Note:
            Token invalidation on password change requires adding a
            ``user_id`` column to ``TokenBlacklist``. This is a future
            enhancement tracked in the security roadmap.
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        if not verify_password(old_password, user.hashed_password):
            self.audit_repo.log_event(
                user_id=user_id,
                action="user.password.change.failed",
                resource="auth",
                ip_address=ip_address,
                details={"reason": "wrong_old_password"},
            )
            raise InvalidPassword("Current password is incorrect")

        new_hashed = get_password_hash(new_password)
        self.user_repo.change_password(user_id, new_hashed)

        self.audit_repo.log_event(
            user_id=user_id,
            action="user.password.change",
            resource="auth",
            ip_address=ip_address,
        )
        logger.info("Password changed", extra={"user_id": str(user_id)})

    # ------------------------------------------------------------------
    # Password reset
    # ------------------------------------------------------------------

    def forgot_password(
        self,
        email: str,
        ip_address: Optional[str] = None,
    ) -> str:
        """Generate a password-reset token for the given email.

        Flow:
            1. Lookup user by email (silently return if not found —
               prevents email enumeration)
            2. Generate a short-lived JWT reset token (15 minute expiry)
            3. Audit log
            4. Return the reset token

        Returns:
            Password reset token (JWT string).

        Security:
            Always returns a token regardless of whether the email exists
            to prevent email enumeration. The token for non-existent emails
            will be validated at reset time (user won't be found).
        """
        user = self.user_repo.get_by_email(email)
        reset_token = _create_token(
            subject=str(user.id) if user else "unknown",
            token_type="reset_password",
            expires_delta=timedelta(minutes=15),
        )

        self.audit_repo.log_event(
            user_id=user.id if user else None,
            action="user.password.reset.requested",
            resource="auth",
            ip_address=ip_address,
            details={"email": email},
        )

        if user:
            logger.info("Password reset requested", extra={"user_id": str(user.id), "email": email})

        return reset_token

    def reset_password(
        self,
        token: str,
        new_password: str,
        ip_address: Optional[str] = None,
    ) -> None:
        """Reset a password using a valid reset token.

        Flow:
            1. Decode the reset token
            2. Verify token type is "reset_password"
            3. Lookup user
            4. Hash new password
            5. Update password hash
            6. Audit log

        Raises:
            InvalidToken: If the token is invalid, expired, or wrong type.
            NotFoundError: If the user no longer exists.
        """
        payload = decode_token(token)
        if payload.get("type") != "reset_password":
            raise InvalidToken("Provided token is not a password reset token")

        user_id = payload.get("sub")
        if not user_id or user_id == "unknown":
            raise NotFoundError("User not found")

        user = self.user_repo.get_by_id(uuid.UUID(user_id))
        if not user:
            raise NotFoundError("User not found")

        new_hashed = get_password_hash(new_password)
        self.user_repo.change_password(user.id, new_hashed)

        self.audit_repo.log_event(
            user_id=user.id,
            action="user.password.reset",
            resource="auth",
            ip_address=ip_address,
        )
        logger.info("Password reset completed", extra={"user_id": str(user.id)})

    # ------------------------------------------------------------------
    # Email verification
    # ------------------------------------------------------------------

    def verify_email(
        self,
        token: str,
        ip_address: Optional[str] = None,
    ) -> None:
        """Verify a user's email address using a verification token.

        Flow:
            1. Decode the verification token
            2. Verify token type is "verify_email"
            3. Lookup user
            4. Mark email as verified
            5. Audit log

        Raises:
            InvalidToken: If token is invalid, expired, or wrong type.
            NotFoundError: If user no longer exists.
        """
        payload = decode_token(token)
        if payload.get("type") != "verify_email":
            raise InvalidToken("Provided token is not an email verification token")

        user_id = payload.get("sub")
        if not user_id:
            raise InvalidToken("Token missing subject claim")

        user = self.user_repo.verify_email(uuid.UUID(user_id))
        if not user:
            raise NotFoundError("User not found")

        self.audit_repo.log_event(
            user_id=user.id,
            action="user.email.verified",
            resource="auth",
            ip_address=ip_address,
        )
        logger.info("Email verified", extra={"user_id": str(user.id)})

    def resend_verification(
        self,
        user_id: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> str:
        """Generate a new email verification token.

        Flow:
            1. Lookup user
            2. Generate a short-lived JWT verification token (24 hour expiry)
            3. Audit log
            4. Return the verification token

        Returns:
            Email verification token (JWT string).
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        verify_token = _create_token(
            subject=str(user.id),
            token_type="verify_email",
            expires_delta=timedelta(hours=24),
        )

        self.audit_repo.log_event(
            user_id=user.id,
            action="user.email.verification.resend",
            resource="auth",
            ip_address=ip_address,
        )
        logger.info("Verification email resent", extra={"user_id": str(user.id)})
        return verify_token

    # ------------------------------------------------------------------
    # Token validation
    # ------------------------------------------------------------------

    def validate_access_token(self, token: str) -> dict:
        """Validate an access token.

        Flow:
            1. Decode the token (validates signature, expiration, blacklist)
            2. Check token type is "access"
            3. Return payload

        Returns:
            Decoded token payload dict.

        Raises:
            InvalidToken: If token is not an access token.
            ExpiredToken: If token has expired.
            TokenRevoked: If token is blacklisted.
        """
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise InvalidToken("Provided token is not an access token")
        return payload

    def validate_refresh_token(self, token: str) -> dict:
        """Validate a refresh token.

        Flow:
            1. Decode the token (validates signature, expiration, blacklist)
            2. Check token type is "refresh"
            3. Return payload

        Returns:
            Decoded token payload dict.

        Raises:
            InvalidToken: If token is not a refresh token.
            ExpiredToken: If token has expired.
            TokenRevoked: If token is blacklisted.
        """
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise InvalidToken("Provided token is not a refresh token")
        return payload

    # ------------------------------------------------------------------
    # Token revocation
    # ------------------------------------------------------------------

    def revoke_token(
        self,
        token: str,
        user_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Revoke a specific token by adding it to the blacklist.

        Flow:
            1. Decode the token
            2. Blacklist the JTI
            3. Audit log

        Note:
            If the token is already expired or invalid, the operation
            still succeeds from the caller's perspective.
        """
        try:
            payload = decode_token(token)
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                expires_in = max(1, int(exp - datetime.now(timezone.utc).timestamp()))
                blacklist_add(jti, expires_in=expires_in)

            if user_id is None and payload.get("sub"):
                user_id = uuid.UUID(payload["sub"])
        except (InvalidToken, ExpiredToken, TokenRevoked):
            pass

        self.audit_repo.log_event(
            user_id=user_id,
            action="user.token.revoked",
            resource="auth",
            ip_address=ip_address,
        )
        logger.info("Token revoked", extra={"user_id": str(user_id) if user_id else "unknown"})
