from utils.course_manager import CourseManager
import json

def display_menu():
    """顯示主選單"""
    print("\n" + "="*50)
    print("📚 NTNU 課程訂閱管理系統")
    print("="*50)
    print("1. 新增課程 (Add)")
    print("2. 刪除課程 (Delete)")
    print("3. 查看所有課程 (Search/List)")
    print("4. 查看待更新課程")
    print("5. 查看課程詳情")
    print("6. 重新載入 (Reload)")
    print("0. 退出 (Exit)")
    print("="*50)

def add_course(manager):
    """新增課程"""
    print("\n--- 新增課程 ---")
    serial = input("請輸入課程序號 (4位數字): ").strip()
    
    if not serial:
        print("❌ 序號不能為空")
        return
    
    if not serial.isdigit() or len(serial) != 4:
        print("❌ 序號必須是 4 位數字")
        return
    
    manager.add_course(serial)

def delete_course(manager):
    """刪除課程"""
    print("\n--- 刪除課程 ---")
    
    # 先重新載入，確保顯示最新清單
    manager.courses = manager.load_courses()
    
    if not manager.courses:
        print("⚠️ 目前沒有任何課程")
        return
    
    print("\n目前課程清單:")
    for serial in sorted(manager.courses.keys()):
        print(f"  - {serial}")
    
    serial = input("\n請輸入要刪除的課程序號: ").strip()
    
    if not serial:
        print("❌ 序號不能為空")
        return
    
    manager.remove_course(serial)

def list_all_courses(manager):
    """列出所有課程"""
    print("\n--- 所有課程清單 ---")
    
    # 先重新載入，確保顯示最新資料
    manager.courses = manager.load_courses()
    
    if not manager.courses:
        print("⚠️ 目前沒有任何課程")
        return
    
    print(f"\n共有 {len(manager.courses)} 門課程:\n")
    
    for serial, info in sorted(manager.courses.items()):
        print(f"課程序號: {serial}")
        if info is None:
            print("  [待更新]")
        else:
            for key, value in info.items():
                print(f"  {key}: {value}")
        print("-" * 10)

def list_pending_courses(manager):
    """列出待更新課程"""
    print("\n--- 待更新課程 ---")
    
    pending = manager.get_pending_courses()
    
    if not pending:
        print("✅ 所有課程都已更新")
        return
    
    print(f"\n共有 {len(pending)} 門課程待更新:\n")
    for serial in sorted(pending):
        print(f"  📌 {serial}")

def show_course_detail(manager):
    """顯示課程詳情"""
    print("\n--- 課程詳情 ---")
    
    if not manager.courses:
        print("⚠️ 目前沒有任何課程")
        return
    
    serial = input("請輸入課程序號: ").strip()
    
    if serial not in manager.courses:
        print(f"❌ 課程不存在: {serial}")
        return
    
    info = manager.courses[serial]
    
    if info is None:
        print(f"\n📌 課程 {serial} - [待更新]")
        print("   尚未取得課程資訊")
    else:
        print(f"\n✅ 課程 {serial} 詳細資訊:")
        print("-" * 40)
        for key, value in info.items():
            print(f"  {key}: {value}")
        print("-" * 40)

def reload_courses(manager):
    """重新載入課程清單"""
    print("\n🔄 重新載入課程清單...")
    manager.courses = manager.load_courses()
    print(f"✅ 已載入 {len(manager.courses)} 門課程")

def main():
    """主程式"""
    print("\n🚀 啟動課程管理系統...")
    
    # 初始化管理器（使用檔案鎖，避免與 Playwright 衝突）
    manager = CourseManager("sub.json")
    
    print(f"✅ 已載入 {len(manager.courses)} 門課程")
    print("\n💡 提示: 此系統使用檔案鎖機制，可與 Playwright 同時執行")
    
    while True:
        display_menu()
        
        choice = input("\n請選擇功能 (0-6): ").strip()
        
        if choice == "1":
            add_course(manager)
        elif choice == "2":
            delete_course(manager)
        elif choice == "3":
            list_all_courses(manager)
        elif choice == "4":
            list_pending_courses(manager)
        elif choice == "5":
            show_course_detail(manager)
        elif choice == "6":
            reload_courses(manager)
        elif choice == "0":
            print("\n👋 感謝使用，再見！")
            break
        else:
            print("\n❌ 無效的選項，請重新選擇")
        
        input("\n按 Enter 繼續...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 程式被中斷")
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()