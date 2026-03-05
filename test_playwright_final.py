#!/usr/bin/env python3
"""
Cantor 完整业务流程 - Playwright 测试
"""

from playwright.sync_api import sync_playwright
import time
import os

def test_cantor():
    screenshots_dir = "/Users/ceia/.openclaw/workspace/aiwork/cantor/test-final"
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
        print("Cantor Playwright 完整测试")
        print("=" * 60)
        
        # 1. 测试官网首页
        print("\n[1/6] 官网首页 /")
        page.goto(base_url, wait_until="networkidle", timeout=30000)
        time.sleep(2)
        page.screenshot(path=f"{screenshots_dir}/01-homepage.png", full_page=True)
        print(f"  ✅ 标题: {page.title()[:50]}")
        
        # 2. 测试登录页
        print("\n[2/6] 登录页 /dashboard/login")
        page.goto(f"{base_url}/dashboard/login", wait_until="networkidle", timeout=30000)
        time.sleep(2)
        page.screenshot(path=f"{screenshots_dir}/02-login.png", full_page=True)
        
        email_count = page.locator("input[type='email']").count()
        password_count = page.locator("input[type='password']").count()
        print(f"  ✅ Email输入框: {email_count}, 密码输入框: {password_count}")
        
        # 3. 测试注册页
        print("\n[3/6] 注册页 /dashboard/register")
        page.goto(f"{base_url}/dashboard/register", wait_until="networkidle", timeout=30000)
        time.sleep(2)
        page.screenshot(path=f"{screenshots_dir}/03-register.png", full_page=True)
        
        inputs = page.locator("input").count()
        print(f"  ✅ 表单输入框数量: {inputs}")
        
        # 4. 登录流程
        print("\n[4/6] 执行登录流程")
        page.goto(f"{base_url}/dashboard/login", wait_until="networkidle")
        time.sleep(1)
        
        # 使用之前 API 测试创建的账号
        page.locator("input[type='email']").fill("apitest@example.com")
        page.locator("input[type='password']").fill("ApiTest123456!")
        page.screenshot(path=f"{screenshots_dir}/04-login-filled.png")
        
        page.locator("button[type='submit']").click()
        time.sleep(3)
        page.screenshot(path=f"{screenshots_dir}/05-after-login.png", full_page=True)
        
        current_url = page.url
        print(f"  登录后URL: {current_url}")
        
        if "login" not in current_url:
            print(f"  ✅ 登录成功")
            
            # 5. 访问云手机页面
            print("\n[5/6] 云手机列表 /dashboard/cloud-phones")
            page.goto(f"{base_url}/dashboard/cloud-phones", wait_until="networkidle", timeout=30000)
            time.sleep(3)
            page.screenshot(path=f"{screenshots_dir}/06-cloud-phones.png", full_page=True)
            
            content = page.content()
            if "云手机" in content or "实例" in content:
                print(f"  ✅ 云手机页面加载成功")
            else:
                print(f"  ⚠️ 页面可能需要同步数据")
            
            # 6. 访问设备页面
            print("\n[6/6] 设备列表 /dashboard/devices")
            page.goto(f"{base_url}/dashboard/devices", wait_until="networkidle", timeout=30000)
            time.sleep(3)
            page.screenshot(path=f"{screenshots_dir}/07-devices.png", full_page=True)
            print(f"  ✅ 设备页面已截图")
        else:
            print(f"  ⚠️ 登录可能失败或需要注册")
        
        browser.close()
        
        print("\n" + "=" * 60)
        print("Playwright 测试完成！")
        print(f"截图保存: {screenshots_dir}/")
        print("=" * 60)
        
        # 列出所有截图
        files = sorted(os.listdir(screenshots_dir))
        print("\n生成的截图:")
        for f in files:
            if f.endswith('.png'):
                print(f"  📸 {f}")

if __name__ == "__main__":
    test_cantor()
