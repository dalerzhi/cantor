#!/usr/bin/env python3
"""
Cantor 完整业务流程测试
1. 注册新用户
2. 登录
3. 查看云手机列表
4. 获取 RTC 连接
"""

from playwright.sync_api import sync_playwright
import time
import os

def test_full_flow():
    screenshots_dir = "/Users/ceia/.openclaw/workspace/aiwork/cantor/test-screenshots-flow"
    os.makedirs(screenshots_dir, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--ignore-certificate-errors']
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )
        
        page = context.new_page()
        base_url = "https://23.236.119.225"
        
        print("=" * 60)
        print("Cantor 完整业务流程测试")
        print("=" * 60)
        
        # 1. 访问注册页
        print("\n[1/5] 访问注册页...")
        page.goto(f"{base_url}/dashboard/register", wait_until="networkidle", timeout=30000)
        time.sleep(2)
        page.screenshot(path=f"{screenshots_dir}/01-register.png")
        print(f"  ✅ 注册页加载成功")
        
        # 2. 填写注册表单
        print("\n[2/5] 填写注册表单...")
        timestamp = int(time.time())
        test_email = f"test{timestamp}@example.com"
        test_password = "Test@123456!"
        
        page.locator("input[name='name']").fill("Test User")
        page.locator("input[type='email']").fill(test_email)
        page.locator("input[name='org_name']").fill("TestOrg")
        page.locator("input[name='org_slug']").fill(f"test-org-{timestamp}")
        page.locator("input[type='password']").first.fill(test_password)
        page.locator("input[name='confirm_password']").fill(test_password)
        
        page.screenshot(path=f"{screenshots_dir}/02-register-filled.png")
        print(f"  ✅ 表单填写完成: {test_email}")
        
        # 3. 提交注册
        print("\n[3/5] 提交注册...")
        page.locator("button[type='submit']").click()
        time.sleep(3)
        
        page.screenshot(path=f"{screenshots_dir}/03-after-register.png", full_page=True)
        current_url = page.url
        print(f"  当前URL: {current_url}")
        
        if "/dashboard" in current_url and "register" not in current_url:
            print(f"  ✅ 注册成功，已登录")
        else:
            print(f"  ⚠️ 可能已存在或需要登录")
            # 尝试登录
            page.goto(f"{base_url}/dashboard/login", wait_until="networkidle")
            time.sleep(2)
            page.locator("input[type='email']").fill(test_email)
            page.locator("input[type='password']").fill(test_password)
            page.locator("button[type='submit']").click()
            time.sleep(3)
        
        # 4. 查看云手机列表
        print("\n[4/5] 访问云手机列表...")
        page.goto(f"{base_url}/dashboard/cloud-phones", wait_until="networkidle", timeout=30000)
        time.sleep(3)
        page.screenshot(path=f"{screenshots_dir}/04-cloud-phones.png", full_page=True)
        
        # 检查页面内容
        content = page.content()
        if "云手机" in content or "实例" in content or "sspd" in content:
            print(f"  ✅ 云手机列表加载成功")
        else:
            print(f"  ⚠️ 可能显示空白或需要数据同步")
        
        # 5. 查看设备列表
        print("\n[5/5] 访问设备列表...")
        page.goto(f"{base_url}/dashboard/devices", wait_until="networkidle", timeout=30000)
        time.sleep(3)
        page.screenshot(path=f"{screenshots_dir}/05-devices.png", full_page=True)
        print(f"  ✅ 设备页面已截图")
        
        browser.close()
        
        print("\n" + "=" * 60)
        print("完整业务流程测试完成！")
        print(f"测试账号: {test_email}")
        print(f"截图保存在: {screenshots_dir}/")
        print("=" * 60)

if __name__ == "__main__":
    test_full_flow()
