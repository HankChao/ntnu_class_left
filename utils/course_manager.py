import json
import os
from filelock import FileLock, Timeout

class CourseManager:
    def __init__(self, json_path="sub.json"):
        self.json_path = json_path
        self.lock_path = json_path + ".lock"
        self.lock = FileLock(self.lock_path, timeout=30)
        self.courses = self.load_courses()
    
    def load_courses(self):
        """載入課程清單（加檔案鎖）"""
        try:
            with self.lock:
                if os.path.exists(self.json_path):
                    with open(self.json_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                return {}
        except Timeout:
            # print("⚠️ 檔案被佔用超過 30 秒，使用空白資料")
            return {}
    
    def save_courses(self, merge_mode=False):
        """儲存課程清單（加檔案鎖）
        
        Args:
            merge_mode: False=完全覆蓋（用於新增/刪除），True=只更新已存在的課程（用於更新資訊）
        """
        try:
            with self.lock:
                if merge_mode:
                    # 合併模式：先讀取檔案，只更新記憶體中有的課程資訊
                    file_courses = {}
                    if os.path.exists(self.json_path):
                        with open(self.json_path, "r", encoding="utf-8") as f:
                            try:
                                file_courses = json.load(f)
                            except:
                                file_courses = {}
                    
                    # 只更新檔案中已存在的課程
                    for serial in self.courses:
                        if serial in file_courses or self.courses[serial] is None:
                            file_courses[serial] = self.courses[serial]
                    
                    sorted_courses = dict(sorted(file_courses.items()))
                else:
                    # 完全覆蓋模式：直接使用記憶體中的資料
                    sorted_courses = dict(sorted(self.courses.items()))
                
                # 寫入檔案
                with open(self.json_path, "w", encoding="utf-8") as f:
                    json.dump(sorted_courses, f, indent=4, ensure_ascii=False)
                # print(f"✅ 已儲存到 {self.json_path}")
                
                # 更新記憶體
                self.courses = sorted_courses
        except Timeout:
            # print(f"❌ 無法儲存，檔案被其他程式鎖定超過 30 秒")
            pass
        except Exception as e:
            # print(f"❌ 儲存失敗: {e}")
            # import traceback
            # traceback.print_exc()
            pass
    
    def add_course(self, serial_number):
        """新增課程（只有 key，沒有 value）"""
        # 先重新載入，確保有最新資料
        self.courses = self.load_courses()
        
        if serial_number not in self.courses:
            self.courses[serial_number] = None
            self.save_courses(merge_mode=False)  # 完全覆蓋模式
            # print(f"✅ 已新增課程: {serial_number}")
        else:
            # print(f"⚠️ 課程已存在: {serial_number}")
            pass
    
    def update_course_info(self, serial_number, course_info):
        """更新課程資訊"""
        if serial_number in self.courses:
            self.courses[serial_number] = course_info
            self.save_courses(merge_mode=True)  # 合併模式，不影響其他課程
            # print(f"✅ 已更新課程資訊: {serial_number}")
        else:
            # print(f"❌ 課程不存在: {serial_number}")
            pass
    
    def get_pending_courses(self):
        """取得需要查詢的課程（value 為 None 的）"""
        return [key for key, value in self.courses.items() if value is None]
    
    def get_all_courses(self):
        """取得所有課程編號"""
        return list(self.courses.keys())
    
    def remove_course(self, serial_number):
        """移除課程"""
        # 先重新載入，確保有最新資料
        self.courses = self.load_courses()
        
        if serial_number in self.courses:
            del self.courses[serial_number]
            self.save_courses(merge_mode=False)  # 完全覆蓋模式
            # print(f"✅ 已移除課程: {serial_number}")
        else:
            # print(f"❌ 課程不存在: {serial_number}")
            pass