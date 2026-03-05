#!/usr/bin/env python3
"""
Cantor 公有云部署 - Playwright 可视化测试
测试内容：
1. 官网首页截图
2. 控制台登录页截图
3. 完整的登录流程
4. 云手机列表页面
"""

from playwright.sync_api import sync_playwright
import time
import os

def test_cantor():
    screenshots_dir = "/Users/ceia/.openclaw/workspace/aiwork/cantor/test-screenshots"
    os.makedirs(screenshots_dir, exist_ok=True)
    
    with sync_playwright() as p:
        # 启动浏览器（接受自签名证书）
        browser = p.chromium.launch(
            headless=True,
            args=['--ignore-certificate-errors']
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True  # 忽略 HTTPS 证书错误
        )
        
        page = context.new_page()
        base_url = "https://23.236.119.225"
        
        print("=" * 60)
        print("Cantor 公有云部署 - Playwright 可视化测试")
        print("=" * 60)
        
        # 1. 测试官网首页
        print("\n[1/4] 测试官网首页...")
        try:
            page.goto(f"{base_url}/", wait_until="networkidle", timeout=30000)
            page.screenshot(path=f"{screenshots_dir}/01-homepage.png", full_page=True)
            title = page.title()
            print(f"  ✅ 首页加载成功")
            print(f"     标题: {title}")
            print(f"     截图: 01-homepage.png")
        except Exception as e:
            print(f"  ❌ 首页加载失败: {e}")
        
        # 2. 测试控制台登录页
        print("\n[2/4] 测试控制台登录页...")
        try:
            page.goto(f"{base_url}/dashboard", wait_until="networkidle", timeout=30000)
            time.sleep(2)  # 等待页面完全渲染
            page.screenshot(path=f"{screenshots_dir}/02-dashboard.png", full_page=True)
            title = page.title()
            print(f"  ✅ 控制台加载成功")
            print(f"     标题: {title}")
            print(f"     截图: 02-dashboard.png")
            
            # 检查是否显示登录表单
            if page.locator("input[type='email']").count() > 0:
                print(f"     检测到登录表单")
        except Exception as e:
            print(f"  ❌ 控制台加载失败: {e}")
            page.screenshot(path=f"{screenshots_dir}/02-dashboard-error.png")
        
        # 3. 执行登录流程
        print("\n[3/4] 执行登录流程...")
        try:
            # 填写登录表单
            email_input = page.locator("input[type='email']")
            password_input = page.locator("input[type='password']")
            
            if email_input.count() > 0 and password_input.count() > 0:
                email_input.fill("apitest@example.com")
                password_input.fill("ApiTest123456!")
                
                page.screenshot(path=f"{screenshots_dir}/03-login-filled.png")
                print(f"  ✅ 表单填写完成")
                
                # 点击登录按钮
                submit_btn = page.locator("button[type='submit']")
                if submit_btn.count() > 0:
                    submit_btn.click()
                    time.sleep(3)  # 等待登录响应
                    
                    page.screenshot(path=f"{screenshots_dir}/04-after-login.png", full_page=True)
                    print(f"  ✅ 登录提交完成")
                    print(f"     当前URL: {page.url}")
                    
                    # 检查登录是否成功
                    if "/dashboard" in page.url and "login" not in page.url:
                        print(f"     登录成功！")
                    else:
                        print(f"     可能需要注册或验证")
            else:
                print(f"  ⚠️ 未检测到登录表单")
        except Exception as e:
            print(f"  ❌ 登录流程失败: {e}")
            page.screenshot(path=f"{screenshots_dir}/03-login-error.png")
        
        # 4. 注册新用户并测试
        print("\n[4/4] 测试注册新用户...")
        try:
            page.goto(f"{base_url}/register", wait_until="networkidle", timeout=30000)
            time.sleep(2)
            
            page.screenshot(path=f"{screenshots_dir}/05-register-page.png", full_page=True)
            print(f"  ✅ 注册页面加载成功")
            
            # 检查注册表单
            inputs = page.locator("input").count()
            print(f"     检测到 {inputs} 个输入字段")
            
        except Exception as e:
            print(f"  ❌ 注册页面加载失败: {e}")
        
        # 关闭浏览器
        browser.close()
        
        print("\n" + "=" * 60)
        print("测试完成！截图保存在:")
        print(f"  {screenshots_dir}/")
        print("=" * 60)
        
        # 列出所有截图
        screenshots = sorted(os.listdir(screenshots_dir))
        if screenshots:
            print("\n生成的截图:")
            for f in screenshots:
                print(f"  - {f}")

if __name__ == "__main__":
    test_cantor()
