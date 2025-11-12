"""
Generate training data for fine-tuning the AI assistant.
This creates example pairs of (user request, expected code) for model training.
"""

def generate_training_examples():
    """
    Generate training examples in OpenAI fine-tuning format.
    Format: {"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
    """

    examples = [
        {
            "messages": [
                {
                    "role": "system",
                    "content": "You are CocoBase Bot. Generate cloud function code WITHOUT imports. Libraries pre-imported: json, datetime, math, re, uuid, hashlib, db, request."
                },
                {
                    "role": "user",
                    "content": "Create a function to list all users with pagination"
                },
                {
                    "role": "assistant",
                    "content": """```python
def main():
    try:
        # Get pagination parameters
        limit = request.get('limit', 100)
        offset = request.get('offset', 0)

        # Query users with pagination
        result = db.query(
            'users',
            limit=limit,
            offset=offset,
            sort='created_at',
            order='desc'
        )

        return {
            'success': True,
            'users': result['data'],
            'total': result['total'],
            'limit': limit,
            'offset': offset
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
```

This function lists users with pagination. It accepts `limit` and `offset` parameters from the request, queries the users collection, and returns the results with pagination info."""
                }
            ]
        },
        {
            "messages": [
                {
                    "role": "system",
                    "content": "You are CocoBase Bot. Generate cloud function code WITHOUT imports. Libraries pre-imported: json, datetime, math, re, uuid, hashlib, db, request."
                },
                {
                    "role": "user",
                    "content": "Create a function to create a new user with validation"
                },
                {
                    "role": "assistant",
                    "content": """```python
def main():
    try:
        # Get user data from request
        data = request.json()

        # Validate required fields
        if not data.get('email'):
            return {'success': False, 'error': 'Email is required'}

        if not data.get('name'):
            return {'success': False, 'error': 'Name is required'}

        # Validate email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, data['email']):
            return {'success': False, 'error': 'Invalid email format'}

        # Check if email already exists
        existing = db.query('users', email=data['email'])
        if existing['total'] > 0:
            return {'success': False, 'error': 'Email already exists'}

        # Create user with timestamp
        user_data = {
            'name': data['name'],
            'email': data['email'],
            'created_at': datetime.datetime.utcnow().isoformat()
        }

        # Create document
        user = db.create_document('users', user_data)

        return {
            'success': True,
            'user': user
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
```

This function creates a new user with validation. It checks for required fields, validates email format, ensures uniqueness, and creates the user with a timestamp."""
                }
            ]
        },
        {
            "messages": [
                {
                    "role": "system",
                    "content": "You are CocoBase Bot. Generate cloud function code WITHOUT imports. Libraries pre-imported: json, datetime, math, re, uuid, hashlib, db, request."
                },
                {
                    "role": "user",
                    "content": "Create a function to get posts with their authors populated"
                },
                {
                    "role": "assistant",
                    "content": """```python
def main():
    try:
        # Get pagination parameters
        limit = request.get('limit', 20)
        offset = request.get('offset', 0)

        # Query posts with author population
        result = db.query(
            'posts',
            populate=['author'],
            limit=limit,
            offset=offset,
            sort='created_at',
            order='desc'
        )

        return {
            'success': True,
            'posts': result['data'],
            'total': result['total']
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
```

This function fetches posts with their author data populated. It uses the `populate` parameter to automatically load author information for each post."""
                }
            ]
        },
        {
            "messages": [
                {
                    "role": "system",
                    "content": "You are CocoBase Bot. Generate cloud function code WITHOUT imports. Libraries pre-imported: json, datetime, math, re, uuid, hashlib, db, request."
                },
                {
                    "role": "user",
                    "content": "Update a user's profile"
                },
                {
                    "role": "assistant",
                    "content": """```python
def main():
    try:
        # Get user ID and update data
        user_id = request.get('user_id')
        data = request.json()

        if not user_id:
            return {'success': False, 'error': 'user_id is required'}

        # Prepare update data
        update_data = {}

        # Only update allowed fields
        allowed_fields = ['name', 'bio', 'avatar']
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]

        if not update_data:
            return {'success': False, 'error': 'No valid fields to update'}

        # Add updated timestamp
        update_data['updated_at'] = datetime.datetime.utcnow().isoformat()

        # Update user
        updated_user = db.update_document('users', user_id, update_data)

        return {
            'success': True,
            'user': updated_user
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
```

This function updates a user's profile. It validates the user ID, filters allowed fields, and updates the user document with a timestamp."""
                }
            ]
        },
        {
            "messages": [
                {
                    "role": "system",
                    "content": "You are CocoBase Bot. Generate cloud function code WITHOUT imports. Libraries pre-imported: json, datetime, math, re, uuid, hashlib, db, request."
                },
                {
                    "role": "user",
                    "content": "Delete a document by ID"
                },
                {
                    "role": "assistant",
                    "content": """```python
def main():
    try:
        # Get document ID and collection
        doc_id = request.get('id')
        collection = request.get('collection')

        if not doc_id:
            return {'success': False, 'error': 'Document ID is required'}

        if not collection:
            return {'success': False, 'error': 'Collection name is required'}

        # Delete document
        db.delete_document(collection, doc_id)

        return {
            'success': True,
            'message': f'Document {doc_id} deleted successfully'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
```

This function deletes a document from a specified collection. It validates the required parameters and returns a success message."""
                }
            ]
        },
        {
            "messages": [
                {
                    "role": "system",
                    "content": "You are CocoBase Bot. Generate cloud function code WITHOUT imports. Libraries pre-imported: json, datetime, math, re, uuid, hashlib, db, request."
                },
                {
                    "role": "user",
                    "content": "Search posts by title using regex"
                },
                {
                    "role": "assistant",
                    "content": """```python
def main():
    try:
        # Get search query
        query = request.get('query', '')

        if not query:
            return {'success': False, 'error': 'Search query is required'}

        # Search posts with title containing query (case-insensitive)
        result = db.query(
            'posts',
            title={'$regex': query, '$options': 'i'},
            limit=50,
            sort='created_at',
            order='desc'
        )

        return {
            'success': True,
            'posts': result['data'],
            'total': result['total'],
            'query': query
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
```

This function searches posts by title using regex pattern matching. The search is case-insensitive and returns up to 50 results."""
                }
            ]
        },
        {
            "messages": [
                {
                    "role": "system",
                    "content": "You are CocoBase Bot. Generate cloud function code WITHOUT imports. Libraries pre-imported: json, datetime, math, re, uuid, hashlib, db, request."
                },
                {
                    "role": "user",
                    "content": "Get user statistics including post count"
                },
                {
                    "role": "assistant",
                    "content": """```python
def main():
    try:
        # Get user ID
        user_id = request.get('user_id')

        if not user_id:
            return {'success': False, 'error': 'user_id is required'}

        # Get user data
        user_result = db.query('users', id=user_id)

        if user_result['total'] == 0:
            return {'success': False, 'error': 'User not found'}

        user = user_result['data'][0]

        # Get user's post count
        posts_result = db.query('posts', author_id=user_id)

        # Calculate statistics
        stats = {
            'user': user,
            'post_count': posts_result['total'],
            'member_since': user.get('created_at'),
            'last_updated': datetime.datetime.utcnow().isoformat()
        }

        return {
            'success': True,
            'statistics': stats
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
```

This function retrieves user statistics including their post count. It fetches the user data and counts their posts."""
                }
            ]
        },
        {
            "messages": [
                {
                    "role": "system",
                    "content": "You are CocoBase Bot. Generate cloud function code WITHOUT imports. Libraries pre-imported: json, datetime, math, re, uuid, hashlib, db, request."
                },
                {
                    "role": "user",
                    "content": "Create a post with automatic slug generation"
                },
                {
                    "role": "assistant",
                    "content": """```python
def main():
    try:
        # Get post data
        data = request.json()

        # Validate required fields
        if not data.get('title'):
            return {'success': False, 'error': 'Title is required'}

        if not data.get('content'):
            return {'success': False, 'error': 'Content is required'}

        if not data.get('author_id'):
            return {'success': False, 'error': 'Author ID is required'}

        # Generate slug from title
        slug = re.sub(r'[^a-z0-9]+', '-', data['title'].lower()).strip('-')

        # Check if slug exists
        existing = db.query('posts', slug=slug)
        if existing['total'] > 0:
            # Add random suffix to make unique
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        # Create post
        post_data = {
            'title': data['title'],
            'content': data['content'],
            'slug': slug,
            'author_id': data['author_id'],
            'status': data.get('status', 'draft'),
            'created_at': datetime.datetime.utcnow().isoformat()
        }

        post = db.create_document('posts', post_data)

        return {
            'success': True,
            'post': post
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
```

This function creates a post with automatic slug generation. It validates input, generates a URL-friendly slug from the title, ensures uniqueness, and creates the post."""
                }
            ]
        }
    ]

    return examples


def save_training_data():
    """Save training examples to JSONL file for OpenAI fine-tuning"""
    import json

    examples = generate_training_examples()

    with open('training_data.jsonl', 'w') as f:
        for example in examples:
            f.write(json.dumps(example) + '\n')

    print(f"✅ Generated {len(examples)} training examples")
    print("📁 Saved to: training_data.jsonl")
    print("\nTo fine-tune:")
    print("1. openai api fine_tunes.create -t training_data.jsonl -m gpt-4o-mini")
    print("2. Wait for training to complete")
    print("3. Use the fine-tuned model in your .env: AI_MODEL=ft:gpt-4o-mini:...")


if __name__ == "__main__":
    save_training_data()
