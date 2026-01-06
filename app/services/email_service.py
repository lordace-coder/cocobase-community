from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr

class EmailService:
    def __init__(self,project_id:str):
        self.conf = ConnectionConfig(
            MAIL_USERNAME="your-email@example.com",
            MAIL_PASSWORD="your-password",
            MAIL_FROM="noreply@example.com",
            MAIL_PORT=587,
            MAIL_SERVER="smtp.gmail.com",
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True
        )
        self.fm = FastMail(self.conf)
    
    async def send_reset_email(self, email: EmailStr, token: str):
        reset_url = f"https://app.cocobase.com/reset-password?token={token}"
        
        html = f"""
        <html>
            <body>
                <h2>Password Reset Request</h2>
                <p>Click the link below to reset your password:</p>
                <a href="{reset_url}">Reset Password</a>
                <p>This link expires in 1 hour.</p>
                <p>If you didn't request this, ignore this email.</p>
            </body>
        </html>
        """
        
        message = MessageSchema(
            subject="Reset Your Password",
            recipients=[email],
            body=html,
            subtype="html"
        )
        
        await self.fm.send_message(message)
