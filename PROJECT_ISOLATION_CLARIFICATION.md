# Project Isolation in AppUsers - Technical Clarification

## ✅ Correct Field: `client_id`

AppUsers are linked to projects via the `client_id` field, not `project_id`.

```python
class AppUser(Base):
    __tablename__ = "app_users"
    id = Column(String, primary_key=True)
    client_id = Column(String, ForeignKey("projects.id"))  # ← Links to Project
    email = Column(String, nullable=False)
    data = Column(JSON, nullable=True)
    # ...
```

---

## 🔒 How Project Isolation Actually Works

### 1. Base Query Filtering

```python
# All AppUser queries filter by client_id
query = db.query(AppUser).filter(AppUser.client_id == project.id)
#                                 ^^^^^^^^^^^^^^^^^^^
#                                 Correct field name
```

**Where this happens in code:**

- Line 42: Login check
- Line 74: User count check
- Line 117: Signup check
- Line 194: List users query
- Line 324: Populate followers
- Line 360: Populate single relationship
- Line 511: Get user by ID

---

### 2. Relationship Population

When populating AppUser relationships (followers, following, etc.):

```python
# Try to populate from AppUsers with client_id filter
related_user = db.query(AppUser).filter(
    AppUser.id == related_id,
    AppUser.client_id == project.id  # ← Only same project
).first()
```

This ensures:

- ✅ Followers are only from the same project
- ✅ Following relationships stay within project
- ✅ Cannot link to users from other projects

---

### 3. Complete Isolation Flow

```
User Request with API Key
    ↓
Validate API Key → Get Project
    ↓
ALL queries filter by: client_id == project.id
    ↓
    ├── List users: WHERE client_id = 'proj-a'
    ├── Get user: WHERE client_id = 'proj-a' AND id = 'user-123'
    ├── Populate followers: WHERE client_id = 'proj-a' AND id IN (...)
    └── Update user: WHERE client_id = 'proj-a' AND id = 'user-123'
    ↓
Return ONLY data from that project
```

---

## 📊 Real Example

```
Database:
┌─────────────────────────────────────────────┐
│ app_users table                             │
├─────────────┬──────────┬──────────────────┬─┤
│ id          │client_id │ email            │ │
├─────────────┼──────────┼──────────────────┼─┤
│ user-a1     │ proj-a   │ user1@a.com      │ │
│ user-a2     │ proj-a   │ user2@a.com      │ │
│ user-b1     │ proj-b   │ user1@b.com      │ │
│ user-b2     │ proj-b   │ user2@b.com      │ │
└─────────────┴──────────┴──────────────────┴─┘

Query from Project A:
GET /auth-collections/users

Executed SQL:
SELECT * FROM app_users
WHERE client_id = 'proj-a';

Result:
[user-a1, user-a2]  ✅
NOT [user-b1, user-b2]  ❌
```

---

## 🔗 Relationship Example

```
Project A:
- user-a1: { "following_ids": ["user-a2", "user-b1"] }
- user-a2: { "followers_ids": ["user-a1"] }

Project B:
- user-b1: { "followers_ids": [] }

Query: GET /proj-a/users?populate=following_ids

Populate logic:
1. Get following_ids = ["user-a2", "user-b1"]
2. Query: SELECT * FROM app_users
         WHERE id IN ('user-a2', 'user-b1')
         AND client_id = 'proj-a'  ← Filter!
3. Result: Only user-a2 (user-b1 filtered out)

Final response:
{
  "following_ids": ["user-a2", "user-b1"],
  "following_ids_populated": [
    { "id": "user-a2", ... }  ← Only from Project A
  ]
}
```

---

## ✅ Security Guarantees

| Operation              | client_id Filter   | Code Location |
| ---------------------- | ------------------ | ------------- |
| List users             | ✅ Always applied  | Line 194      |
| Get by ID              | ✅ Always applied  | Line 511      |
| Login                  | ✅ Always applied  | Line 42       |
| Signup                 | ✅ Set on creation | Line 127      |
| Populate followers     | ✅ Always applied  | Line 324      |
| Populate relationships | ✅ Always applied  | Line 360      |
| OAuth login            | ✅ Always applied  | Line 673      |

---

## 🎯 Key Points

1. **Field Name**: It's `client_id`, not `project_id`
2. **Foreign Key**: Links to `projects.id`
3. **Always Filtered**: Every query includes `client_id == project.id`
4. **Relationships**: Only populate users with same `client_id`
5. **Complete Isolation**: No way to access other projects' users

---

## 📝 Model Definition

```python
class AppUser(Base):
    __tablename__ = "app_users"

    id = Column(String, primary_key=True)
    client_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    #          ^^^^^^^^^ Links to Project

    email = Column(String, nullable=False)
    password = Column(String, nullable=False)
    data = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    oauth_id = Column(String, nullable=True, unique=True)
    roles = Column(PickleType, nullable=True, default=list)

    # Unique constraint: same email can exist in different projects
    __table_args__ = (
        UniqueConstraint("client_id", "email", name="uq_client_email"),
    )
```

---

## 🔍 Why `client_id`?

The naming comes from treating each project as a "client" of the BaaS platform:

- **Platform level**: CocoBase (your BaaS)
- **Client level**: Projects (your users' applications)
- **End-user level**: AppUsers (your users' users)

```
CocoBase Platform
  └── Project A (client_id: proj-a)
      └── AppUsers (client_id = proj-a)
          ├── user-a1
          └── user-a2
  └── Project B (client_id: proj-b)
      └── AppUsers (client_id = proj-b)
          ├── user-b1
          └── user-b2
```

---

**Summary: Every AppUser operation filters by `client_id` to ensure complete project isolation!** 🔒
