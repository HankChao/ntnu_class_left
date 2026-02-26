from PIL import Image, ImageFilter
import colorsys
import cv2
import numpy as np
import ddddocr


def keep_vivid_else_white(img, s_keep=0.45, v_keep=0.35, v_max=0.98):
    """保留鮮豔顏色,其他變白色"""
    img = img.convert("RGB")
    w, h = img.size
    px = img.load()

    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            rr, gg, bb = r/255.0, g/255.0, b/255.0
            _, s, v = colorsys.rgb_to_hsv(rr, gg, bb)

            keep = (s >= s_keep) and (v >= v_keep) and (v <= v_max)
            if not keep:
                px[x, y] = (255, 255, 255)

    return img


def preprocess_image(input_path, output_path="./ocr_img/ocr_ready.png"):
    """圖像預處理:二值化、形態學操作、放大"""
    out = Image.open(input_path)
    img_cv = np.array(out)
    img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 254, 255, cv2.THRESH_BINARY)
    binary_inv = cv2.bitwise_not(binary)

    kernel = np.ones((2, 2), np.uint8)
    closed_inv = cv2.morphologyEx(binary_inv, cv2.MORPH_CLOSE, kernel)
    final_binary = cv2.bitwise_not(closed_inv)

    h, w = final_binary.shape
    resized = cv2.resize(final_binary, (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)

    cv2.imwrite(output_path, resized)
    return output_path


def ocr_and_calculate(image_path):
    """OCR識別並計算算式結果"""
    ocr = ddddocr.DdddOcr(show_ad=False)

    with open(image_path, "rb") as f:
        image = f.read()

    result = ocr.classification(image)

    try:
        #有就重來
        if '/' in result:   return None
            
        if any(ch.isdigit() for ch in result):
            a = result[0]
            b = result[2]
            sym = result[1]

            if sym == 'x' or sym == 'X':
                sym = '*'

            # 手動除錯一些常見的誤識別
            if a == '>': a = '7'
            if b == '>': b = '7'

            result = str(eval(f"{a}{sym}{b}"))
        
        if any(ch.isupper() for ch in result):
            return None  # 不會有大寫
        return result

    except Exception as e:
        print(e)
        return None

def process_captcha(image_path, s_keep=0.45, v_keep=0.35, v_max=0.98):
    """完整的驗證碼處理流程"""
    # 1. 讀取圖片
    img = Image.open(image_path)
    
    # 2. 保留鮮豔顏色
    bright_img = keep_vivid_else_white(img, s_keep=s_keep, v_keep=v_keep, v_max=v_max)
    bright_img.save("./ocr_img/bright.png")
    
    # 3. 預處理圖像
    ocr_ready_path = preprocess_image("./ocr_img/bright.png")
    
    # 4. OCR識別並計算
    result = ocr_and_calculate(ocr_ready_path)
    
    return result