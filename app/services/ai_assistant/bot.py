# COCOBASE CLOUD FUNCTIONS BOT - AI Assistant for Writing CocoBase Cloud Functions
import os
from typing import Optional
from openai import OpenAI
import hashlib


# Load documentation files
def load_documentation():
    """Load essential documentation files from the cloud_function_docs folder"""
    docs = []
    doc_folder = "cloud_function_docs"

    # Only load essential docs to reduce token usage
    # Priority: most important for code generation
    essential_docs = [
        "quick-reference.md",      # Concise API reference
        "database-api.md",         # Database operations
        "README.md",               # Overview
    ]

    if os.path.exists(doc_folder):
        for filename in essential_docs:
            filepath = os.path.join(doc_folder, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                        # Limit each doc to first 3000 chars (most important info)
                        if len(content) > 3000:
                            content = content[:3000] + "\n\n[... truncated for brevity ...]"
                        docs.append(f"## {filename}\n\n{content}")
                except Exception as e:
                    print(f"Warning: Could not load {filename}: {e}")

    return "\n\n---\n\n".join(docs)


# Load the documentation
documentation = load_documentation()

# Cache documentation hash to track changes
doc_hash = hashlib.md5(documentation.encode()).hexdigest()[:8]

# System prompt that defines the bot's role and provides context
SYSTEM_PROMPT = f"""You are CocoBase Bot, expert at writing CocoBase Cloud Functions.

DOCUMENTATION:
{documentation}

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


def ask_question(
    user_question: str,
    project_id: Optional[str] = None
) -> dict:
    """
    Answer questions about CocoBase cloud functions without generating code.

    Args:
        user_question: User's question about CocoBase, APIs, best practices, etc.
        project_id: Optional project ID

    Returns:
        dict: {
            "success": bool,
            "answer": "the answer to the question",
            "error": optional error message
        }
    """
    # Use OpenAI API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "success": False,
            "answer": "",
            "error": "OPENAI_API_KEY not set in environment variables",
            "project_id": project_id
        }

    # TODO: Replace with your fine-tuned model ID after training completes
    # Example: ft:gpt-4o-mini-2024-07-18:your-org:cocobase:abc123
    model = os.getenv("AI_MODEL", "gpt-4o-mini")

    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Answer this question (no code generation): {user_question}"}
            ],
            temperature=0.7,
            max_tokens=2048
        )

        answer = response.choices[0].message.content

        return {
            "success": True,
            "answer": answer,
            "project_id": project_id
        }

    except Exception as e:
        return {
            "success": False,
            "answer": "",
            "error": str(e),
            "project_id": project_id
        }


def generate_or_edit_code(
    user_prompt: str,
    existing_code: Optional[str] = None,
    project_id: Optional[str] = None
) -> dict:
    """
    Generate new cloud function code or edit existing code based on user requirements.

    Args:
        user_prompt: User's description of what the function should do or what changes to make
        existing_code: Optional existing code to edit (if None, generates new code)
        project_id: Optional project ID for potential rate limiting/quota enforcement

    Returns:
        dict: {
            "code": "the generated/edited code",
            "explanation": "explanation of what was done",
            "suggestions": "optional suggestions for improvements"
        }
    """
    # Use OpenAI API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "success": False,
            "error": "OPENAI_API_KEY not set in environment variables",
            "code": None,
            "explanation": "Missing OpenAI API key",
            "full_response": None,
            "project_id": project_id,
            "is_edit": existing_code is not None
        }

    # TODO: Replace with your fine-tuned model ID after training completes
    # Example: ft:gpt-4o-mini-2024-07-18:your-org:cocobase:abc123
    model = os.getenv("AI_MODEL", "gpt-4o-mini")

    client = OpenAI(api_key=api_key)

    # Build the prompt based on whether we're editing or generating
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

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=4096
        )

        response_text = response.choices[0].message.content

        # Parse the response to extract code and explanation
        code = ""
        explanation = response_text

        # Extract code from markdown code blocks
        if "```python" in response_text:
            parts = response_text.split("```python")
            if len(parts) > 1:
                code_part = parts[1].split("```")[0].strip()
                code = code_part
                # Remove code from explanation
                explanation = response_text.replace(f"```python\n{code_part}\n```", "[CODE GENERATED]").strip()
        elif "```" in response_text:
            parts = response_text.split("```")
            if len(parts) >= 3:
                code = parts[1].strip()
                explanation = (parts[0] + parts[2]).strip()

        return {
            "success": True,
            "code": code if code else None,
            "explanation": explanation,
            "full_response": response_text,
            "project_id": project_id,
            "is_edit": existing_code is not None
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "code": None,
            "explanation": f"Failed to generate code: {str(e)}",
            "full_response": None,
            "project_id": project_id,
            "is_edit": existing_code is not None
        }
