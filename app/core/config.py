import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
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
