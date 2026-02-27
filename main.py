"""
NTNU 課程名額監控系統 - 主程式
同時啟動 Playwright 爬蟲和 Discord Bot
"""
import subprocess
import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))
from logger import main_logger as logger

# 初始化必要的目錄和文件
def init_directories():
    """建立必要的目錄和文件"""
    # 建立 log 目錄
    if not os.path.exists("./log"):
        os.makedirs("./log", exist_ok=True)
        logger.log("✅ 已建立 log 目錄")
    
    # 建立 ocr_img 目錄
    if not os.path.exists("./ocr_img"):
        os.makedirs("./ocr_img", exist_ok=True)
        logger.log("✅ 已建立 ocr_img 目錄")
    
    # 建立 sub.json 檔案
    if not os.path.exists("./sub.json"):
        with open("./sub.json", "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        logger.log("✅ 已建立 sub.json 檔案")

# 執行初始化
init_directories()

# 啟動兩個 Python 程式
processes = []

try:
    # print("🚀 正在啟動服務...")
    logger.log("🚀 正在啟動服務...")
    
    # 啟動 Playwright 爬蟲
    p1 = subprocess.Popen([sys.executable, "utils/playright_setup.py"])
    processes.append(("Playwright", p1))
    # print(f"✅ Playwright 已啟動 (PID: {p1.pid})")
    logger.log(f"✅ Playwright 已啟動 (PID: {p1.pid})")
    
    # 啟動 Discord Bot
    p2 = subprocess.Popen([sys.executable, "utils/dcbot.py"])
    processes.append(("Discord Bot", p2))
    # print(f"✅ Discord Bot 已啟動 (PID: {p2.pid})")
    logger.log(f"✅ Discord Bot 已啟動 (PID: {p2.pid})")
    
    # print("\n💡 按 Ctrl+C 停止所有服務\n")
    logger.log("💡 按 Ctrl+C 停止所有服務")
    
    # 等待任一程式結束
    for name, proc in processes:
        proc.wait()
        # print(f"⚠️  {name} 已退出")
        logger.log(f"⚠️  {name} 已退出")
        
except KeyboardInterrupt:
    # print("\n\n🛑 收到停止信號 (Ctrl+C)")
    logger.log("🛑 收到停止信號 (Ctrl+C)")
except Exception as e:
    # print(f"\n\n❌ 發生錯誤: {e}")
    logger.log(f"❌ 發生錯誤: {e}")
finally:
    # 無論如何都確保殺掉所有子進程
    # print("🔄 正在清理子進程...")
    logger.log("🔄 正在清理子進程...")
    for name, proc in processes:
        if proc.poll() is None:  # 如果進程還在運行
            # print(f"⏳ 正在停止 {name}...")
            logger.log(f"⏳ 正在停止 {name}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)  # 給 5 秒時間優雅退出
                # print(f"✅ {name} 已停止")
                logger.log(f"✅ {name} 已停止")
            except subprocess.TimeoutExpired:
                # print(f"⚠️  {name} 無法正常停止，強制終止...")
                logger.log(f"⚠️  {name} 無法正常停止，強制終止...")
                proc.kill()
                proc.wait()  # 確保完全終止
                # print(f"✅ {name} 已強制終止")
                logger.log(f"✅ {name} 已強制終止")
    # print("👋 所有服務已停止")
    logger.log("👋 所有服務已停止")
