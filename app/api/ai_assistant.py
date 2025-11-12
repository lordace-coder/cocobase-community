from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import get_project_with_access, get_current_user
from app.models.user import User
from app.services.ai_assistant.bot import generate_or_edit_code, ask_question

router = APIRouter(prefix="/ai-assistant", tags=["AI Assistant"])


# Pydantic models
class CodeGenerationRequest(BaseModel):
    prompt: str
    existing_code: Optional[str] = None


class CodeGenerationResponse(BaseModel):
    success: bool
    code: Optional[str] = None
    explanation: str
    full_response: Optional[str] = None
    is_edit: bool
    error: Optional[str] = None


class QuestionRequest(BaseModel):
    question: str


class QuestionResponse(BaseModel):
    success: bool
    answer: str
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

    Use this endpoint for:
    - Understanding how to use CocoBase APIs
    - Getting help with database queries
    - Learning best practices
    - Debugging issues
    - General questions (no code generation)

    Args:
        project_id: Project ID (for context)
        question: Your question about CocoBase

    Returns:
        Answer to your question
    """
    # Verify user has access to project
    project = get_project_with_access(project_id, user, db)

    try:
        result = ask_question(
            user_question=request.question,
            project_id=project.id
        )

        return QuestionResponse(**result)

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

    The AI assistant will:
    - Generate production-ready cloud function code from a description
    - Edit existing code based on requirements
    - Follow CocoBase best practices
    - Optimize for performance
    - Include proper error handling

    Args:
        project_id: Project ID (for potential rate limiting)
        prompt: Description of what the function should do or changes to make
        existing_code: Optional existing code to edit (if None, generates new code)

    Returns:
        Generated/edited code with explanation
    """
    # Verify user has access to project
    project = get_project_with_access(project_id, user, db)

    try:
        result = generate_or_edit_code(
            user_prompt=request.prompt,
            existing_code=request.existing_code,
            project_id=project.id
        )

        return CodeGenerationResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI assistant error: {str(e)}",
        )
