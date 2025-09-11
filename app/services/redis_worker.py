import redis

REDIS_URL = (
    "redis://default:269473f8b00b4e2cac1d08be8e1634f2@fly-jobist-redis.upstash.io:6379"
)
instance = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
)
