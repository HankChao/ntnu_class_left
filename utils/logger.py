"""
日誌管理模組
- 寫入 log 到檔案
- 自動保留最新 100 行
"""
import os
from datetime import datetime
from pathlib import Path

class Logger:
    def __init__(self, log_file="app.log", max_lines=100):
        """初始化 Logger
        
        Args:
            log_file: log 檔案名稱
            max_lines: 保留的最大行數
        """
        self.log_file = log_file
        self.max_lines = max_lines
        
        # 確保 log 檔案目錄存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
    def log(self, message):
        """寫入 log 並保持最新 max_lines 行
        
        Args:
            message: 要記錄的訊息
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        # 寫入 log
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        # 檢查並清理舊 log（只保留最新 max_lines 行）
        self._trim_log()
    
    def _trim_log(self):
        """只保留最新的 max_lines 行"""
        try:
            if not os.path.exists(self.log_file):
                return
            
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 如果超過行數限制，只保留最新的行
            if len(lines) > self.max_lines:
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    f.writelines(lines[-self.max_lines:])
        except Exception as e:
            # 如果清理失敗，不影響程式運行
            pass

# 創建全域 logger 實例
main_logger = Logger("log/main.log", max_lines=50)
playwright_logger = Logger("log/playwright.log", max_lines=1500)
bot_logger = Logger("log/bot.log", max_lines=50)
