# 師大選課監控系統
用於監控師大選課剩餘名額

## 環境設置
```bash
pip install -r requirements.txt

playwright install

#在該專案中安裝 ddddocr
git clone https://github.com/sml2h3/ddddocr.git
cd ddddocr
pip install .
```

### .env設置
```
# Discord Bot 設定
DISCORD_TOKEN=DC_BOT_TOKEN

# 開發測試用（可選）：指定伺服器 ID，讓指令立即生效
# 如果不填，則使用全域同步（需等 1 小時）
# 建議填寫
GUILD_ID=伺服器id

# 通知頻道 ID：Bot 會在這個頻道發送課程有名額的通知
CHANNEL_ID=DC_channel_id

# 選課系統帳號密碼
ACCOUNT=帳號
PASSWORD=密碼

# 選課系統，可自行更換
SYS_URL=https://cos2s.ntnu.edu.tw/AasEnrollStudent/LoginCheckCtrl?language=TW
SYS_ID=2

# 系統運行參數
LOGIN_RETRY_INTERVAL=30
SEARCH_INTERVAL=20
website_error_retry_interval=300
```
### 無頭模式
預設使用無頭模式省資源，若要顯示瀏覽器視窗，請修改 `utils/playright_setup.py` 中的 `headless` 參數為 `False`

## 運行
```bash
python3 main.py
```