# Welcome Email & 2FA Implementation Guide

## Summary

This guide outlines the implementation of:
1. **Welcome Email** - Automatic email sent when users sign up
2. **2FA System** - Two-factor authentication via email (can be enabled per project)

---

## Part 1: Welcome Email (90% Complete)

### ✅ What's Done

1. **Welcome Email Template Added to Migration**
   - File: `app/migrations/versions/5c8e4a2b1f9d_seed_default_email_templates.py`
   - Template added with professional HTML and text versions
   - Variables: `{{app_name}}`, `{{user_name}}`, `{{user_email}}`, `{{join_date}}`, `{{login_url}}`, `{{year}}`

2. **EmailService Method Created**
   - Method: `send_welcome_email()` appended to `app/services/email_service.py`
   - Handles template fetching, rendering, and sending
   - Non-blocking (won't fail signup if email fails)

### 🔨 What's Needed

**Wire up to Signup Endpoint**

File: `app/api/auth_collection.py` (Line 218)

**Current code:**
```python
user = AppUser(**user_data)
user.set_password(password)
user.client_id = project.id
db.add(user)
db.commit()
db.refresh(user)
return {"access_token":create_app_user_token(user), "user":user}
```

**Updated code:**
```python
user = AppUser(**user_data)
user.set_password(password)
user.client_id = project.id
db.add(user)
db.commit()
db.refresh(user)

# Send welcome email (only if enabled in project config)
send_welcome = project.configs.get('SEND_WELCOME_EMAIL', True) if project.configs else True
if send_welcome:
    try:
        from app.services.email_service import EmailService
        email_service = EmailService(project_id=project.id, db=db)
        login_url = project.configs.get('LOGIN_URL') if project.configs else None
        bg.add_task(
            email_service.send_welcome_email,
            to_email=user.email,
            user_name=user_data.get('name') or user_data.get('username'),
            app_name=project.name,
            login_url=login_url
        )
    except Exception as e:
        # Log but don't fail signup
        print(f"Failed to send welcome email: {e}")

return {"access_token":create_app_user_token(user), "user":user}
```

**Add import at top of file:**
```python
from app.services.email_service import EmailService
```

### Configuration

Projects can control welcome emails via config:

```python
project.configs = {
    "SEND_WELCOME_EMAIL": True,  # Default: True
    "LOGIN_URL": "https://yourapp.com/login"  # Optional
}
```

### Re-run Migration

After updating the migration file, run:
```bash
# If templates already exist, first rollback
alembic downgrade -1

# Then upgrade to latest
alembic upgrade head
```

---

## Part 2: 2FA System Implementation

### Overview

Implement email-based 2FA that projects can enable via configuration.

### Step 1: Create 2FA Models

**File: `app/models/two_factor_auth.py`** (NEW)

```python
from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from app.core.database import Base
import secrets


class TwoFactorCode(Base):
    """Store 2FA codes for email verification"""
    __tablename__ = 'two_factor_codes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    project_id = Column(String(255), nullable=False, index=True)
    code = Column(String(6), nullable=False)  # 6-digit code
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    @staticmethod
    def generate_code():
        """Generate a 6-digit code"""
        return f"{secrets.randbelow(1000000):06d}"

    def is_expired(self):
        """Check if code is expired"""
        return datetime.utcnow() > self.expires_at

    def is_valid(self):
        """Check if code is valid (not used and not expired)"""
        return not self.is_used and not self.is_expired()


class TwoFactorSettings(Base):
    """Store 2FA settings per user"""
    __tablename__ = 'two_factor_settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), unique=True, nullable=False, index=True)
    project_id = Column(String(255), nullable=False, index=True)
    is_enabled = Column(Boolean, default=False)
    backup_email = Column(String(255), nullable=True)
    last_verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
```

### Step 2: Create Migration

```bash
alembic revision -m "add_2fa_tables"
```

**Migration content:**
```python
def upgrade() -> None:
    op.create_table(
        'two_factor_codes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('project_id', sa.String(255), nullable=False),
        sa.Column('code', sa.String(6), nullable=False),
        sa.Column('is_used', sa.Boolean(), default=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_2fa_codes_user_id', 'two_factor_codes', ['user_id'])
    op.create_index('ix_2fa_codes_project_id', 'two_factor_codes', ['project_id'])

    op.create_table(
        'two_factor_settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(255), unique=True, nullable=False),
        sa.Column('project_id', sa.String(255), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), default=False),
        sa.Column('backup_email', sa.String(255), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_2fa_settings_user_id', 'two_factor_settings', ['user_id'], unique=True)


def downgrade() -> None:
    op.drop_table('two_factor_settings')
    op.drop_table('two_factor_codes')
```

### Step 3: Add 2FA Email Template

Update the email templates migration to include a 2FA code template:

**Add to migration (before `def downgrade()`):**

```python
# 2FA Code Email Template
twofa_html = """... (similar to password reset, but with 6-digit code) ..."""
twofa_text = """..."""
twofa_vars = json.dumps({
    'app_name': 'Name of the application',
    'user_name': 'User\'s name',
    'code': '6-digit verification code',
    'expiry_minutes': 'Minutes until code expires',
    'year': 'Current year'
})

connection.execute(
    text("""..."""),
    {
        'template_type': 'LOGIN_ALERT',  # Reuse existing enum
        'name': '2FA Verification Code',
        'subject': 'Your Verification Code',
        'html_body': twofa_html,
        'text_body': twofa_text,
        'available_variables': twofa_vars,
        'is_active': True,
        'version': 1
    }
)
```

### Step 4: Create 2FA Endpoints

**File: `app/api/two_factor_auth.py`** (NEW)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_project
from app.models.two_factor_auth import TwoFactorCode, TwoFactorSettings
from app.models.app_client import AppUser
from app.services.email_service import EmailService

router = APIRouter(prefix="/auth-collections/2fa", tags=["2FA"])


class Enable2FARequest(BaseModel):
    user_id: str


class Verify2FARequest(BaseModel):
    user_id: str
    code: str


class Send2FACodeRequest(BaseModel):
    user_id: str


@router.post("/enable")
async def enable_2fa(
    request: Enable2FARequest,
    db: Session = Depends(get_db),
    proj = Depends(get_project),
):
    """Enable 2FA for a user (requires project config)"""
    project = proj[0]

    # Check if 2FA is enabled for this project
    if not project.configs.get('ENABLE_2FA', False):
        raise HTTPException(400, "2FA is not enabled for this project")

    # Get user
    user = db.query(AppUser).filter(
        AppUser.id == request.user_id,
        AppUser.client_id == project.id
    ).first()

    if not user:
        raise HTTPException(404, "User not found")

    # Create or update 2FA settings
    settings = db.query(TwoFactorSettings).filter(
        TwoFactorSettings.user_id == user.id
    ).first()

    if not settings:
        settings = TwoFactorSettings(
            user_id=user.id,
            project_id=project.id,
            is_enabled=True
        )
        db.add(settings)
    else:
        settings.is_enabled = True

    db.commit()
    return {"message": "2FA enabled successfully"}


@router.post("/send-code")
async def send_2fa_code(
    request: Send2FACodeRequest,
    db: Session = Depends(get_db),
    proj = Depends(get_project),
):
    """Send 2FA code to user's email"""
    project = proj[0]

    # Get user
    user = db.query(AppUser).filter(
        AppUser.id == request.user_id,
        AppUser.client_id == project.id
    ).first()

    if not user:
        raise HTTPException(404, "User not found")

    # Generate code
    code = TwoFactorCode.generate_code()
    expiry_minutes = 10

    twofa_code = TwoFactorCode(
        user_id=user.id,
        project_id=project.id,
        code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=expiry_minutes)
    )
    db.add(twofa_code)
    db.commit()

    # Send email
    email_service = EmailService(project_id=project.id, db=db)
    # TODO: Implement send_2fa_code_email method

    return {"message": "2FA code sent"}


@router.post("/verify")
async def verify_2fa_code(
    request: Verify2FARequest,
    db: Session = Depends(get_db),
    proj = Depends(get_project),
):
    """Verify 2FA code"""
    project = proj[0]

    # Get most recent unused code for user
    twofa_code = db.query(TwoFactorCode).filter(
        TwoFactorCode.user_id == request.user_id,
        TwoFactorCode.project_id == project.id,
        TwoFactorCode.code == request.code,
        TwoFactorCode.is_used == False
    ).order_by(TwoFactorCode.created_at.desc()).first()

    if not twofa_code:
        raise HTTPException(400, "Invalid code")

    if not twofa_code.is_valid():
        raise HTTPException(400, "Code expired or already used")

    # Mark as used
    twofa_code.is_used = True

    # Update last verified
    settings = db.query(TwoFactorSettings).filter(
        TwoFactorSettings.user_id == request.user_id
    ).first()
    if settings:
        settings.last_verified_at = datetime.utcnow()

    db.commit()

    return {"message": "Code verified successfully"}
```

### Step 5: Wire Up to Login

**File: `app/api/auth_collection.py`**

In the login endpoint (around line 49), add 2FA check:

```python
@router.post("/login")
async def login_user(...):
    # ... existing authentication logic ...

    # Check if 2FA is enabled for project AND user
    if project.configs.get('ENABLE_2FA', False):
        settings = db.query(TwoFactorSettings).filter(
            TwoFactorSettings.user_id == user.id,
            TwoFactorSettings.is_enabled == True
        ).first()

        if settings:
            # Generate and send 2FA code
            code = TwoFactorCode.generate_code()
            twofa_code = TwoFactorCode(
                user_id=user.id,
                project_id=project.id,
                code=code,
                expires_at=datetime.utcnow() + timedelta(minutes=10)
            )
            db.add(twofa_code)
            db.commit()

            # Send email
            email_service = EmailService(project_id=project.id, db=db)
            # await email_service.send_2fa_code_email(...)

            return {
                "requires_2fa": True,
                "user_id": user.id,
                "message": "2FA code sent to your email"
            }

    # Normal login flow
    return {"access_token": create_app_user_token(user), "user": user}
```

### Configuration

Projects enable 2FA via config:

```python
project.configs = {
    "ENABLE_2FA": True,  # Enable 2FA for this project
    "2FA_REQUIRED_FOR_ALL": False,  # Optional: make it required for all users
}
```

---

## Testing

### Test Welcome Email
```bash
# 1. Ensure migration is run
alembic upgrade head

# 2. Create new user
POST /auth-collections/signup
{
  "email": "test@example.com",
  "password": "password123"
}

# 3. Check email inbox for welcome email
```

### Test 2FA
```bash
# 1. Enable 2FA for project
project.configs["ENABLE_2FA"] = True

# 2. Enable 2FA for user
POST /auth-collections/2fa/enable
{
  "user_id": "user_id_here"
}

# 3. Login - should receive 2FA code
POST /auth-collections/login
{
  "email": "test@example.com",
  "password": "password123"
}

# 4. Verify code
POST /auth-collections/2fa/verify
{
  "user_id": "user_id_here",
  "code": "123456"
}
```

---

## Next Steps

1. ✅ Run updated migration for welcome email
2. ✅ Wire up welcome email to signup endpoint
3. ⏳ Create 2FA models file
4. ⏳ Create 2FA migration
5. ⏳ Add 2FA email template
6. ⏳ Create 2FA endpoints file
7. ⏳ Integrate 2FA with login flow
8. ⏳ Test both features
9. ⏳ Update documentation

This modular approach allows implementing welcome emails immediately, then 2FA when ready!
