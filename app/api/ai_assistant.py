from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.core.dependencies import get_project_with_access, get_current_user
from app.models.user import User
from app.services.ai_assistant import bot_with_history

router = APIRouter(prefix="/ai-assistant", tags=["AI Assistant"])


# Pydantic models
class CodeGenerationRequest(BaseModel):
    prompt: str
    existing_code: Optional[str] = None
    session_id: Optional[str] = None  # For conversation history
    function_name: Optional[str] = None


class RateLimitInfo(BaseModel):
    allowed: bool
    remaining: int
    limit: int
    plan_type: str
    reset_time: str
    current_usage: int


class CodeGenerationResponse(BaseModel):
    success: bool
    code: Optional[str] = None
    explanation: str
    full_response: Optional[str] = None
    is_edit: bool
    session_id: str  # Return session ID for follow-up
    rate_limit: RateLimitInfo
    error: Optional[str] = None


class QuestionRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


class QuestionResponse(BaseModel):
    success: bool
    answer: str
    session_id: str
    rate_limit: RateLimitInfo
    error: Optional[str] = None


@router.post("/{project_id}/ask", response_model=QuestionResponse)
async def ask_ai_question(
    project_id: str,
    request: QuestionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Ask the AI assistant questions about CocoBase cloud functions.

    **Rate Limits:**
    - Free plan: 10 chats/hour
    - Paid plan: 30 chats/hour
    - Premium plan: 100 chats/hour

    **Features:**
    - Conversation history (pass session_id for context)
    - Rate limiting per project
    - Context-aware responses

    Use this endpoint for:
    - Understanding how to use CocoBase APIs
    - Getting help with database queries
    - Learning best practices
    - Debugging issues
    - General questions (no code generation)

    Args:
        project_id: Project ID
        question: Your question about CocoBase
        session_id: Optional session ID for conversation history

    Returns:
        Answer to your question with rate limit info
    """
    # Verify user has access to project
    project = get_project_with_access(project_id, user, db)

    try:
        result = bot_with_history.ask_question(
            user_question=request.question,
            project_id=project.id,
            db=db,
            session_id=request.session_id,
            user_id=str(user.id)
        )

        if not result.get('success'):
            if 'rate limit' in result.get('error', '').lower():
                raise HTTPException(
                    status_code=429,
                    detail=result.get('error')
                )
            raise HTTPException(
                status_code=400,
                detail=result.get('error')
            )

        return QuestionResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI assistant error: {str(e)}",
        )


@router.post("/{project_id}/generate", response_model=CodeGenerationResponse)
async def generate_code(
    project_id: str,
    request: CodeGenerationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Generate new cloud function code or edit existing code.

    **Rate Limits:**
    - Free plan: 10 chats/hour
    - Paid plan: 30 chats/hour
    - Premium plan: 100 chats/hour

    **Features:**
    - Conversation history (maintains context across edits)
    - Rate limiting per project
    - Auto code parsing

    The AI assistant will:
    - Generate production-ready cloud function code from a description
    - Edit existing code based on requirements
    - Follow CocoBase best practices
    - Optimize for performance
    - Include proper error handling

    Args:
        project_id: Project ID
        prompt: Description of what the function should do or changes to make
        existing_code: Optional existing code to edit (if None, generates new code)
        session_id: Optional session ID for conversation history
        function_name: Optional function name being edited

    Returns:
        Generated/edited code with explanation and rate limit info
    """
    # Verify user has access to project
    project = get_project_with_access(project_id, user, db)

    try:
        result = bot_with_history.generate_or_edit_code(
            user_prompt=request.prompt,
            project_id=project.id,
            db=db,
            existing_code=request.existing_code,
            session_id=request.session_id,
            user_id=str(user.id),
            function_name=request.function_name
        )

        if not result.get('success'):
            if 'rate limit' in result.get('error', '').lower():
                raise HTTPException(
                    status_code=429,
                    detail=result.get('error')
                )
            raise HTTPException(
                status_code=400,
                detail=result.get('error')
            )

        return CodeGenerationResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI assistant error: {str(e)}",
        )


@router.get("/{project_id}/rate-limit")
async def get_rate_limit(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Check current AI assistant rate limit status.

    Returns:
    - How many chats remaining this hour
    - Total limit based on plan
    - When the limit resets
    - Current plan type
    """
    project = get_project_with_access(project_id, user, db)

    rate_info = bot_with_history.check_rate_limit(project.id, db)

    if 'error' in rate_info:
        raise HTTPException(status_code=404, detail=rate_info['error'])

    return rate_info


@router.get("/{project_id}/conversation/{session_id}")
async def get_conversation(
    project_id: str,
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Retrieve conversation history for a session.

    Useful for:
    - Displaying chat history in UI
    - Debugging conversation flow
    - Exporting conversation data
    """
    project = get_project_with_access(project_id, user, db)

    from app.models.ai_assistant import AIConversation
    from sqlalchemy import and_

    messages = db.query(AIConversation).filter(
        and_(
            AIConversation.project_id == project.id,
            AIConversation.session_id == session_id
        )
    ).order_by(AIConversation.created_at.asc()).all()

    formatted_messages = []
    for msg in messages:
        formatted_messages.append({
            "role": msg.message_type,
            "content": msg.content,
            "timestamp": msg.created_at.isoformat(),
            "function_name": msg.function_name,
            "code_generated": msg.code_generated
        })

    return {
        "session_id": session_id,
        "messages": formatted_messages,
        "total_messages": len(formatted_messages)
    }


@router.get("/{project_id}/usage-stats")
async def get_usage_stats(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    hours: int = 24
):
    """
    Get AI assistant usage statistics.

    Returns hourly usage for the past N hours.
    """
    project = get_project_with_access(project_id, user, db)

    from app.models.ai_assistant import AIUsageCounter
    from datetime import timedelta

    current_hour = AIUsageCounter.get_current_hour_bucket()
    start_time = current_hour - timedelta(hours=hours)

    usage_records = db.query(AIUsageCounter).filter(
        AIUsageCounter.project_id == project.id,
        AIUsageCounter.hour_bucket >= start_time
    ).order_by(AIUsageCounter.hour_bucket.asc()).all()

    hourly_data = []
    total_chats = 0
    total_code_gen = 0
    total_questions = 0

    for record in usage_records:
        hourly_data.append({
            "hour": record.hour_bucket.isoformat(),
            "chats": record.chat_count,
            "code_generations": record.code_generation_count,
            "questions": record.question_count
        })
        total_chats += record.chat_count
        total_code_gen += record.code_generation_count
        total_questions += record.question_count

    return {
        "hourly_usage": hourly_data,
        "totals": {
            "chats": total_chats,
            "code_generations": total_code_gen,
            "questions": total_questions
        },
        "period_hours": hours
    }
