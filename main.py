
import os
import time
from playwright.sync_api import sync_playwright, Cookie, TimeoutError as PlaywrightTimeoutError

def add_server_time(server_url="https://dash.icehost.pl/server/2920225f"):
    """
    优先使用 REMEMBER_WEB_COOKIE 进行会话登录，如果不存在则回退到邮箱密码登录。
    此函数设计为每次GitHub Actions运行时执行一次。
    """
    # 从环境变量获取登录凭据
    remember_web_cookie = os.environ.get('REMEMBER_WEB_COOKIE')

    with sync_playwright() as p:
        # 在 GitHub Actions 中，使用 headless 无头模式运行
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # 增加默认超时时间到90秒，以应对网络波动和慢加载
        page.set_default_timeout(90000)

        try:
            # --- 方案一：优先尝试使用 Cookie 会话登录 ---
            if remember_web_cookie:
                print("检测到 REMEMBER_WEB_COOKIE，尝试使用 Cookie 登录...")
                session_cookie = {
                    'name': 'icehostpl_session',
                    'value': remember_web_cookie,
                    'domain': 'dash.icehost.pl',  # 已更新为新的域名
                    'path': '/',
                    'expires': int(time.time()) + 3600 * 24 * 365, # 设置一个较长的过期时间
                    'httpOnly': True,
                    'secure': True,
                    'sameSite': 'Lax'
                }
                page.context.add_cookies([session_cookie])
                print(f"已设置 Cookie。正在访问目标服务器页面: {server_url}")
                
                try:
                    # 使用 'domcontentloaded' 以加快页面加载判断，然后依赖选择器等待确保元素加载
                    page.goto(server_url, wait_until="domcontentloaded", timeout=90000)
                except PlaywrightTimeoutError:
                    print(f"页面加载超时（90秒）。")
                    page.screenshot(path="goto_timeout_error.png")
                
                # 检查是否因 Cookie 无效被重定向到登录页
                if "login" in page.url or "auth" in page.url:
                    print("Cookie 登录失败或会话已过期，将回退到邮箱密码登录。")
                    page.context.clear_cookies()
                    remember_web_cookie = None # 标记 Cookie 登录失败，以便执行下一步
                else:
                    print("Cookie 登录成功，已进入服务器页面。")



            # --- 确保当前位于正确的服务器页面 ---
            if page.url != server_url:
                print(f"当前不在目标服务器页面，正在导航至: {server_url}")
                page.goto(server_url, wait_until="domcontentloaded", timeout=90000)
                if "login" in page.url:
                    print("导航失败，会话可能已失效，需要重新登录。")
                    page.screenshot(path="server_page_nav_fail.png")
                    browser.close()
                    return False

            # --- 核心操作：查找并点击 "시간 추가" 按钮 ---
            add_button_selector = 'button:has-text("DODAJ 6 GODZIN WAŻNOŚCI")' # 已更新为新的按钮文本
            print(f"正在查找并等待 '{add_button_selector}' 按钮...")

            try:
                # 等待按钮变为可见且可点击
                add_button = page.locator(add_button_selector)
                add_button.wait_for(state='visible', timeout=30000)
                add_button.click()
                print("成功点击 'DODAJ 6 GODZIN WAŻNOŚCI' 按钮。")
                time.sleep(5) # 等待5秒，确保操作在服务器端生效
                print("任务完成。")
                browser.close()
                return True
            except PlaywrightTimeoutError:
                print(f"错误: 在30秒内未找到或 'DODAJ 6 GODZIN WAŻNOŚCI' 按钮不可见/不可点击。")
                page.screenshot(path="add_6h_button_not_found.png")
                browser.close()
                return False

        except Exception as e:
            print(f"执行过程中发生未知错误: {e}")
            # 发生任何异常时都截图，以便调试
            page.screenshot(path="general_error.png")
            browser.close()
            return False

if __name__ == "__main__":
    print("开始执行添加服务器时间任务...")
    success = add_server_time()
    if success:
        print("任务执行成功。")
        exit(0)
    else:
        print("任务执行失败。")
        exit(1)
