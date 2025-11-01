from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from google import genai
from google.genai import types

from app.core.database import get_db
from app.core.dependencies import get_project_with_access, get_current_user
from app.models.app_client import Project
from app.models.user import User
from app.services.ai_assistant.utils import (
    create_cloud_function,
    update_cloud_function,
    get_cloud_function,
    list_cloud_functions,
    delete_cloud_function,
)
from app.services.ai_assistant.bot import SYSTEM_PROMPT
import os

router = APIRouter(prefix="/ai-assistant", tags=["AI Assistant"])

# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")  # Move to env variable in production


# Define function declarations for Gemini
def get_function_declarations():
    """Get function declarations in the format Gemini expects"""
    return [
        {
            "name": "create_cloud_function",
            "description": "Create a new cloud function in the user's project. Use this when the user asks to create, make, or write a new function.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the cloud function (e.g., 'get_users', 'create_order')",
                    },
                    "code": {
                        "type": "string",
                        "description": "Python code for the function. Must include a main() function that returns a dict.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of what the function does",
                    },
                },
                "required": ["name", "code", "description"],
            },
        },
        {
            "name": "update_cloud_function",
            "description": "Update an existing cloud function. Use this when the user asks to modify, edit, or change a function.",
            "parameters": {
                "type": "object",
                "properties": {
                    "function_id": {
                        "type": "string",
                        "description": "ID of the function to update",
                    },
                    "code": {"type": "string", "description": "Updated Python code"},
                    "description": {
                        "type": "string",
                        "description": "Updated description",
                    },
                    "name": {"type": "string", "description": "Updated function name"},
                },
                "required": ["function_id"],
            },
        },
        {
            "name": "list_cloud_functions",
            "description": "List all cloud functions in the project. Use this when the user asks to see, show, or list their functions.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_cloud_function",
            "description": "Get details of a specific cloud function. Use this when the user asks about a specific function.",
            "parameters": {
                "type": "object",
                "properties": {
                    "function_id": {
                        "type": "string",
                        "description": "ID of the function to retrieve",
                    }
                },
                "required": ["function_id"],
            },
        },
        {
            "name": "delete_cloud_function",
            "description": "Delete a cloud function. Use this when the user asks to remove or delete a function.",
            "parameters": {
                "type": "object",
                "properties": {
                    "function_id": {
                        "type": "string",
                        "description": "ID of the function to delete",
                    }
                },
                "required": ["function_id"],
            },
        },
    ]


# Pydantic models
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []


class ChatResponse(BaseModel):
    response: str
    history: List[ChatMessage]
    cloud_function: Optional[dict] = None  # Created/updated cloud function object


# Helper function to convert chat history to Gemini format
def format_history_for_gemini(history: List[ChatMessage]) -> List[dict]:
    """Convert our chat history format to Gemini's format"""
    formatted = []
    for msg in history:
        role = "user" if msg.role == "user" else "model"
        formatted.append({"role": role, "parts": [{"text": msg.content}]})
    return formatted


@router.post("/{project_id}/chat", response_model=ChatResponse)
async def chat_with_assistant(
    project_id: str,
    request: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Chat with the AI assistant about cloud functions.
    The AI can create, update, list, and delete functions through tool calls.
    Maintains conversation history for context.
    """
    project = get_project_with_access(project_id, user, db)

    try:
        # Initialize Gemini client
        client = genai.Client(api_key=GEMINI_API_KEY)

        # Convert history to Gemini format
        chat_history = format_history_for_gemini(request.history)

        # Add current user message
        chat_history.append(
            {
                "role": "user",
                "parts": [{"text": f"Project ID: {project_id}\n{request.message}"}],
            }
        )

        # Configure with function declarations in Gemini format
        tools = types.Tool(function_declarations=get_function_declarations())
        config = types.GenerateContentConfig(
            tools=[tools],
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
        )

        # Generate response - AI may call tools automatically
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=chat_history,
            config=config,
        )
        print(response)

        assistant_response = (
            response.text
            if response.text
            else "I apologize, I couldn't generate a response. Please try again."
        )

        # Extract function calls and execute them
        cloud_function = None
        try:
            if hasattr(response, "candidates") and response.candidates:
                for candidate in response.candidates:
                    if not hasattr(candidate, "content"):
                        continue

                    content = candidate.content
                    if not hasattr(content, "parts") or not content.parts:
                        continue

                    for part in content.parts:
                        # Check if this part has a function_call attribute
                        if not hasattr(part, "function_call"):
                            continue

                        fc = part.function_call
                        if not fc or not hasattr(fc, "name"):
                            continue

                        # Extract and execute function calls
                        args = dict(fc.args) if hasattr(fc, "args") and fc.args else {}

                        try:
                            if fc.name == "create_cloud_function":
                                cloud_function = create_cloud_function(
                                    project=project.id,
                                    name=args.get("name"),
                                    code=args.get("code"),
                                    description=args.get("description", ""),
                                )
                            elif fc.name == "update_cloud_function":
                                cloud_function = update_cloud_function(
                                    function_id=args.get("function_id"),
                                    project_id=project.id,
                                    code=args.get("code"),
                                    description=args.get("description"),
                                    name=args.get("name"),
                                    is_active=args.get("is_active"),
                                )
                        except Exception as exec_error:
                            print(f"Error executing {fc.name}: {str(exec_error)}")
        except Exception as e:
            # Log the error but don't fail the request
            print(f"Warning: Failed to process function calls: {str(e)}")

        # Update history with assistant response
        updated_history = request.history + [
            ChatMessage(role="user", content=request.message),
            ChatMessage(role="assistant", content=assistant_response),
        ]

        return ChatResponse(
            response=assistant_response,
            history=updated_history,
            cloud_function=cloud_function,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI assistant error: {str(e)}",
        )
