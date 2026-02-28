import json
import uuid
import logging
from typing import Dict, Optional, Any
from datetime import datetime

from core.redis_client import redis_client

logger = logging.getLogger(__name__)


class TaskStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


async def publish_task(cantor_id: str, task_data: Dict[str, Any]) -> str:
    """
    Publish a task to the Cantor instance's task queue.
    
    Args:
        cantor_id: The Cantor instance ID
        task_data: Task data dictionary containing task details
        
    Returns:
        task_id: The generated task ID
    """
    global redis_client
    
    if not redis_client:
        logger.error("Redis client not initialized")
        raise RuntimeError("Redis client not initialized")
    
    # Generate unique task ID
    task_id = f"task_{uuid.uuid4().hex[:12]}"
    
    # Build task message
    task_message = {
        "id": task_id,
        "cantor_id": cantor_id,
        "data": task_data,
        "status": TaskStatus.PENDING,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "result": None,
        "error": None
    }
    
    # Push to Redis queue
    queue_key = f"cantor:{cantor_id}:queue"
    
    # Store task in hash for status tracking
    task_key = f"task:{task_id}"
    await redis_client.hset(task_key, mapping={
        "id": task_id,
        "cantor_id": cantor_id,
        "data": json.dumps(task_data),
        "status": TaskStatus.PENDING,
        "created_at": task_message["created_at"],
        "updated_at": task_message["updated_at"],
        "result": "",
        "error": ""
    })
    
    # Push task ID to queue
    await redis_client.lpush(queue_key, task_id)
    
    logger.info(f"Published task {task_id} to queue {queue_key}")
    
    return task_id


async def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Get task status from Redis.
    
    Args:
        task_id: The task ID to query
        
    Returns:
        Task status dictionary or None if not found
    """
    global redis_client
    
    if not redis_client:
        logger.error("Redis client not initialized")
        raise RuntimeError("Redis client not initialized")
    
    task_key = f"task:{task_id}"
    task_data = await redis_client.hgetall(task_key)
    
    if not task_data:
        return None
    
    # Parse task data
    result = {
        "id": task_data.get("id"),
        "cantor_id": task_data.get("cantor_id"),
        "status": task_data.get("status"),
        "created_at": task_data.get("created_at"),
        "updated_at": task_data.get("updated_at"),
        "data": json.loads(task_data.get("data", "{}")),
        "result": task_data.get("result") if task_data.get("result") else None,
        "error": task_data.get("error") if task_data.get("error") else None
    }
    
    return result


async def update_task_status(task_id: str, status: str, result: Optional[str] = None, error: Optional[str] = None):
    """
    Update task status in Redis.
    
    Args:
        task_id: The task ID
        status: New status (pending/processing/completed/failed)
        result: Optional result data
        error: Optional error message
    """
    global redis_client
    
    if not redis_client:
        logger.error("Redis client not initialized")
        return False
    
    task_key = f"task:{task_id}"
    
    update_data = {
        "status": status,
        "updated_at": datetime.now().isoformat()
    }
    
    if result is not None:
        update_data["result"] = result
    
    if error is not None:
        update_data["error"] = error
    
    await redis_client.hset(task_key, mapping=update_data)
    logger.info(f"Updated task {task_id} status to {status}")
    
    return True


async def get_queue_length(cantor_id: str) -> int:
    """
    Get the number of pending tasks in a Cantor instance's queue.
    
    Args:
        cantor_id: The Cantor instance ID
        
    Returns:
        Number of tasks in queue
    """
    global redis_client
    
    if not redis_client:
        return 0
    
    queue_key = f"cantor:{cantor_id}:queue"
    return await redis_client.llen(queue_key)


async def pop_task(cantor_id: str) -> Optional[Dict[str, Any]]:
    """
    Pop a task from the Cantor instance's queue.
    Used by workers to get tasks to process.
    
    Args:
        cantor_id: The Cantor instance ID
        
    Returns:
        Task data or None if queue is empty
    """
    global redis_client
    
    if not redis_client:
        return None
    
    queue_key = f"cantor:{cantor_id}:queue"
    
    # Pop from right side of list (FIFO)
    task_id = await redis_client.rpop(queue_key)
    
    if not task_id:
        return None
    
    # Get full task data
    task_data = await get_task_status(task_id)
    
    if task_data:
        # Update status to processing
        await update_task_status(task_id, TaskStatus.PROCESSING)
        task_data["status"] = TaskStatus.PROCESSING
    
    return task_data