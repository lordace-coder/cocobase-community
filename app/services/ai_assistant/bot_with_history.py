"""
COCOBASE CLOUD FUNCTIONS BOT - AI Assistant with Conversation History & Rate Limiting
"""
import os
import uuid
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import and_

# System prompt
SYSTEM_PROMPT = """You are CocoBase Bot, expert at writing CocoBase Cloud Functions.

CRITICAL RULES:
1. NEVER write import statements - all libraries are pre-imported
2. All functions MUST have main() that returns dict
3. Use 'db' object for database operations (auto-scoped to project)
4. Get request data: request.json() or request.get()
5. 20s timeout - optimize performance
6. NO external network calls allowed
7. Always use try/except for errors
8. Return JSON-serializable data only

PRE-IMPORTED LIBRARIES (no imports needed):
- json (JSON operations)
- datetime (date/time handling)
- math (mathematical operations)
- re (regex patterns)
- uuid (UUID generation)
- hashlib (hashing: md5, sha256, etc)
- db (database: query, create_document, update_document, delete_document)
- request (HTTP request data)

GENERATE:
- Production-ready code WITHOUT imports
- Error handling (try/except)
- Pagination (limit=100, offset=0) for lists
- Sensible defaults

EDIT:
- Preserve logic unless asked
- Remove any import statements
- Optimize performance

OUTPUT:
- Code in python block (NO IMPORTS)
- Brief explanation
- Usage notes"""


# Rate limiting configuration
RATE_LIMITS = {
    'free': {
        'chats_per_hour': 10,
        'max_history': 5,  # Keep only last 5 messages for context
    },
    'paid': {
        'chats_per_hour': 30,
        'max_history': 10,  # Keep last 10 messages
    },
    'premium': {
        'chats_per_hour': 100,
        'max_history': 20,
    }
}


def check_rate_limit(project_id: str, db: Session) -> dict:
    """
    Check if project has exceeded rate limit for current hour.

    Returns:
        dict: {
            "allowed": bool,
            "remaining": int,
            "limit": int,
            "plan_type": str,
            "reset_time": datetime
        }
    """
    from app.models.ai_assistant import AIUsageCounter
    from app.models.pricing import get_current_plan

    # Get current hour bucket
    current_hour = AIUsageCounter.get_current_hour_bucket()

    # Get project's current plan
    from app.models.app_client import Project
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        return {
            "allowed": False,
            "remaining": 0,
            "limit": 0,
            "plan_type": "unknown",
            "error": "Project not found"
        }

    plan = get_current_plan(project, db)

    # Determine plan type
    if plan.is_free:
        plan_type = 'free'
    elif plan.price < 20:  # Adjust threshold as needed
        plan_type = 'paid'
    else:
        plan_type = 'premium'

    limits = RATE_LIMITS.get(plan_type, RATE_LIMITS['free'])
    max_chats = limits['chats_per_hour']

    # Get or create usage counter for this hour
    usage = db.query(AIUsageCounter).filter(
        and_(
            AIUsageCounter.project_id == project_id,
            AIUsageCounter.hour_bucket == current_hour
        )
    ).first()

    current_usage = usage.chat_count if usage else 0

    # Calculate reset time (next hour)
    reset_time = current_hour + timedelta(hours=1)

    return {
        "allowed": current_usage < max_chats,
        "remaining": max(0, max_chats - current_usage),
        "limit": max_chats,
        "plan_type": plan_type,
        "reset_time": reset_time.isoformat(),
        "current_usage": current_usage
    }


def increment_usage(project_id: str, db: Session, chat_type: str = 'chat'):
    """
    Increment usage counter for project.

    Args:
        project_id: Project ID
        db: Database session
        chat_type: Type of chat ('chat', 'code_generation', 'question')
    """
    from app.models.ai_assistant import AIUsageCounter

    current_hour = AIUsageCounter.get_current_hour_bucket()

    usage = db.query(AIUsageCounter).filter(
        and_(
            AIUsageCounter.project_id == project_id,
            AIUsageCounter.hour_bucket == current_hour
        )
    ).first()

    if not usage:
        usage = AIUsageCounter(
            project_id=project_id,
            hour_bucket=current_hour,
            chat_count=0,
            code_generation_count=0,
            question_count=0
        )
        db.add(usage)

    # Increment appropriate counter
    usage.chat_count += 1
    if chat_type == 'code_generation':
        usage.code_generation_count += 1
    elif chat_type == 'question':
        usage.question_count += 1

    usage.last_request_at = datetime.now(timezone.utc)
    db.commit()


def get_conversation_history(
    project_id: str,
    session_id: str,
    db: Session,
    max_messages: int = 10
) -> List[Dict[str, str]]:
    """
    Retrieve conversation history for context.

    Args:
        project_id: Project ID
        session_id: Conversation session ID
        db: Database session
        max_messages: Maximum number of messages to retrieve

    Returns:
        List of message dictionaries in OpenAI format
    """
    from app.models.ai_assistant import AIConversation

    # Get recent messages for this session
    messages = db.query(AIConversation).filter(
        and_(
            AIConversation.project_id == project_id,
            AIConversation.session_id == session_id
        )
    ).order_by(AIConversation.created_at.desc()).limit(max_messages).all()

    # Reverse to get chronological order
    messages = list(reversed(messages))

    # Convert to OpenAI format
    history = []
    for msg in messages:
        history.append({
            "role": msg.message_type,
            "content": msg.content
        })

    return history


def save_message(
    project_id: str,
    session_id: str,
    message_type: str,
    content: str,
    db: Session,
    user_id: Optional[str] = None,
    function_name: Optional[str] = None,
    code_generated: Optional[str] = None
):
    """
    Save a message to conversation history.

    Args:
        project_id: Project ID
        session_id: Session ID
        message_type: 'system', 'user', or 'assistant'
        content: Message content
        db: Database session
        user_id: Optional user ID
        function_name: Optional function name
        code_generated: Optional code that was generated
    """
    from app.models.ai_assistant import AIConversation

    message = AIConversation(
        project_id=project_id,
        session_id=session_id,
        message_type=message_type,
        content=content,
        user_id=user_id,
        function_name=function_name,
        code_generated=code_generated
    )

    db.add(message)
    db.commit()


def generate_or_edit_code(
    user_prompt: str,
    project_id: str,
    db: Session,
    existing_code: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    function_name: Optional[str] = None
) -> dict:
    """
    Generate or edit cloud function code with conversation history and rate limiting.

    Args:
        user_prompt: User's description
        project_id: Project ID for rate limiting
        db: Database session
        existing_code: Optional existing code to edit
        session_id: Optional session ID for conversation context
        user_id: Optional user ID
        function_name: Optional function name being edited

    Returns:
        dict with code, explanation, and metadata
    """
    # Generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())

    # Check rate limit
    rate_check = check_rate_limit(project_id, db)
    if not rate_check['allowed']:
        return {
            "success": False,
            "error": f"Rate limit exceeded. You have used {rate_check['current_usage']}/{rate_check['limit']} chats this hour. Resets at {rate_check['reset_time']}",
            "rate_limit": rate_check,
            "session_id": session_id
        }

    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "success": False,
            "error": "OPENAI_API_KEY not set",
            "session_id": session_id
        }

    model = os.getenv("AI_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=api_key)

    # Get plan type to determine history limit
    plan_type = rate_check.get('plan_type', 'free')
    max_history = RATE_LIMITS[plan_type]['max_history']

    # Get conversation history
    history = get_conversation_history(project_id, session_id, db, max_history)

    # Build user message
    if existing_code:
        user_message = f"""Edit the following cloud function code based on this request: {user_prompt}

EXISTING CODE:
```python
{existing_code}
```

Please provide:
1. The complete updated code in a python code block
2. An explanation of changes made
3. Any important notes or suggestions"""
    else:
        user_message = f"""Generate a new cloud function based on this request: {user_prompt}

Please provide:
1. Complete, production-ready code in a python code block
2. An explanation of what the function does
3. Any important usage notes or suggestions"""

    # Save user message to history
    save_message(project_id, session_id, 'user', user_message, db, user_id, function_name)

    # Build messages for OpenAI
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add conversation history (if any)
    messages.extend(history)

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=4096
        )

        response_text = response.choices[0].message.content

        # Parse code from response
        code = ""
        explanation = response_text

        if "```python" in response_text:
            parts = response_text.split("```python")
            if len(parts) > 1:
                code_part = parts[1].split("```")[0].strip()
                code = code_part
                explanation = response_text.replace(f"```python\n{code_part}\n```", "[CODE GENERATED]").strip()
        elif "```" in response_text:
            parts = response_text.split("```")
            if len(parts) >= 3:
                code = parts[1].strip()
                explanation = (parts[0] + parts[2]).strip()

        # Save assistant response to history
        save_message(
            project_id,
            session_id,
            'assistant',
            response_text,
            db,
            user_id,
            function_name,
            code
        )

        # Increment usage
        increment_usage(project_id, db, 'code_generation')

        # Get updated rate limit info
        updated_rate = check_rate_limit(project_id, db)

        return {
            "success": True,
            "code": code if code else None,
            "explanation": explanation,
            "full_response": response_text,
            "session_id": session_id,
            "is_edit": existing_code is not None,
            "rate_limit": updated_rate
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "session_id": session_id
        }


def ask_question(
    user_question: str,
    project_id: str,
    db: Session,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> dict:
    """
    Answer questions about CocoBase with conversation history and rate limiting.

    Args:
        user_question: User's question
        project_id: Project ID
        db: Database session
        session_id: Optional session ID
        user_id: Optional user ID

    Returns:
        dict with answer and metadata
    """
    if not session_id:
        session_id = str(uuid.uuid4())

    # Check rate limit
    rate_check = check_rate_limit(project_id, db)
    if not rate_check['allowed']:
        return {
            "success": False,
            "error": f"Rate limit exceeded. Resets at {rate_check['reset_time']}",
            "rate_limit": rate_check,
            "session_id": session_id
        }

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "success": False,
            "error": "OPENAI_API_KEY not set",
            "session_id": session_id
        }

    model = os.getenv("AI_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=api_key)

    plan_type = rate_check.get('plan_type', 'free')
    max_history = RATE_LIMITS[plan_type]['max_history']

    history = get_conversation_history(project_id, session_id, db, max_history)

    user_message = f"Answer this question (no code generation): {user_question}"
    save_message(project_id, session_id, 'user', user_message, db, user_id)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=2048
        )

        answer = response.choices[0].message.content

        save_message(project_id, session_id, 'assistant', answer, db, user_id)
        increment_usage(project_id, db, 'question')

        updated_rate = check_rate_limit(project_id, db)

        return {
            "success": True,
            "answer": answer,
            "session_id": session_id,
            "rate_limit": updated_rate
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "session_id": session_id
        }
