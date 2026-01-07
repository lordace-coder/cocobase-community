from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, Enum, Index, UniqueConstraint
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.core.database import Base



class SMTPConfiguration(Base):
    """SMTP configuration for each project"""
    __tablename__ = 'smtp_configurations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # SMTP Settings
    host = Column(String(255), nullable=False)
    port = Column(Integer, default=587, nullable=False)
    username = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)  # Should be encrypted in production
    use_tls = Column(Boolean, default=True)
    use_ssl = Column(Boolean, default=False)
    
    # Sender Information
    from_email = Column(String(255), nullable=False)
    from_name = Column(String(255), default='')
    
    # Status and Metadata
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_verified_at = Column(DateTime, nullable=True)
    
    # Rate Limiting (optional)
    daily_limit = Column(Integer, nullable=True)
    hourly_limit = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<SMTPConfiguration(project_id='{self.project_id}', host='{self.host}')>"


class EmailTemplateTypeEnum(str, enum.Enum):
    """Predefined template types for common actions"""
    WELCOME = 'welcome'
    VERIFICATION = 'verification'
    FORGOT_PASSWORD = 'forgot_password'
    RESET_PASSWORD = 'reset_password'
    PASSWORD_CHANGED = 'password_changed'
    ACCOUNT_DELETED = 'account_deleted'
    LOGIN_ALERT = 'login_alert'
    CUSTOM = 'custom'


class DefaultEmailTemplate(Base):
    """System-wide default templates that can be easily edited by admins"""
    __tablename__ = 'default_email_templates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_type = Column(
        Enum(EmailTemplateTypeEnum), 
        unique=True, 
        nullable=False,
        index=True
    )
    
    name = Column(String(255), nullable=False)
    description = Column(Text, default='')
    
    # Template Content
    subject = Column(String(255), nullable=False)
    html_body = Column(Text, nullable=False)
    text_body = Column(Text, nullable=False)
    
    # Template Variables Documentation
    available_variables = Column(
        JSON,
        default=dict,
        nullable=False
    )
    
    # Metadata
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<DefaultEmailTemplate(template_type='{self.template_type.value}', name='{self.name}')>"


class ProjectEmailTemplate(Base):
    """Project-specific email templates that users can customize"""
    __tablename__ = 'project_email_templates'
    __table_args__ = (
        UniqueConstraint('project_id', 'template_type', name='uq_project_template_type'),
        Index('idx_project_template_active', 'project_id', 'template_type', 'is_active'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(255), nullable=False, index=True)
    
    template_type = Column(
        Enum(EmailTemplateTypeEnum),
        nullable=False,
        index=True
    )
    
    name = Column(String(255), nullable=False)
    description = Column(Text, default='')
    
    # Template Content
    subject = Column(String(255), nullable=False)
    html_body = Column(Text, nullable=False)
    text_body = Column(Text, nullable=False)
    
    # Template Variables
    available_variables = Column(JSON, default=dict, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_default_override = Column(Boolean, default=False)
    
    # Metadata
    created_by = Column(String(255), default='')
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<ProjectEmailTemplate(project_id='{self.project_id}', template_type='{self.template_type.value}')>"


class EmailStatusEnum(str, enum.Enum):
    """Email delivery status"""
    PENDING = 'pending'
    SENT = 'sent'
    FAILED = 'failed'
    BOUNCED = 'bounced'


class EmailLog(Base):
    """Log of sent emails for tracking and debugging"""
    __tablename__ = 'email_logs'
    __table_args__ = (
        Index('idx_email_log_project_created', 'project_id', 'created_at'),
        Index('idx_email_log_status_created', 'status', 'created_at'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(255), nullable=False, index=True)
    
    # Email Details
    recipients = Column(JSON, nullable=False)  # ["user@example.com"] or ["user1@...", "user2@..."]
    subject = Column(String(255), nullable=False)
    template_type = Column(Enum(EmailTemplateTypeEnum), nullable=False)
    
    # Template Used
    used_default_template = Column(Boolean, default=False)
    template_id = Column(String(255), nullable=True)
    
    # Status Tracking
    status = Column(Enum(EmailStatusEnum), default=EmailStatusEnum.PENDING, nullable=False)
    error_message = Column(Text, default='')
    
    # Metadata
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    def __repr__(self):
        recipient_count = len(self.recipients) if isinstance(self.recipients, list) else 0
        return f"<EmailLog(id={self.id}, recipients={recipient_count}, status='{self.status.value}')>"