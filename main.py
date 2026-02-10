import os
import time
import signal
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime

# --- 配置项 ---
SERVER_URL = "https://dash.icehost.pl/server/2920225f"
LOGIN_URL = "https://dash.icehost.pl/server/2920225f"
COOKIE_NAME = "icehostpl_session"
# 单次任务执行的超时时间（秒），依然保留以防单次运行卡死
TASK_TIMEOUT_SECONDS = 300  # 5分钟

# --- 超时处理机制 ---
class TaskTimeoutError(Exception):
    """自定义任务超时异常"""
    pass

def timeout_handler(signum, frame):
    """超时信号处理函数"""
    raise TaskTimeoutError("任务执行时间超过设定的阈值")

if os.name != 'nt':
    signal.signal(signal.SIGALRM, timeout_handler)

# login_with_playwright 函数保持不变，此处为完整代码
def login_with_playwright(page):
    """处理登录逻辑，优先使用Cookie，失败则使用邮箱密码。"""
    remember_web_cookie = os.environ.get('PTERODACTYL_COOKIE')
    pterodactyl_email = os.environ.get('PTERODACTYL_EMAIL')
    pterodactyl_password = os.environ.get('PTERODACTYL_PASSWORD')

    if remember_web_cookie:
        print("检测到 PTERODACTYL_COOKIE，尝试使用 Cookie 登录...")
        session_cookie = {
            'name': COOKIE_NAME, 'value': remember_web_cookie, 'domain': '.icehost.pl',
            'path': '/', 'expires': int(time.time()) + 3600 * 24 * 365, 'httpOnly': True,
            'secure': True, 'sameSite': 'Lax'
        }
        page.context.add_cookies([session_cookie])
        print(f"已设置 Cookie。正在访问目标服务器页面: {SERVER_URL}")
        page.goto(SERVER_URL, wait_until="domcontentloaded")
        
        if "auth/login" in page.url:
            print("Cookie 登录失败或会话已过期，将回退到邮箱密码登录。")
            page.context.clear_cookies()
        else:
            print("Cookie 登录成功！")
            return True

    if not (pterodactyl_email and pterodactyl_password):
        print("错误: Cookie 无效或未提供，且未提供 PTERODACTYL_EMAIL 和 PTERODACTYL_PASSWORD。无法登录。", flush=True)
        return False


def add_time_task(page):
    """执行一次增加服务器时长的任务。"""
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始执行增加时长任务...")
        
        if page.url != SERVER_URL:
            print(f"当前不在目标页面，正在导航至: {SERVER_URL}")
            page.goto(SERVER_URL, wait_until="domcontentloaded")
        

        #add_button_selector = 'button:has-text("Dodaj 6 godzin ważności")'
        print("步骤1: 查找并点击 'Dodaj 6 godzin ważności' 按钮...")
        page.get_by_text("DODAJ 6 GODZIN WAŻNOŚCI").click()
        #page.locator(add_button_selector).wait_for(state='visible', timeout=30000)
        #page.locator(add_button_selector).click()
        #print("...已点击 'Add 90 minutes'。")

        #watch_ad_selector = 'button:has-text("Watch advertisment")'
        #print("步骤2: 查找并点击 'Watch advertisment' 按钮...")
        #page.locator(watch_ad_selector).wait_for(state='visible', timeout=30000)
        #page.locator(watch_ad_selector).click()
        #print("...已点击 'Watch advertisment'。")

        # 【【【 核心修改点在这里 】】】
        # 不再等待成功提示，而是直接固定等待2分钟。
        print("步骤3: 开始固定等待20s...")
        time.sleep(20)  # 等待 2 分钟 (120 秒)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ 已等待20s，默认任务完成。")
        
        return True

    except PlaywrightTimeoutError as e:
        print(f"❌ 任务执行超时: 未在规定时间内找到元素。请检查选择器或页面是否已更改。", flush=True)
        page.screenshot(path="task_element_timeout_error.png")
        return False
    except Exception as e:
        print(f"❌ 任务执行过程中发生未知错误: {e}", flush=True)
        page.screenshot(path="task_general_error.png")
        return False

def main():
    """
    主函数，执行一次登录和一次任务，然后退出。
    """
    print("启动自动化任务（单次运行, 固定等待模式）...", flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(60000)
        print("浏览器启动成功。", flush=True)

        try:
            # 步骤1: 登录
            if not login_with_playwright(page):
                print("登录失败，程序终止。", flush=True)
                exit(1)

            # 步骤2: 执行增加时长的核心任务 (带超时监控)
            if os.name != 'nt':
                signal.alarm(TASK_TIMEOUT_SECONDS)
            
            print("\n----------------------------------------------------")
            success = add_time_task(page)
            
            if os.name != 'nt':
                signal.alarm(0)

            if success:
                print("本轮任务成功完成。", flush=True)
            else:
                print("本轮任务失败。", flush=True)
                exit(1)

        except TaskTimeoutError as e:
            print(f"🔥🔥🔥 任务强制超时（{TASK_TIMEOUT_SECONDS}秒）！🔥🔥🔥", flush=True)
            print(f"错误信息: {e}", flush=True)
            page.screenshot(path="task_force_timeout_error.png")
            exit(1)
        except Exception as e:
            print(f"主程序发生严重错误: {e}", flush=True)
            page.screenshot(path="main_critical_error.png")
            exit(1)
        finally:
            print("关闭浏览器，程序结束。", flush=True)
            browser.close()

if __name__ == "__main__":
    main()
    print("脚本执行完毕。")
    exit(0)
