import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

#114-2 有5030筆，推薦到5500即可
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'zh-TW,zh;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://courseap2.itc.ntnu.edu.tw/acadmOpenCourse/CofopdlCtrl?language=chinese',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Dest': 'empty',
    'Connection': 'keep-alive'
}

def fetch_course_data(serial_number,config):
    s = requests.Session()
    s.get('https://courseap2.itc.ntnu.edu.tw/acadmOpenCourse/index.jsp', headers=headers)
    
    timestamp = int(time.time() * 1000)
    
    res = s.get(
        f"https://courseap2.itc.ntnu.edu.tw/acadmOpenCourse/CofopdlCtrl?_dc={timestamp}&acadmYear={config['year']}&acadmTerm={config['term']}&chn=&engTeach=N&clang=N&moocs=N&remoteCourse=N&digital=N&adsl=N&deptCode=&zuDept=&classCode=&kind=&generalCore=&teacher=&serial_number={serial_number}&course_code=&language=chinese&action=showGrid&start=0&limit=99999&page=1",
        headers=headers
    )
    
    if res.status_code == 200:
        try:
            data = res.json()
            if data['Count'] > 0:
                return serial_number, data['List'][0]
        except json.JSONDecodeError:
            pass
    
    return serial_number, None

# 一次性收集所有資料 (多線程加速)
def run_fetch_all_courses(config):
    all_courses = {}
    
    # 使用 20 個線程並行請求
    with ThreadPoolExecutor(max_workers=10) as executor:
        # 提交所有任務
        futures = {
            executor.submit(fetch_course_data, f"{serial:04d}", config): serial for serial in range(1, 5500)
        }
        
        # 收集結果
        for future in as_completed(futures):
            serial_number, course = future.result()
            
            if course:
                all_courses[serial_number] = {
                    'chn_name': course['chn_name'],
                    'teacher': course['teacher'],
                    'course_code': course['course_code']
                }
                print(f"Serial {serial_number}: 已找到課程 - {course['chn_name']}")
            else:
                print(f"Serial {serial_number}: 無資料")

    # 最後一次寫入檔案 (按 key 排序)
    with open('./class_id/class_id.json', 'w', encoding='utf-8') as f:
        json.dump(all_courses, f, indent=2, ensure_ascii=False, sort_keys=True)

    print(f"\n完成!總共收集 {len(all_courses)} 筆課程資料")

if __name__ == "__main__":

    with open("./class_id/class_year_config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    run_fetch_all_courses(config)