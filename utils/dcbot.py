import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from course_manager import CourseManager

# 載入環境變數
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')  # 可選：開發測試時填入伺服器 ID
CHANNEL_ID = os.getenv('CHANNEL_ID')  # 通知頻道 ID

# 建立 Bot
class CourseBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        
        # 初始化課程管理器
        self.course_manager = CourseManager("sub.json")
        
        # 記錄課程最後通知時間（避免 10 分鐘內重複通知）
        self.last_notified = {}  # {serial: datetime}
        
        # 記錄頻道錯誤是否已提示（避免重複輸出）
        self.channel_error_shown = False
    
    async def setup_hook(self):
        """註冊 slash commands"""
        if GUILD_ID:
            # 開發模式：指定伺服器，立即同步
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print("✅ Slash commands 已同步（伺服器模式，立即生效）")
        else:
            # 正式模式：全域同步，需等 1 小時
            await self.tree.sync()
            print("✅ Slash commands 已同步（全域模式，需等 1 小時生效）")
        
        # 啟動監控任務
        if CHANNEL_ID:
            self.monitor_courses.start()
            print("✅ 課程監控任務已啟動（每 1 分鐘檢查一次，同課程 10 分鐘內只通知一次）")
    
    @tasks.loop(minutes=1)
    async def monitor_courses(self):
        """每 1 分鐘檢查課程餘額"""
        if not CHANNEL_ID:
            return
        
        channel = self.get_channel(int(CHANNEL_ID))
        if not channel:
            print(f"❌ 找不到頻道 ID: {CHANNEL_ID}")
            return
        
        # 重新載入課程資料（Playwright 每 30 秒更新，資料永遠是最新的）
        self.course_manager.courses = self.course_manager.load_courses()
        
        now = datetime.now()
        
        for serial, info in self.course_manager.courses.items():
            if info is None or '課程名稱' not in info:
                continue  # 尚未更新完整資訊的課程跳過
            
            # 計算剩餘名額
            remaining = self.calculate_remaining_seats(info)
            
            # 檢查是否需要通知
            if not self.should_send_notification(serial, remaining):
                continue
            
            # 從 sub.json 取得課程資訊
            course_name = self.clean_course_name(info.get('課程名稱', '未知課程'))
            teacher = info.get('教師', '未知')
            department = info.get('開課系所', 'N/A')
            course_code = info.get('科目代碼', 'N/A')
            credit = info.get('學分', 'N/A')
            time_place = info.get('上課時間地點', 'N/A')
            update_time = info.get('更新時間(timestamp)', 'N/A')
            
            # 建立通知 Embed
            embed = discord.Embed(
                title="🔔 課程有名額了！",
                description=f"**{course_name}**",
                color=discord.Color.gold()
            )
            
            embed.add_field(name="📌 開課序號", value=f"`{serial}`", inline=True)
            embed.add_field(name="👨‍🏫 教師", value=teacher, inline=True)
            embed.add_field(name="🏫 開課系所", value=department, inline=True)
            embed.add_field(name="✨ 剩餘名額", value=f"**{remaining}**", inline=True)
            embed.add_field(name="📖 科目代碼", value=course_code, inline=True)
            embed.add_field(name="💳 學分", value=credit, inline=True)
            
            if time_place != 'N/A':
                embed.add_field(name="⏰ 上課時間地點", value=time_place, inline=False)
            
            embed.set_footer(text=f"更新時間: {update_time}")
            embed.timestamp = discord.utils.utcnow()
            
            # 發送通知
            try:
                await channel.send(embed=embed)
                print(f"✅ 已發送通知: {serial} - {course_name} (剩餘 {remaining} 名額)")
                self.last_notified[serial] = now
            except discord.HTTPException as e:
                print(f"❌ 發送通知失敗: {serial} - {e}")
    
    @monitor_courses.before_loop
    async def before_monitor(self):
        """等待 Bot 連線完成"""
        await self.wait_until_ready()
        print("🔍 開始監控課程餘額...")
    
    def calculate_remaining_seats(self, info: dict) -> int:
        """計算剩餘名額"""
        try:
            limit = int(info.get('限修人數', 0))
            distributed = int(info.get('已分發人數', 0))
            remaining = limit - distributed
        except (ValueError, TypeError):
            remaining = 0
        
        return remaining
    
    def clean_course_name(self, name: str) -> str:
        """移除課程名稱中的 HTML 標籤並轉換為換行"""
        return name.replace('</br>', '\n').replace('<br>', '\n').strip()
    
    def should_send_notification(self, serial: str, remaining: int) -> bool:
        """判斷是否應發送通知
        
        Args:
            serial: 課程序號
            remaining: 剩餘名額
            
        Returns:
            是否應發送通知
        """
        if remaining <= 0:
            return False
        
        last_notify_time = self.last_notified.get(serial)
        
        # 從未通知過
        if last_notify_time is None:
            return True
        
        # 距離上次通知超過 10 分鐘
        return datetime.now() - last_notify_time >= timedelta(minutes=10)

bot = CourseBot()

# ==================== 事件 ====================

@bot.event
async def on_ready():
    print(f'✅ Bot 已登入為 {bot.user}')
    
    # 檢查是否已加入伺服器
    if not bot.guilds:
        print("⚠️ Bot 尚未加入任何伺服器！")
        print("📌 請前往 Discord Developer Portal 使用 OAuth2 URL Generator 邀請 Bot")
    else:
        print(f'✅ 伺服器: {", ".join([g.name for g in bot.guilds])}')
    
    # 設定狀態
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="課程餘額"
        )
    )

# ==================== Slash Commands ====================

# 📌 /add - 新增課程
@bot.tree.command(name="add", description="新增要追蹤的課程")
@app_commands.describe(serial_number="課程序號（4位數字）")
async def add_course(interaction: discord.Interaction, serial_number: str):
    """新增課程到追蹤清單"""
    
    # 驗證格式
    if not serial_number.isdigit() or len(serial_number) != 4:
        await interaction.response.send_message(
            "❌ 課程序號必須是 4 位數字！",
            ephemeral=True
        )
        return
    
    # 檢查是否已存在
    if serial_number in bot.course_manager.courses:
        await interaction.response.send_message(
            f"⚠️ 課程 `{serial_number}` 已在追蹤清單中",
            ephemeral=True
        )
        return
    
    # 新增課程
    try:
        bot.course_manager.add_course(serial_number)
        
        embed = discord.Embed(
            title="✅ 新增成功",
            description=f"已將課程 `{serial_number}` 加入追蹤清單",
            color=discord.Color.green()
        )
        embed.set_footer(text="Playwright 將在下一輪更新課程資訊")
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(
            f"❌ 新增失敗: {e}",
            ephemeral=True
        )

# 📌 /delete - 刪除課程
@bot.tree.command(name="delete", description="刪除追蹤的課程")
@app_commands.describe(serial_number="課程序號")
async def delete_course(interaction: discord.Interaction, serial_number: str):
    """從追蹤清單中刪除課程"""
    
    # 檢查是否存在
    if serial_number not in bot.course_manager.courses:
        await interaction.response.send_message(
            f"❌ 課程 `{serial_number}` 不在追蹤清單中",
            ephemeral=True
        )
        return
    
    # 刪除課程
    try:
        bot.course_manager.remove_course(serial_number)
        
        embed = discord.Embed(
            title="🗑️ 刪除成功",
            description=f"已將課程 `{serial_number}` 從追蹤清單移除",
            color=discord.Color.orange()
        )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(
            f"❌ 刪除失敗: {e}",
            ephemeral=True
        )

# 📌 /list - 查看所有課程
@bot.tree.command(name="list", description="查看所有追蹤中的課程")
async def list_courses(interaction: discord.Interaction):
    """顯示所有追蹤中的課程"""
    
    # 重新載入最新資料
    bot.course_manager.courses = bot.course_manager.load_courses()
    
    if not bot.course_manager.courses:
        await interaction.response.send_message(
            "📭 目前沒有追蹤任何課程",
            ephemeral=True
        )
        return
    
    # 建立 Embed
    embed = discord.Embed(
        title="📚 課程追蹤清單",
        description=f"共 {len(bot.course_manager.courses)} 門課程",
        color=discord.Color.blue()
    )
    
    # 分類：待更新 vs 已更新
    pending = []
    updated = []
    
    for serial, info in sorted(bot.course_manager.courses.items()):
        if info is None or '課程名稱' not in info:
            pending.append(serial)
        else:
            # 取得關鍵資訊
            remaining_seats = bot.calculate_remaining_seats(info)
            remaining = remaining_seats if remaining_seats != 0 else info.get('未分發人數', '?')
            course_name = bot.clean_course_name(info.get('課程名稱', '未知'))
            teacher = info.get('教師', '未知')
            update_time = info.get('更新時間(timestamp)', 'N/A')
            
            updated.append(
                f"`{serial}` **{course_name}** ({teacher})\n"
                f"    └ 餘額: {remaining} | 更新: {update_time}"
            )
    
    # 添加欄位
    if updated:
        embed.add_field(
            name=f"✅ 已更新 ({len(updated)})",
            value="\n".join(updated),
            inline=False
        )
    
    if pending:
        embed.add_field(
            name=f"⏳ 待更新 ({len(pending)})",
            value=", ".join([f"`{s}`" for s in pending]),
            inline=False
        )
    
    embed.set_footer(text="使用 /info <課程序號> 查看詳細資訊")
    
    await interaction.response.send_message(embed=embed)

# 📌 /info - 查看課程詳細資訊
@bot.tree.command(name="info", description="查看特定課程的詳細資訊")
@app_commands.describe(serial_number="課程序號")
async def course_info(interaction: discord.Interaction, serial_number: str):
    """顯示課程詳細資訊"""
    
    # 重新載入
    bot.course_manager.courses = bot.course_manager.load_courses()
    
    if serial_number not in bot.course_manager.courses:
        await interaction.response.send_message(
            f"❌ 課程 `{serial_number}` 不在追蹤清單中\n使用 `/add {serial_number}` 新增",
            ephemeral=True
        )
        return
    
    info = bot.course_manager.courses[serial_number]
    
    if info is None or '課程名稱' not in info:
        await interaction.response.send_message(
            f"⏳ 課程 `{serial_number}` 尚未更新完整資訊\nPlaywright 將在下一輪更新",
            ephemeral=True
        )
        return
    
    # 建立詳細資訊 Embed
    course_name = bot.clean_course_name(info.get('課程名稱', '未知課程'))
    embed = discord.Embed(
        title=f"📖 {course_name}",
        description=f"開課序號: `{serial_number}`",
        color=discord.Color.blue()
    )
    
    # 基本資訊
    embed.add_field(
        name="📚 基本資訊",
        value=(
            f"**教師**: {info.get('教師', 'N/A')}\n"
            f"**開課系所**: {info.get('開課系所', 'N/A')}\n"
            f"**科目代碼**: {info.get('科目代碼', 'N/A')}\n"
            f"**學分**: {info.get('學分', 'N/A')}\n"
            f"**必修/選修**: {info.get('必修/選修', 'N/A')}\n"
            f"**全英語授課**: {info.get('全英語授課', 'N/A')}"
        ),
        inline=False
    )
    
    # 上課時間地點
    time_place = info.get('上課時間地點', 'N/A')
    if time_place and time_place != 'N/A':
        embed.add_field(
            name="⏰ 上課時間地點",
            value=time_place,
            inline=False
        )
    
    # 名額資訊
    embed.add_field(
        name="👥 名額資訊",
        value=(
            f"**限修人數**: {info.get('限修人數', 'N/A')}\n"
            f"**已分發**: {info.get('已分發人數', 'N/A')}\n"
            f"**未分發**: {info.get('未分發人數', 'N/A')}\n"
            f"**保留新生**: {info.get('保留新生人數', 'N/A')}"
        ),
        inline=False
    )
    
    # 限修條件
    if info.get('限修條件'):
        embed.add_field(
            name="⚠️ 限修條件",
            value=info.get('限修條件', '無'),
            inline=False
        )
    
    # 備註
    if info.get('備註'):
        embed.add_field(
            name="📝 備註",
            value=info.get('備註', '無'),
            inline=False
        )
    
    # 更新時間
    embed.set_footer(text=f"更新時間: {info.get('更新時間(timestamp)', 'N/A')}")
    
    await interaction.response.send_message(embed=embed)

# 📌 /pending - 查看待更新課程
@bot.tree.command(name="pending", description="查看尚未更新資訊的課程")
async def pending_courses(interaction: discord.Interaction):
    """顯示待更新的課程"""
    
    pending = bot.course_manager.get_pending_courses()
    
    if not pending:
        await interaction.response.send_message(
            "✅ 所有課程資訊都已更新",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title="⏳ 待更新課程",
        description=f"共 {len(pending)} 門課程等待 Playwright 更新",
        color=discord.Color.yellow()
    )
    
    embed.add_field(
        name="課程清單",
        value=", ".join([f"`{s}`" for s in pending]),
        inline=False
    )
    
    embed.set_footer(text="Playwright 將在下一輪自動更新")
    
    await interaction.response.send_message(embed=embed)

# 📌 /notify - 測試通知功能
@bot.tree.command(name="notify", description="手動觸發一次課程監控檢查")
async def test_notify(interaction: discord.Interaction):
    """手動執行一次監控檢查"""
    await interaction.response.defer(ephemeral=True)
    
    # 執行一次監控檢查
    await bot.monitor_courses()
    
    await interaction.followup.send("✅ 已執行一次課程監控檢查", ephemeral=True)

# ==================== 啟動 Bot ====================

if __name__ == "__main__":
    bot.run(TOKEN)