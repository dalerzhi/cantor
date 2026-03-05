#!/usr/bin/env python3
"""
Cantor 控制台修复后测试
"""

from playwright.sync_api import sync_playwright
import time
import os

def test_dashboard():
    screenshots_dir = "/Users/ceia/.openclaw/workspace/aiwork/cantor/test-screenshots-v2"
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
        print("Cantor 控制台修复后测试")
        print("=" * 60)
        
        # 1. 测试控制台登录页
        print("\n[1/3] 测试 /dashboard/login")
        try:
            page.goto(f"{base_url}/dashboard/login", wait_until="networkidle", timeout=30000)
            time.sleep(3)
            page.screenshot(path=f"{screenshots_dir}/01-login.png", full_page=True)
            title = page.title()
            content = page.content()
            print(f"  标题: {title}")
            
            # 检查是否有登录表单
            email_inputs = page.locator("input[type='email']").count()
            password_inputs = page.locator("input[type='password']").count()
            
            if email_inputs > 0 and password_inputs > 0:
                print(f"  ✅ 检测到登录表单（email: {email_inputs}, password: {password_inputs}）")
            else:
                print(f"  ⚠️ 未检测到登录表单（email: {email_inputs}, password: {password_inputs}）")
                print(f"  页面内容片段: {content[:500]}")
        except Exception as e:
            print(f"  ❌ 错误: {e}")
            page.screenshot(path=f"{screenshots_dir}/01-login-error.png")
        
        # 2. 测试注册页
        print("\n[2/3] 测试 /dashboard/register")
        try:
            page.goto(f"{base_url}/dashboard/register", wait_until="networkidle", timeout=30000)
            time.sleep(3)
            page.screenshot(path=f"{screenshots_dir}/02-register.png", full_page=True)
            title = page.title()
            print(f"  标题: {title}")
            
            inputs = page.locator("input").count()
            print(f"  检测到 {inputs} 个输入字段")
            
            if inputs >= 4:
                print(f"  ✅ 注册表单正常")
            else:
                print(f"  ⚠️ 注册表单可能不完整")
        except Exception as e:
            print(f"  ❌ 错误: {e}")
        
        # 3. 测试首页（重定向检查）
        print("\n[3/3] 测试 /dashboard")
        try:
            page.goto(f"{base_url}/dashboard", wait_until="networkidle", timeout=30000)
            time.sleep(2)
            page.screenshot(path=f"{screenshots_dir}/03-dashboard-index.png", full_page=True)
            
            current_url = page.url
            print(f"  当前URL: {current_url}")
            
            if "login" in current_url:
                print(f"  ✅ 正确重定向到登录页")
            else:
                print(f"  ℹ️ 页面未重定向")
        except Exception as e:
            print(f"  ❌ 错误: {e}")
        
        browser.close()
        
        print("\n" + "=" * 60)
        print("测试完成！截图保存在:")
        print(f"  {screenshots_dir}/")
        print("=" * 60)

if __name__ == "__main__":
    test_dashboard()
