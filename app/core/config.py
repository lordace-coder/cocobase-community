DATABASE_URL = "postgresql://cocobase_owner:npg_zLEhvQOD1Iu9@ep-lucky-glade-a5sg2kpd-pooler.us-east-2.aws.neon.tech/cocobase"

SECRET_KEY = "iawfukcd liqyrbx01yoq2bdhqx2br8oxq2 bxdzbgq 7oxiwtfo zpfbow3owb"


# store securely (e.g., environment variable)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 2  # Two days


DEFAULT_PERMISSION_DICT = dict(
    {
        "create": [],
        "read": [],
        "update": [],
        "delete": [],
    }
)
