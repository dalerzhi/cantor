#!/usr/bin/env python3
"""
Cantor 端到端集成测试脚本
测试流程:
1. 检查服务状态
2. 创建设备
3. 通过 Redis 模拟发送命令到设备
4. 验证消息流转
"""

import asyncio
import json
import sys
import time
from datetime import datetime

import requests
import redis.asyncio as redis
import websockets

# 配置
BRAIN_API = "http://localhost:8000"
GATEWAY_WS = "ws://localhost:8766/ws"
REDIS_URL = "redis://localhost:6379/0"

# 颜色输出
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def log_info(msg):
    print(f"{GREEN}[INFO]{RESET} {msg}")


def log_warn(msg):
    print(f"{YELLOW}[WARN]{RESET} {msg}")


def log_error(msg):
    print(f"{RED}[ERROR]{RESET} {msg}")


def log_step(step_num, msg):
    print(f"\n{YELLOW}▶ Step {step_num}:{RESET} {msg}")


async def check_services():
    """检查 Brain API 是否可访问"""
    log_step(1, "检查服务状态")
    
    try:
        # 检查 Brain
        resp = requests.get(f"{BRAIN_API}/api/health", timeout=5)
        if resp.status_code == 200:
            log_info(f"Brain API 运行正常: {resp.json()}")
        else:
            log_error(f"Brain API 返回异常状态码: {resp.status_code}")
            return False
    except Exception as e:
        log_error(f"Brain API 无法连接: {e}")
        log_warn("请先运行: ./scripts/start-all.sh")
        return False
    
    # 检查 Redis
    try:
        r = await redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        await r.ping()
        log_info("Redis 连接正常")
        await r.aclose()
    except Exception as e:
        log_error(f"Redis 无法连接: {e}")
        return False
    
    return True


async def create_device():
    """通过 API 创建设备"""
    log_step(2, "创建设备")
    
    device_data = {
        "name": f"test-device-{int(time.time())}",
        "ip_address": "127.0.0.1"
    }
    
    try:
        resp = requests.post(
            f"{BRAIN_API}/api/devices",
            json=device_data,
            timeout=5
        )
        if resp.status_code == 201:
            device = resp.json()
            log_info(f"设备创建成功: ID={device['id']}, name={device['name']}")
            return device
        else:
            log_error(f"创建设备失败: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        log_error(f"创建设备请求异常: {e}")
        return None


async def simulate_device_connection(device_id):
    """模拟设备 WebSocket 连接"""
    log_step(3, "模拟设备 WebSocket 连接")
    
    ws_url = f"{GATEWAY_WS}?device_id={device_id}"
    log_info(f"连接 Gateway: {ws_url}")
    
    try:
        ws = await websockets.connect(ws_url)
        log_info(f"设备 {device_id} 已连接到 Gateway")
        return ws
    except Exception as e:
        log_error(f"WebSocket 连接失败: {e}")
        return None


async def test_command_flow(device_id, ws):
    """测试命令下发流程"""
    log_step(4, "测试命令下发流程")
    
    received_messages = []
    test_command = {"action": "test", "payload": "hello from brain", "timestamp": time.time()}
    
    # 启动消息接收任务
    async def receive_messages():
        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
                received_messages.append(msg)
                log_info(f"设备收到消息: {msg}")
        except asyncio.TimeoutError:
            log_info("消息接收超时 (正常)")
        except websockets.exceptions.ConnectionClosed:
            log_warn("WebSocket 连接已关闭")
    
    # 连接 Redis 并发送命令
    r = await redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    
    # 启动接收任务
    recv_task = asyncio.create_task(receive_messages())
    
    # 等待连接稳定
    await asyncio.sleep(0.5)
    
    # 发送命令到 Redis (Brain -> Gateway)
    channel = f"cantor:commands:{device_id}"
    log_info(f"通过 Redis 发送命令到 {channel}")
    await r.publish(channel, json.dumps(test_command))
    
    # 等待接收
    await asyncio.sleep(1)
    recv_task.cancel()
    
    try:
        await recv_task
    except asyncio.CancelledError:
        pass
    
    await r.aclose()
    
    # 验证结果
    if received_messages:
        log_info(f"✅ 命令流转测试通过! 收到 {len(received_messages)} 条消息")
        for msg in received_messages:
            try:
                data = json.loads(msg)
                if data.get("action") == "test":
                    log_info(f"✅ 命令内容验证通过: {data}")
                    return True
            except json.JSONDecodeError:
                pass
    else:
        log_error("❌ 未收到任何消息")
    
    return len(received_messages) > 0


async def test_event_flow(device_id, ws):
    """测试事件上报流程"""
    log_step(5, "测试事件上报流程")
    
    test_event = {"type": "status", "status": "online", "timestamp": time.time()}
    received_events = []
    
    # 连接 Redis 订阅设备事件
    r = await redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.psubscribe("device:events:*")
    
    # 启动事件监听任务
    async def listen_events():
        try:
            async for message in pubsub.listen():
                if message["type"] in ("message", "pmessage"):
                    received_events.append({
                        "channel": message["channel"],
                        "data": message["data"]
                    })
                    log_info(f"Brain 收到事件: {message['channel']} = {message['data']}")
        except asyncio.CancelledError:
            pass
    
    listen_task = asyncio.create_task(listen_events())
    
    # 等待订阅建立
    await asyncio.sleep(0.5)
    
    # 发送事件 (Device -> Gateway -> Redis)
    log_info(f"设备发送事件: {test_event}")
    await ws.send(json.dumps(test_event))
    
    # 等待接收
    await asyncio.sleep(1)
    listen_task.cancel()
    
    try:
        await listen_task
    except asyncio.CancelledError:
        pass
    
    await pubsub.punsubscribe()
    await pubsub.close()
    await r.aclose()
    
    # 验证结果
    if received_events:
        log_info(f"✅ 事件上报测试通过! 收到 {len(received_events)} 个事件")
        for event in received_events:
            if device_id in event["channel"]:
                log_info(f"✅ 事件通道验证通过: {event['channel']}")
                return True
    else:
        log_error("❌ 未收到任何事件")
    
    return len(received_events) > 0


async def cleanup_device(device_id):
    """清理测试设备"""
    log_step(6, "清理测试数据")
    try:
        resp = requests.delete(f"{BRAIN_API}/api/devices/{device_id}", timeout=5)
        if resp.status_code == 204:
            log_info(f"测试设备 {device_id} 已删除")
        else:
            log_warn(f"删除设备返回: {resp.status_code}")
    except Exception as e:
        log_warn(f"清理设备失败: {e}")


async def run_e2e_test():
    """运行端到端测试"""
    print("=" * 60)
    print("🧪 Cantor 端到端集成测试")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 检查服务
    if not await check_services():
        log_error("服务检查失败，测试中止")
        return False
    
    # 创建设备
    device = await create_device()
    if not device:
        log_error("设备创建失败，测试中止")
        return False
    
    device_id = device["id"]
    ws = None
    results = []
    
    try:
        # 连接设备
        ws = await simulate_device_connection(device_id)
        if not ws:
            log_error("设备连接失败")
            return False
        
        # 测试命令下发
        cmd_result = await test_command_flow(device_id, ws)
        results.append(("命令下发", cmd_result))
        
        # 测试事件上报
        event_result = await test_event_flow(device_id, ws)
        results.append(("事件上报", event_result))
        
    finally:
        # 关闭 WebSocket
        if ws:
            await ws.close()
            log_info("WebSocket 连接已关闭")
        
        # 清理设备
        await cleanup_device(device_id)
    
    # 测试总结
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = f"{GREEN}✅ 通过{RESET}" if passed else f"{RED}❌ 失败{RESET}"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print(f"{GREEN}🎉 所有测试通过!{RESET}")
    else:
        print(f"{RED}⚠️ 部分测试失败{RESET}")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    # 检查依赖
    try:
        import requests
        import redis.asyncio
        import websockets
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请安装: pip install requests redis websockets")
        sys.exit(1)
    
    # 运行测试
    success = asyncio.run(run_e2e_test())
    sys.exit(0 if success else 1)
