import os
os.environ['ORT_LOGGING_LEVEL'] = '3'  # 隱藏 ONNX Runtime 警告訊息

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from captcha_ocr import process_captcha
from course_manager import CourseManager
from datetime import datetime
import time
import signal
import sys as system
from logger import playwright_logger as logger

# 全局變數，用於儲存當前頁面以便在信號處理中使用
current_page = None
is_shutting_down = False
is_logged_in = False  # 追蹤是否已登入（點擊下一頁後）

def signal_handler(signum, frame):
    """處理終止信號（SIGTERM 和 SIGINT）"""
    global is_shutting_down
    if is_shutting_down:
        return  # 避免重複處理
    
    is_shutting_down = True
    signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
    logger.log(f"🛑 收到 {signal_name} 信號，正在安全關閉...")
    
    # 只有在已登入狀態才嘗試登出
    if current_page and is_logged_in:
        try:
            sys_logout(current_page)
        except Exception as e:
            logger.log(f"⚠️ 信號處理中登出失敗: {e}")
    elif not is_logged_in:
        logger.log("ℹ️ 尚未登入，跳過登出程序")
    
    logger.log("👋 程式已安全退出")
    system.exit(0)

# 註冊信號處理器
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# 載入環境變數
load_dotenv()

# 確保 ocr_img 目錄存在
if not os.path.exists("./ocr_img"):
    os.makedirs("./ocr_img", exist_ok=True)

def playwright_main():
    """主程式函數"""
    # 從環境變數讀取設定
    config = {
        "account": os.getenv("ACCOUNT"),
        "password": os.getenv("PASSWORD"),
        "sys": os.getenv("SYS_URL"),
        "sys_id": os.getenv("SYS_ID"),
        "login_retry_interval": int(os.getenv("LOGIN_RETRY_INTERVAL", "30")),
        "search_interval": int(os.getenv("SEARCH_INTERVAL", "20")),
        "website_error_retry_interval": int(os.getenv("WEBSITE_ERROR_RETRY_INTERVAL", "300"))
    }

    manager = CourseManager("sub.json")

    # 使用 Playwright
    try:
        with sync_playwright() as p:
            while not is_shutting_down:
                browser = None
                try:
                    # 每次循環都重新啟動瀏覽器（可選擇 chromium, firefox, webkit）
                    # headless=True 表示背景執行（無視窗）
                    logger.log("🔄 啟動瀏覽器...")
                    browser = p.chromium.launch(headless=True)
                    context = browser.new_context()     
                    page = context.new_page()

                    playwright_run(page, config, context, manager)
                    
                except Exception as e:
                    logger.log(f"❌ 執行過程發生錯誤: {e}")
                    logger.log(f"錯誤類型: {type(e).__name__}")
                finally:
                    # 確保關閉瀏覽器，釋放資源
                    try:
                        if browser:
                            browser.close()
                            logger.log("✅ 已關閉瀏覽器")
                    except Exception as e:
                        logger.log(f"⚠️ 關閉瀏覽器時發生錯誤: {e}")
                
                if not is_shutting_down:
                    logger.log(f"⏳ 等待 {config['website_error_retry_interval']} 秒後重新啟動...")
                    time.sleep(config["website_error_retry_interval"])  # 等待n秒後重新啟動

    except KeyboardInterrupt:
        logger.log("🛑 收到停止信號，程式結束")
    except Exception as e:
        logger.log(f"❌ 主程式錯誤: {e}")

def playwright_run(page, config, context, manager):
    global current_page, is_logged_in
    current_page = page  # 儲存當前頁面供信號處理器使用
    is_logged_in = False  # 重置登入狀態
    
    try:
        logger.log(f"🌐 正在訪問網站: {config['sys']}")
        page.goto(config["sys"], wait_until="networkidle", timeout=60000)  # 等待網絡空閒
        logger.log("✅ 頁面載入完成")
        
        # 檢查頁面是否正確載入
        try:
            page.wait_for_selector("input[name='userid']", timeout=10000)
            logger.log("✅ 登入表單已載入")
        except Exception as e:
            logger.log(f"⚠️ 未找到登入表單，可能頁面載入異常")
            logger.log(f"📄 當前頁面標題: {page.title()}")
            logger.log(f"📍 當前頁面 URL: {page.url}")
            raise  # 重新拋出，觸發重啟

        save_captcha_image(page, config, context)
        login = sys_login(page, config, context)

        while not login:
            try:
                page.wait_for_selector("a.x-btn-button span:has-text('OK')", timeout=5000)  # 等待登入結果
                page.click("a.x-btn-button span:has-text('OK')")
            except Exception:
                logger.log("⚠️ 未知登入問題，可能沒有 OK 按鈕")
                #嘗試重載頁面
                try:
                    logger.log(f"🌐 正在訪問網站: {config['sys']}")
                    page.goto(config["sys"], wait_until="networkidle", timeout=60000)  # 等待網絡空閒
                    logger.log("✅ 頁面載入完成")
                except Exception as e:
                    logger.log(f"⚠️ 頁面載入失敗: {e}")
                    raise  # 重新拋出，觸發重啟
            
            try:
                page.wait_for_selector("input[name='userid']", timeout=10000)
                logger.log("✅ 登入表單已載入")
            except Exception as e:
                logger.log(f"⚠️ 未找到登入表單，可能頁面載入異常")
                logger.log(f"📄 當前頁面標題: {page.title()}")
                logger.log(f"📍 當前頁面 URL: {page.url}")
                raise  # 重新拋出，觸發重啟

            save_captcha_image(page, config, context)
            login = sys_login(page, config, context)
            time.sleep(1)
        
        iframe = to_search_page(page)
        
        if iframe:
            # 成功進入選課頁面，設定已登入標誌
            is_logged_in = True
            logger.log("✅ 已進入選課頁面，登入狀態啟用")
            start_time = time.time()
            while time.time() - start_time < 1100:  # 運行1100秒結束

                manager.courses = manager.load_courses()  # 每次迴圈開始時重新載入課程清單，確保最新狀態     
                all_courses = manager.get_all_courses()
                
                for serial in all_courses:
                    course_info = search_course(iframe, serial)
                    time.sleep(0.5)  # 每次查詢後等待0.5秒，避免過快
                    if course_info:
                        manager.update_course_info(serial, course_info[serial])
                    else:
                        # print(f"⚠️ 無法獲取課程資訊: {serial}")
                        logger.log(f"⚠️ 無法獲取課程資訊: {serial}")
                manager.save_courses()  # 每輪結束後儲存
                time.sleep(config["search_interval"])  # 每n秒查詢一輪
            
        else:
            # print("❌ 無法進入選課頁面")
            logger.log("❌ 無法進入選課頁面")
            raise Exception("無法進入選課頁面")  # 拋出異常觸發重啟

    except KeyboardInterrupt:
        logger.log("⚠️ playwright_run 收到中斷信號")
        raise  # 重新拋出以便 playwright_main 處理
    except Exception as e:
        logger.log(f"❌ 發生錯誤: {e}")
        logger.log(f"錯誤類型: {type(e).__name__}")
        raise  # 重新拋出例外，讓 playwright_main 處理並重啟瀏覽器
    
    finally:
        if not is_shutting_down and is_logged_in:  # 只有不是被信號終止且已登入時才登出
            sys_logout(page)
        elif not is_logged_in:
            logger.log("ℹ️ 未成功登入，跳過登出程序")
        current_page = None  # 清空全局變數
        is_logged_in = False  # 重置登入狀態

def save_captcha_image(page, config, context):
    """儲存驗證碼圖片"""

    captcha_page = context.new_page()
    
    try:
        captcha_url = f"https://cos{config['sys_id']}s.ntnu.edu.tw/AasEnrollStudent/RandImage"
        captcha_page.goto(captcha_url)
        time.sleep(1)  # 等待圖片載入   

        response = captcha_page.request.get(captcha_url)
        with open("./ocr_img/captcha.png", "wb") as f:
            f.write(response.body())
        
        # print("✅ 驗證碼已儲存")
        logger.log("✅ 驗證碼已儲存")
    finally:
        # 關閉分頁
        captcha_page.close()
    return

def sys_login(page, config, context):
    """模擬登入系統"""
    page.fill("input[name='userid']", config["account"])
    page.fill("input[name='password']", config["password"])
    
    captcha = process_captcha("./ocr_img/captcha.png")
    while captcha is None:
        save_captcha_image(page, config, context)
        captcha = process_captcha("./ocr_img/captcha.png")

    page.fill("input[name='validateCode']", captcha)
    
    page.click("a.x-btn-button span:has-text('登入')")

    try:
        time.sleep(2)  # 等待登入結果
        if not page.wait_for_selector("text=下一頁 (開始選課)", timeout=4000).is_visible():
            # print("❌ 驗證碼錯誤，請重新嘗試")
            logger.log("❌ 驗證碼錯誤，請重新嘗試")
            return False
        return True
    except Exception as e:
        # print(f"❌ 登入失敗: {e}")
        logger.log(f"❌ 登入失敗: {e}")
        return False

def sys_logout(page):
    """登出系統，確保安全退出"""
    try:
        if page.is_closed():
            logger.log("⚠️ 頁面已關閉，跳過登出")
            return
        
        time.sleep(1)  # 等待頁面載入
        
        # 嘗試查找並點擊登出按鈕
        logout_button = page.wait_for_selector("a.x-btn-button span:has-text('登出')", timeout=5000)
        if logout_button:
            page.click("a.x-btn-button span:has-text('登出')")
            logger.log("✅ 已點擊登出按鈕")
            time.sleep(1)
    except Exception as e:
        logger.log(f"⚠️ 登出時發生錯誤（可能已登出）: {e}")



def to_search_page(page):
    # 處理登入後的彈窗
    try:
        page.wait_for_selector("a.x-btn-button span:has-text('OK')", timeout=3000)
        page.click("a.x-btn-button span:has-text('OK')")
        # print("已點擊登入後的 OK")
        logger.log("已點擊登入後的 OK")
    except:
        # print("沒有 OK 按鈕,跳過")
        logger.log("沒有 OK 按鈕,跳過")
    
    # 點擊「下一頁 (開始選課)」進入主頁面
    try:
        page.wait_for_selector("text=下一頁 (開始選課)", timeout=10000)
        page.click("text=下一頁 (開始選課)")
        # print("✅ 已點擊 '下一頁 (開始選課)'")
        logger.log("✅ 已點擊 '下一頁 (開始選課)'")
    except Exception as e:
        # print(f"❌ 無法點擊下一頁: {e}")
        logger.log(f"❌ 無法點擊下一頁: {e}")
        return None
    
    # 等待 iframe 出現
    try:
        page.wait_for_selector("iframe[name='stfseldListDo']", timeout=15000)
    except Exception as e:
        # print(f"❌ 無法找到選課頁面的 iframe: {e}")
        logger.log(f"❌ 無法找到選課頁面的 iframe: {e}")
        return None
    
    # 切換到「我的選課」tab 的 iframe
    # print("切換到 iframe...")
    logger.log("切換到 iframe...")
    iframe = page.frame_locator("iframe[name='stfseldListDo']")
    
    # 在 iframe 內點擊「查詢課程」
    try:
        iframe.locator("a#query-btnEl").filter(has_text="查詢課程").click(timeout=10000)
        # print("✅ 已點擊 '查詢課程'")
        logger.log("✅ 已點擊 '查詢課程'")
    except Exception as e:
        # print(f"❌ 無法點擊查詢課程: {e}")
        logger.log(f"❌ 無法點擊查詢課程: {e}")
        try:
            iframe.locator("a#add-btnEl").filter(has_text="加選").click(timeout=10000)
            # print("✅ 已點擊 '加選'")
            logger.log("✅ 已點擊 '加選'")
        except Exception as e:
            # print(f"❌ 無法點擊加選: {e}")
            logger.log(f"❌ 無法點擊加選: {e}")
            return None
    
    time.sleep(1)
    
    # 後續操作也要在 iframe 內
    iframe.locator("input#comboDeptCode-inputEl").click(timeout=5000)
    iframe.locator("text=所有系所").click(timeout=5000)
    # print("✅ 已選擇 '所有系所'")
    logger.log("✅ 已選擇 '所有系所'")

    return iframe

def search_course(iframe, serial_number):
    """搜尋課程"""
    #填開課序號
    iframe.locator("input#serialNo-inputEl").fill(serial_number)
    time.sleep(1)

    #查詢按鈕
    iframe.locator("a.x-btn-button span:has-text('查詢')").click(timeout=5000)
    # print(f"✅ 已搜尋課程: {serial_number}")
    logger.log(f"✅ 已搜尋課程: {serial_number}")

    # 點課程
    iframe.locator("tr[data-boundview='gridview-1085']").click(timeout=10000)
    time.sleep(0.5)

    course_name = iframe.locator("td.x-grid-cell-gridcolumn-1070").inner_text(timeout=5000)#科目名稱
    course_teacher = iframe.locator("td.x-grid-cell-gridcolumn-1071").inner_text(timeout=5000)#教師
    time_place = iframe.locator("td.x-grid-cell-gridcolumn-1072").inner_text(timeout=5000)#上課時間地點
    used_eng = iframe.locator("td.x-grid-cell-gridcolumn-1073").inner_text(timeout=5000)#全英語授課(是/否)
    credit = iframe.locator("td.x-grid-cell-gridcolumn-1074").inner_text(timeout=5000)#學分
    course_code = iframe.locator("td.x-grid-cell-gridcolumn-1075").inner_text(timeout=5000)#科目代碼
    must = iframe.locator("td.x-grid-cell-gridcolumn-1076").inner_text(timeout=5000)#必修/選修
    department = iframe.locator("td.x-grid-cell-gridcolumn-1078").inner_text(timeout=5000)#開課系所


    # 看課程資訊
    iframe.locator("span#button-1087-btnInnerEl").click(timeout=10000)
    time.sleep(0.5)  # 等待視窗彈出
    
    # 獲取課程資訊
    course_info = get_course_info(iframe, course_name, course_teacher, time_place, 
                                   course_code, credit, must, department, used_eng)
    # print(f"📚 課程資訊: {course_info}")
    logger.log(f"📚 課程資訊: {course_info}")

    iframe.locator("img.x-tool-close").click(timeout=5000)
    
    return course_info

def clean_text(text):
    """清理文本中的全角空格和多餘空白"""
    return text.replace('\u3000', '').strip()

def get_course_info(iframe, course_name, course_teacher, time_place, 
                    course_code, credit, must, department, used_eng):
    """獲取課程資訊並返回字典"""
    # 等待窗口出現
    time.sleep(1)  # 增加等待時間，確保視窗載入
    
    # 先等待 iframe 出現再切換
    iframe.locator("iframe.x-window-item").wait_for(state="attached", timeout=10000)
    iframe = iframe.frame_locator("iframe.x-window-item")
    
    # 使用 locator 定位元素並獲取內容，並清理文本
    serial_number = clean_text(iframe.locator("div#displayfield-1011-inputEl").inner_text(timeout=10000))
    stu_limit = clean_text(iframe.locator("div#displayfield-1012-inputEl").inner_text(timeout=10000))
    new_stu_keep = clean_text(iframe.locator("div#displayfield-1013-inputEl").inner_text(timeout=10000))
    alreay_stu = clean_text(iframe.locator("div#displayfield-1014-inputEl").inner_text(timeout=10000))
    still_not_stu = clean_text(iframe.locator("div#displayfield-1015-inputEl").inner_text(timeout=10000))
    code_stu = clean_text(iframe.locator("div#displayfield-1016-inputEl").inner_text(timeout=10000))
    used_code_stu = clean_text(iframe.locator("div#displayfield-1017-inputEl").inner_text(timeout=10000))
    class_limit = clean_text(iframe.locator("div#displayfield-1018-inputEl").inner_text(timeout=10000))
    note = clean_text(iframe.locator("div#displayfield-1019-inputEl").inner_text(timeout=10000))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 組合成字典，以 serial_number 為 key
    course_dict = {
        serial_number: {
            "課程名稱": course_name,
            "科目代碼": course_code,
            "教師": course_teacher,
            "上課時間地點": time_place,
            "學分": credit,
            "必修/選修": must,
            "開課系所": department,
            "全英語授課": used_eng,
            "限修人數": stu_limit,
            "保留新生人數": new_stu_keep,
            "已分發人數": alreay_stu,
            "未分發人數": still_not_stu,
            "授權碼人數": code_stu,
            "授權碼選課人數": used_code_stu,
            "限修條件": class_limit,
            "備註": note,
            "更新時間(timestamp)": timestamp
        }
    }
    
    # print('-'*10)
    logger.log('-'*10)
    # print(f"✅ 已獲取課程資訊: {serial_number}")
    logger.log(f"✅ 已獲取課程資訊: {serial_number}")
    return course_dict

playwright_main()