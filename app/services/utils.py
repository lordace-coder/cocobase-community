import secrets
import bcrypt
import requests


def hash_password(raw_password):
    return bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(raw_password, hashed_password):
    return bcrypt.checkpw(raw_password.encode("utf-8"), hashed_password.encode("utf-8"))


def generate_api_key():
    return secrets.token_urlsafe(30)


def handle_webhook_call(url, data, isUpdate=False):
    data["isUpdate"] = isUpdate
    if not url:
        return
    try:

        x = requests.post(url, json=data)
        if not x.ok:
            ...
            # email user that webhook failed
    except:
        pass
