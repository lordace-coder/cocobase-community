"""
Enhanced training examples showing advanced patterns and better diversity.
Add these to your training_data_generator.py
"""

ADVANCED_EXAMPLES = [
    # Complex multi-field query with date ranges
    {
        "messages": [
            {
                "role": "system",
                "content": "You are CocoBase Bot. Generate cloud function code WITHOUT imports. Libraries pre-imported: json, datetime, math, re, uuid, hashlib, db, request."
            },
            {
                "role": "user",
                "content": "Get all published posts from the last 30 days with author info and comment count"
            },
            {
                "role": "assistant",
                "content": """```python
def main():
    try:
        # Calculate date 30 days ago
        thirty_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
        date_threshold = thirty_days_ago.isoformat()

        # Get pagination params
        limit = request.get('limit', 20)
        offset = request.get('offset', 0)

        # Query published posts from last 30 days with author populated
        posts_result = db.query(
            'posts',
            status='published',
            created_at={'$gte': date_threshold},
            populate=['author'],
            limit=limit,
            offset=offset,
            sort='created_at',
            order='desc'
        )

        # Enrich each post with comment count
        enriched_posts = []
        for post in posts_result['data']:
            # Count comments for this post
            comments_result = db.query('comments', post_id=post['id'])
            post['comment_count'] = comments_result['total']
            enriched_posts.append(post)

        return {
            'success': True,
            'posts': enriched_posts,
            'total': posts_result['total'],
            'limit': limit,
            'offset': offset,
            'date_range': {
                'from': date_threshold,
                'to': datetime.datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
```

This function retrieves published posts from the last 30 days with their authors and comment counts. It uses date filtering, population, and enriches results with aggregated data."""
            }
        ]
    },

    # Batch operations
    {
        "messages": [
            {
                "role": "system",
                "content": "You are CocoBase Bot. Generate cloud function code WITHOUT imports. Libraries pre-imported: json, datetime, math, re, uuid, hashlib, db, request."
            },
            {
                "role": "user",
                "content": "Bulk update post statuses from draft to published"
            },
            {
                "role": "assistant",
                "content": """```python
def main():
    try:
        # Get list of post IDs to publish
        data = request.json()
        post_ids = data.get('post_ids', [])

        if not post_ids:
            return {'success': False, 'error': 'post_ids array is required'}

        if not isinstance(post_ids, list):
            return {'success': False, 'error': 'post_ids must be an array'}

        # Update each post
        updated_posts = []
        failed_posts = []

        for post_id in post_ids:
            try:
                # Update status and add published timestamp
                updated = db.update_document('posts', post_id, {
                    'status': 'published',
                    'published_at': datetime.datetime.utcnow().isoformat(),
                    'updated_at': datetime.datetime.utcnow().isoformat()
                })
                updated_posts.append(updated)
            except Exception as e:
                failed_posts.append({
                    'post_id': post_id,
                    'error': str(e)
                })

        return {
            'success': True,
            'updated_count': len(updated_posts),
            'failed_count': len(failed_posts),
            'updated_posts': updated_posts,
            'failed_posts': failed_posts
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
```

This function performs a bulk update to publish multiple posts at once. It validates input, updates each post individually, tracks successes and failures, and returns detailed results."""
            }
        ]
    },

    # Data validation and transformation
    {
        "messages": [
            {
                "role": "system",
                "content": "You are CocoBase Bot. Generate cloud function code WITHOUT imports. Libraries pre-imported: json, datetime, math, re, uuid, hashlib, db, request."
            },
            {
                "role": "user",
                "content": "Create product with price validation and automatic SKU generation"
            },
            {
                "role": "assistant",
                "content": """```python
def main():
    try:
        data = request.json()

        # Validate required fields
        required_fields = ['name', 'price', 'category']
        for field in required_fields:
            if not data.get(field):
                return {'success': False, 'error': f'{field} is required'}

        # Validate price
        try:
            price = float(data['price'])
            if price <= 0:
                return {'success': False, 'error': 'Price must be greater than 0'}
        except ValueError:
            return {'success': False, 'error': 'Invalid price format'}

        # Generate SKU from name and category
        name_slug = re.sub(r'[^a-z0-9]+', '', data['name'].lower())[:8]
        category_slug = re.sub(r'[^a-z0-9]+', '', data['category'].lower())[:4]
        random_suffix = uuid.uuid4().hex[:4].upper()
        sku = f"{category_slug}-{name_slug}-{random_suffix}"

        # Ensure SKU is unique
        existing = db.query('products', sku=sku)
        while existing['total'] > 0:
            random_suffix = uuid.uuid4().hex[:4].upper()
            sku = f"{category_slug}-{name_slug}-{random_suffix}"
            existing = db.query('products', sku=sku)

        # Create product
        product_data = {
            'name': data['name'],
            'sku': sku,
            'price': price,
            'category': data['category'],
            'description': data.get('description', ''),
            'stock': data.get('stock', 0),
            'status': 'active',
            'created_at': datetime.datetime.utcnow().isoformat()
        }

        product = db.create_document('products', product_data)

        return {
            'success': True,
            'product': product,
            'generated_sku': sku
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
```

This function creates a product with comprehensive validation and automatic SKU generation. It validates required fields and price, generates a unique SKU from the product name and category, and ensures SKU uniqueness."""
            }
        ]
    },

    # Code editing example
    {
        "messages": [
            {
                "role": "system",
                "content": "You are CocoBase Bot. Generate cloud function code WITHOUT imports. Libraries pre-imported: json, datetime, math, re, uuid, hashlib, db, request."
            },
            {
                "role": "user",
                "content": """Edit the following cloud function code based on this request: Add email notification when a new order is created

EXISTING CODE:
```python
def main():
    try:
        data = request.json()

        if not data.get('user_id'):
            return {'success': False, 'error': 'user_id is required'}

        order = db.create_document('orders', {
            'user_id': data['user_id'],
            'items': data.get('items', []),
            'total': data.get('total', 0),
            'created_at': datetime.datetime.utcnow().isoformat()
        })

        return {'success': True, 'order': order}
    except Exception as e:
        return {'success': False, 'error': str(e)}
```"""
            },
            {
                "role": "assistant",
                "content": """```python
def main():
    try:
        data = request.json()

        if not data.get('user_id'):
            return {'success': False, 'error': 'user_id is required'}

        # Create order
        order = db.create_document('orders', {
            'user_id': data['user_id'],
            'items': data.get('items', []),
            'total': data.get('total', 0),
            'status': 'pending',
            'created_at': datetime.datetime.utcnow().isoformat()
        })

        # Get user email for notification
        user_result = db.query('users', id=data['user_id'])
        if user_result['total'] > 0:
            user = user_result['data'][0]
            user_email = user.get('email', '')

            # Log notification task (email sending happens via webhook/external service)
            db.create_document('notifications', {
                'type': 'order_created',
                'user_id': data['user_id'],
                'email': user_email,
                'order_id': order['id'],
                'data': {
                    'order_number': order['id'],
                    'total': data.get('total', 0),
                    'item_count': len(data.get('items', []))
                },
                'status': 'pending',
                'created_at': datetime.datetime.utcnow().isoformat()
            })

        return {
            'success': True,
            'order': order,
            'notification_queued': user_result['total'] > 0
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}
```

**Changes made:**
1. Added order status field ('pending')
2. Fetches user data to get email address
3. Creates a notification document to queue email sending
4. Returns notification status in response
5. Maintains all original functionality

**Note:** Email notifications are queued in the database. You'll need a separate service/webhook to process the notifications queue and actually send emails."""
            }
        ]
    },

    # Performance optimization pattern
    {
        "messages": [
            {
                "role": "system",
                "content": "You are CocoBase Bot. Generate cloud function code WITHOUT imports. Libraries pre-imported: json, datetime, math, re, uuid, hashlib, db, request."
            },
            {
                "role": "user",
                "content": "Get dashboard stats - total users, posts, and comments (optimize for performance)"
            },
            {
                "role": "assistant",
                "content": """```python
def main():
    try:
        # Use limit=1 for count queries to reduce data transfer
        # We only need the 'total' field, not the actual documents

        users_count = db.query('users', limit=1)['total']
        posts_count = db.query('posts', limit=1)['total']
        comments_count = db.query('comments', limit=1)['total']

        # Get recent activity (last 24 hours)
        yesterday = (datetime.datetime.utcnow() - datetime.timedelta(days=1)).isoformat()

        recent_users = db.query('users', created_at={'$gte': yesterday}, limit=1)['total']
        recent_posts = db.query('posts', created_at={'$gte': yesterday}, limit=1)['total']

        return {
            'success': True,
            'stats': {
                'total_users': users_count,
                'total_posts': posts_count,
                'total_comments': comments_count,
                'recent_activity': {
                    'new_users_24h': recent_users,
                    'new_posts_24h': recent_posts
                }
            },
            'generated_at': datetime.datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
```

This function efficiently retrieves dashboard statistics. It uses limit=1 for count queries to minimize data transfer and improve performance, since we only need totals."""
            }
        ]
    },

    # Error handling edge case
    {
        "messages": [
            {
                "role": "system",
                "content": "You are CocoBase Bot. Generate cloud function code WITHOUT imports. Libraries pre-imported: json, datetime, math, re, uuid, hashlib, db, request."
            },
            {
                "role": "user",
                "content": "Transfer ownership of a post with validation"
            },
            {
                "role": "assistant",
                "content": """```python
def main():
    try:
        data = request.json()

        # Validate required parameters
        post_id = data.get('post_id')
        current_owner_id = data.get('current_owner_id')
        new_owner_id = data.get('new_owner_id')

        if not post_id:
            return {'success': False, 'error': 'post_id is required'}
        if not current_owner_id:
            return {'success': False, 'error': 'current_owner_id is required'}
        if not new_owner_id:
            return {'success': False, 'error': 'new_owner_id is required'}

        # Verify post exists
        post_result = db.query('posts', id=post_id)
        if post_result['total'] == 0:
            return {'success': False, 'error': 'Post not found'}

        post = post_result['data'][0]

        # Verify current ownership
        if post.get('author_id') != current_owner_id:
            return {
                'success': False,
                'error': 'Current owner verification failed. Post belongs to different user.'
            }

        # Verify new owner exists
        new_owner_result = db.query('users', id=new_owner_id)
        if new_owner_result['total'] == 0:
            return {'success': False, 'error': 'New owner user not found'}

        # Transfer ownership
        updated_post = db.update_document('posts', post_id, {
            'author_id': new_owner_id,
            'previous_owner_id': current_owner_id,
            'transferred_at': datetime.datetime.utcnow().isoformat(),
            'updated_at': datetime.datetime.utcnow().isoformat()
        })

        # Log the transfer for audit trail
        db.create_document('audit_logs', {
            'action': 'post_ownership_transfer',
            'post_id': post_id,
            'from_user_id': current_owner_id,
            'to_user_id': new_owner_id,
            'timestamp': datetime.datetime.utcnow().isoformat()
        })

        return {
            'success': True,
            'post': updated_post,
            'message': 'Ownership transferred successfully'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
```

This function safely transfers post ownership with comprehensive validation. It verifies the post exists, checks current ownership, validates the new owner, performs the transfer, and creates an audit log entry."""
            }
        ]
    }
]


def get_suggestions():
    """Print suggestions for creating more training data"""
    print("""
## SUGGESTIONS FOR MORE TRAINING DATA:

### 1. Capture Real Usage (BEST SOURCE)
- Log actual user requests and generated code
- Include successful interactions
- Save code that users kept vs. rejected

### 2. Add More Edge Cases
- Invalid input handling
- Database errors and retries
- Empty result sets
- Duplicate key handling
- Type conversion errors

### 3. Advanced Patterns
- Nested populate: populate=['author', 'comments.user']
- Complex filters: {age: {'$gte': 18, '$lte': 65}}
- Sorting by multiple fields
- Full-text search patterns
- Geospatial queries (if applicable)

### 4. Domain-Specific Logic
- E-commerce: cart, checkout, inventory
- Social: likes, follows, feeds
- Auth: login, permissions, sessions
- Analytics: aggregations, reports

### 5. Code Editing Scenarios
- Add feature to existing code
- Fix bug in code
- Refactor for performance
- Add error handling
- Update API patterns

### 6. Question/Answer Examples
- "How do I query with multiple filters?"
- "What's the best way to handle pagination?"
- "How do I populate nested relationships?"
- "What's the performance limit for queries?"

Target: 200-500 examples for production quality
Current: 48 examples + 6 advanced = 54 examples
Needed: ~150-450 more examples
""")


if __name__ == "__main__":
    print(f"Generated {len(ADVANCED_EXAMPLES)} advanced training examples")
    get_suggestions()
