#!/usr/bin/env python3
"""
测试注册流程
"""

from playwright.sync_api import sync_playwright
import time
import os

def test_register():
    screenshots_dir = "/Users/ceia/.openclaw/workspace/aiwork/cantor/test-register"
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
        print("测试注册流程")
        print("=" * 60)
        
        # 访问注册页
        print("\n[1/3] 访问注册页")
        page.goto(f"{base_url}/dashboard/register", wait_until="networkidle", timeout=30000)
        time.sleep(2)
        page.screenshot(path=f"{screenshots_dir}/01-register.png", full_page=True)
        print(f"  ✅ 页面标题: {page.title()}")
        
        # 填写注册表单
        print("\n[2/3] 填写注册表单")
        timestamp = int(time.time())
        
        page.locator("input[name='name']").fill("Playwright Test")
        page.locator("input[type='email']").fill(f"playwright{timestamp}@test.com")
        page.locator("input[name='org_name']").fill("Playwright Org")
        page.locator("input[name='org_slug']").fill(f"playwright-org-{timestamp}")
        
        # 密码
        passwords = page.locator("input[type='password']").all()
        if len(passwords) >= 2:
            passwords[0].fill("Playwright@123456")
            passwords[1].fill("Playwright@123456")
        
        page.screenshot(path=f"{screenshots_dir}/02-register-filled.png")
        print(f"  ✅ 表单已填写")
        
        # 提交注册
        print("\n[3/3] 提交注册")
        page.locator("button[type='submit']").click()
        time.sleep(5)
        page.screenshot(path=f"{screenshots_dir}/03-after-submit.png", full_page=True)
        
        current_url = page.url
        print(f"  提交后URL: {current_url}")
        
        # 检查是否有错误信息
        error_text = page.locator("text=/error|failed|错误|失败/i").first.inner_text() if page.locator("text=/error|failed|错误|失败/i").count() > 0 else "无错误"
        print(f"  错误信息: {error_text[:100]}")
        
        if "login" not in current_url and "register" not in current_url:
            print(f"  ✅ 注册成功，已跳转到: {current_url}")
        else:
            print(f"  ⚠️ 可能注册失败或需要处理")
        
        browser.close()
        
        print("\n" + "=" * 60)
        print("注册测试完成")
        print("=" * 60)

if __name__ == "__main__":
    test_register()
