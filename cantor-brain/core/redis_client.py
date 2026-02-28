import asyncio
import logging
from redis.asyncio import Redis, from_url

from typing import Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Global Redis client
redis_client: Optional[Redis] = None

async def init_redis():
    global redis_client
    redis_client = await from_url("redis://localhost:6379/0", encoding="utf-8", decode_responses=True)
    logger.info("Connected to Redis")

async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.aclose()
        logger.info("Closed Redis connection")

async def subscribe_to_device_events():
    global redis_client
    if not redis_client:
        return
    
    pubsub = redis_client.pubsub()
    await pubsub.psubscribe("device:events:*")
    logger.info("Subscribed to device:events:*")
    
    try:
        async for message in pubsub.listen():
            if message["type"] in ("message", "pmessage"):
                channel = message["channel"]
                data = message["data"]
                logger.info(f"Received from {channel}: {data}")
    except asyncio.CancelledError:
        logger.info("Redis listener cancelled")
    except Exception as e:
        logger.error(f"Redis listener error: {e}")
    finally:
        try:
            await pubsub.punsubscribe("device:events:*")
            await pubsub.close()
        except Exception:
            pass

async def send_device_command(device_id: str, command_data: str):
    global redis_client
    if not redis_client:
        logger.error("Redis client not initialized")
        return False
    
    channel = f"cantor:commands:{device_id}"
    await redis_client.publish(channel, command_data)
    logger.info(f"Published command to {channel}: {command_data}")
    return True