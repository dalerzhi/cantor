import asyncio
from unittest.mock import AsyncMock, MagicMock
import core.redis_client

async def test():
    # Mock Redis
    mock_redis = AsyncMock()
    mock_pubsub = MagicMock()
    mock_redis.pubsub.return_value = mock_pubsub
    
    # Mock pubsub.listen()
    async def mock_listen():
        yield {"type": "message", "channel": "device:events:123", "data": "hello"}
        await asyncio.sleep(0.1) # Keep alive
    
    mock_pubsub.listen = mock_listen
    core.redis_client.from_url = AsyncMock(return_value=mock_redis)

    # Init
    await core.redis_client.init_redis()
    
    # Start background task
    task = asyncio.create_task(core.redis_client.subscribe_to_device_events())
    
    await asyncio.sleep(0.2)
    
    # Test publish
    await core.redis_client.send_device_command("456", "turn_on")
    
    # Verify mock
    mock_redis.publish.assert_called_with("cantor:commands:456", "turn_on")
    mock_pubsub.psubscribe.assert_called_with("device:events:*")
    
    # Cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    await core.redis_client.close_redis()
    print("Test passed successfully with mocks.")

if __name__ == "__main__":
    asyncio.run(test())