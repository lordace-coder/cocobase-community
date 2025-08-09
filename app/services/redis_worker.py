import redis

REDIS_URL = "redis://default:ixV21Gy0eLUXUU3Vz8el8iwYHdOxRV3Z@redis-12065.c245.us-east-1-3.ec2.redns.redis-cloud.com:12065"
instance = redis.Redis.from_url(
    "redis://default:ixV21Gy0eLUXUU3Vz8el8iwYHdOxRV3Z@redis-12065.c245.us-east-1-3.ec2.redns.redis-cloud.com:12065",
    decode_responses=True,
)
