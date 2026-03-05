#!/usr/bin/env python3
"""
Cantor 修复后完整测试 - 包含注册、登录、查看云手机
"""

from playwright.sync_api import sync_playwright
import time
import os

def test_full_flow():
    screenshots_dir = "/Users/ceia/.openclaw/workspace/aiwork/cantor/test-fixed"
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
        print("Cantor 修复后 Playwright 测试")
        print("=" * 60)
        
        # 1. 注册新用户
        print("\n[1/6] 注册新用户")
        page.goto(f"{base_url}/dashboard/register", wait_until="networkidle", timeout=30000)
        time.sleep(2)
        
        timestamp = int(time.time())
        test_email = f"user{timestamp}@test.com"
        test_password = "Test@12345678"  # 至少12位
        
        page.locator("input[name='name']").fill("Test User")
        page.locator("input[type='email']").fill(test_email)
        page.locator("input[name='org_name']").fill("TestOrg")
        page.locator("input[name='org_slug']").fill(f"test-org-{timestamp}")
        
        passwords = page.locator("input[type='password']").all()
        if len(passwords) >= 2:
            passwords[0].fill(test_password)
            passwords[1].fill(test_password)
        
        page.screenshot(path=f"{screenshots_dir}/01-register.png")
        print(f"  填写: {test_email}")
        
        page.locator("button[type='submit']").click()
        time.sleep(5)
        page.screenshot(path=f"{screenshots_dir}/02-after-register.png", full_page=True)
        
        url_after_register = page.url
        print(f"  注册后URL: {url_after_register}")
        
        # 2. 检查是否成功
        if "login" in url_after_register:
            print("  ⚠️ 需要登录，尝试登录")
            page.locator("input[type='email']").fill(test_email)
            page.locator("input[type='password']").fill(test_password)
            page.screenshot(path=f"{screenshots_dir}/03-login.png")
            page.locator("button[type='submit']").click()
            time.sleep(5)
        
        url_final = page.url
        print(f"  最终URL: {url_final}")
        
        if "/dashboard" in url_final and "login" not in url_final and "register" not in url_final:
            print("  ✅ 登录成功！")
            
            # 3. 查看 Dashboard
            print("\n[2/6] Dashboard 首页")
            page.screenshot(path=f"{screenshots_dir}/04-dashboard.png", full_page=True)
            print(f"  ✅ 已截图")
            
            # 4. 查看云手机
            print("\n[3/6] 云手机列表")
            page.goto(f"{base_url}/dashboard/cloud-phones", wait_until="networkidle", timeout=30000)
            time.sleep(3)
            page.screenshot(path=f"{screenshots_dir}/05-cloud-phones.png", full_page=True)
            
            content = page.content()
            if "同步" in content or "实例" in content or "sspd" in content:
                print("  ✅ 云手机数据已加载")
            else:
                print(f"  ℹ️ 页面内容: {content[:300]}")
            
            # 5. 查看设备
            print("\n[4/6] 设备列表")
            page.goto(f"{base_url}/dashboard/devices", wait_until="networkidle", timeout=30000)
            time.sleep(3)
            page.screenshot(path=f"{screenshots_dir}/06-devices.png", full_page=True)
            print(f"  ✅ 已截图")
            
            # 6. 尝试查看第一个设备详情
            print("\n[5/6] 尝试查看设备详情")
            links = page.locator("a[href*='/devices/']").all()
            if len(links) > 0:
                links[0].click()
                time.sleep(3)
                page.screenshot(path=f"{screenshots_dir}/07-device-detail.png", full_page=True)
                print(f"  ✅ 已截图设备详情")
            else:
                print(f"  ⚠️ 没有可点击的设备")
                
        else:
            print(f"  ❌ 登录失败或仍在登录页")
            # 检查错误信息
            error_msg = page.locator("text=/error|failed|错误|失败/i").first.inner_text() if page.locator("text=/error|failed|错误|失败/i").count() > 0 else "无错误信息"
            print(f"  错误: {error_msg}")
        
        browser.close()
        
        print("\n" + "=" * 60)
        print("测试完成！")
        print(f"账号: {test_email}")
        print(f"密码: {test_password}")
        print(f"截图: {screenshots_dir}/")
        print("=" * 60)

if __name__ == "__main__":
    test_full_flow()
