from maix import image, display, app, time, camera
import cv2
import numpy as np
import gc
from micu_uart_lib import (
    SimpleUART, micu_printf, bind_variable,
    VariableContainer, clear_variable_bindings
)

# --------------------------- 紫色激光检测器类 ---------------------------
class PurpleLaserDetector:
    def __init__(self, pixel_radius=3):
        self.pixel_radius = pixel_radius
        self.kernel = MORPH_KERNEL

    def detect(self, img):
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # 1. 紫色HSV范围检测 (可能需要根据实际情况微调阈值)
        # 原始阈值 LOWER_PURPLE = [54, 30, 56], UPPER_PURPLE = [230, 178, 255]
        # 调整为更严格的范围，特别是提高S和V的下限，降低V的上限可能有助于排除纸张反光
        # 示例调整 (请根据实际测试效果再调整):
        # LOWER_PURPLE = np.array([120, 60, 100]) # 提高S和V下限
        # UPPER_PURPLE = np.array([160, 255, 255]) # 保持或微调
        mask_purple = cv2.inRange(hsv, LOWER_PURPLE, UPPER_PURPLE)

        # 2. 形态学操作，去除噪点并连接可能的激光点区域
        mask_purple = cv2.morphologyEx(mask_purple, cv2.MORPH_OPEN, self.kernel)  # 先开运算去噪
        mask_purple = cv2.morphologyEx(mask_purple, cv2.MORPH_CLOSE, self.kernel) # 再闭运算连接

        # 3. 查找轮廓
        contours_purple, _ = cv2.findContours(mask_purple, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best_laser_point = None
        best_score = -1 # 用于选择最佳点的分数 (例如亮度或面积)

        # 4. 筛选候选激光点
        for cnt in contours_purple:
            area = cv2.contourArea(cnt)

            # a. 面积筛选：排除过小或过大的区域
            if not (LASER_MIN_AREA <= area <= LASER_MAX_AREA):
                continue

            # b. 圆形度筛选 (可选但推荐)
            perimeter = cv2.arcLength(cnt, True)
            if perimeter == 0: continue # 避免除以零
            circularity = 4 * np.pi * area / (perimeter * perimeter)
            if circularity < LASER_MIN_CIRCULARITY: # 例如 0.4 或 0.5
                 continue

            # c. 计算轮廓中心作为激光点坐标
            rect = cv2.minAreaRect(cnt)
            cx, cy = map(int, rect[0])

            # d. 亮度筛选 (在原始图像或V通道上检查中心点亮度)
            #    这里检查V通道亮度，确保是足够亮的紫色点
            v_value_at_center = hsv[cy, cx, 2] # 获取中心点的V值
            if v_value_at_center < LASER_MIN_BRIGHTNESS_V: # 例如 150 或更高
                continue

            # e. 计算评分 (例如使用中心点V值或面积)
            score = v_value_at_center # 或者 score = area
            # f. 选择最佳点 (亮度最高或面积最大)
            if score > best_score:
                best_score = score
                best_laser_point = (cx, cy)

        # 5. 如果找到最佳激光点，则绘制并返回
        if best_laser_point is not None:
            cx, cy = best_laser_point
            # 绘制激光点标记（紫色，3像素大小）
            cv2.circle(img, (cx, cy), self.pixel_radius, (255, 0, 255), -1)
            cv2.putText(img, "Purple", (cx - 20, cy - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 0, 255), 1)
            return img, [best_laser_point] # 返回包含单个点的列表

        # 6. 如果没有找到符合条件的点
        return img, [] # 返回空列表


# --------------------------- 紫色激光检测参数 ---------------------------
PIXEL_RADIUS = 3
# 紫色HSV范围（可根据实际激光调整，可能需要更窄的范围）
LOWER_PURPLE = np.array([54, 30, 56])    # 下限（H:130, S:80, V:80）
UPPER_PURPLE = np.array([230, 178, 255])  # 上限（H:160, S:255, V:255）
MORPH_KERNEL = np.ones((3, 3), np.uint8)  # 形态学处理核

# 新增激光点筛选参数
LASER_MIN_AREA = 5      # 激光点最小面积 (根据像素大小调整)
LASER_MAX_AREA = 200    # 激光点最大面积 (防止检测到大区域或残影)
LASER_MIN_CIRCULARITY = 0.3 # 最小圆形度 (0到1，1为完美圆)
LASER_MIN_BRIGHTNESS_V = 150 # HSV中V通道的最小亮度值 (0-255，越高越严格)


# --------------------------- A4纸检测参数 (基于HSV) ---------------------------
# 白色HSV范围 (H: 0-250, S: 0-20, V: 0-250)
LOWER_WHITE_HSV = np.array([0, 0, 0])      # 白色HSV下限
UPPER_WHITE_HSV = np.array([250, 20, 250]) # 白色HSV上限
A4_MIN_AREA = 50        # A4纸最小面积（根据实际调整）
A4_MAX_AREA = 100000       # A4纸最大面积（根据实际调整）
A4_ASPECT_RATIO = 1.414    # A4纸标准长宽比(297mm/210mm)
ASPECT_TOLERANCE = 0.2     # 长宽比容差(±20%)

# --------------------------- 公共参数配置 ---------------------------
CAM_WIDTH, CAM_HEIGHT = 160, 120
DISPLAY_FPS = 60

# --------------------------- 模式切换参数 ---------------------------
MODE_A4 = 0                # A4纸检测模式
MODE_LASER = 1             # 激光检测模式
current_mode = MODE_A4     # 初始模式
SWITCH_INTERVAL = 1        # 切换间隔（帧数）

# --------------------------- 形状检测参数 ---------------------------
DO_DILATION = True
DILATION_KERNEL_SIZE = 3
DILATION_ITERATIONS = 1
TRIANGLE_SCALE = 0.6
TRIANGLE_POS_X = 0.5
TRIANGLE_POS_Y = 0.5
POINTS_PER_EDGE = 3        # 每条边的点数量
# 显示参数
FONT_SCALE = 0.4
FONT_THICKNESS = 1

# --------------------------- 主程序 ---------------------------
if __name__ == "__main__":
    gc.disable()
    print("A4纸检测与紫色激光检测程序启动...")
    print(f"每条边点数量: {POINTS_PER_EDGE}，点大小: 3像素")
    disp = display.Display()
    cam = camera.Camera(CAM_WIDTH, CAM_HEIGHT, image.Format.FMT_BGR888, fps=DISPLAY_FPS)
    detector = PurpleLaserDetector(pixel_radius=PIXEL_RADIUS)
    frame_count = 0
    last_time = time.time()
    generated_points = []  # 存储生成的点坐标
    # 初始化串口
    uart = SimpleUART()
    if uart.init("/dev/ttyS0", 115200, set_as_global=True):
        print("串口初始化成功")
    else:
        print("串口初始化失败")
        exit()
    uart.set_frame("$$", "##", True)  # 设置帧头尾为 $$...##
    while not app.need_exit():
        frame_count += 1
        # 每SWITCH_INTERVAL帧切换一次模式
        if frame_count % SWITCH_INTERVAL == 0:
            current_mode = MODE_LASER if current_mode == MODE_A4 else MODE_A4
        # 读取原始图像
        img = cam.read()
        if img is None:
            continue
        img_cv = image.image2cv(img, ensure_bgr=False, copy=False)
        img_display = img_cv.copy()
        # 初始化变量
        a4_count = 0
        laser_points = []
        # --------------------------- 模式1：A4纸检测与点生成 ---------------------------
        if current_mode == MODE_A4:
            # 1. 转换为HSV颜色空间并提取白色区域
            hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
            white_mask = cv2.inRange(hsv, LOWER_WHITE_HSV, UPPER_WHITE_HSV)

            # 2. 形态学操作，减少噪点
            if DO_DILATION:
                kernel = np.ones((DILATION_KERNEL_SIZE, DILATION_KERNEL_SIZE), np.uint8)
                white_mask = cv2.dilate(white_mask, kernel, iterations=DILATION_ITERATIONS)
                white_mask = cv2.erode(white_mask, kernel, iterations=DILATION_ITERATIONS)

            # 3. 查找轮廓
            contours, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # 4. 筛选A4纸候选区域
            a4_candidates = []
            for contour in contours:
                area = cv2.contourArea(contour)
                # 过滤面积不在范围内的轮廓
                if not (A4_MIN_AREA <= area <= A4_MAX_AREA):
                    continue
                # 多边形逼近（检测矩形）
                perimeter = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.03 * perimeter, True)
                # 检测四边形
                if len(approx) == 4:
                    # 计算最小外接矩形
                    rect = cv2.minAreaRect(approx)
                    width, height = rect[1]
                    # 计算长宽比（考虑旋转）
                    aspect_ratio = max(width, height) / min(width, height)
                    # 检查是否接近A4纸的长宽比
                    if abs(aspect_ratio - A4_ASPECT_RATIO) <= ASPECT_TOLERANCE:
                        a4_candidates.append(approx)

            # 5. 处理找到的A4纸（选择最大的一个）
            if a4_candidates:
                # 按面积排序，选择最大的A4纸候选区域
                a4_candidates.sort(key=lambda c: cv2.contourArea(c), reverse=True)
                a4_contour = a4_candidates[0]
                a4_count = 1
                # 提取四个顶点
                pts = a4_contour.reshape(4, 2).astype(np.float32)
                # 顶点排序（确保顺序：左上、右上、右下、左下）
                s = pts.sum(axis=1)
                tl = pts[np.argmin(s)]  # 左上
                br = pts[np.argmax(s)]  # 右下
                diff = np.diff(pts, axis=1)
                tr = pts[np.argmin(diff)]  # 右上
                bl = pts[np.argmax(diff)]  # 左下
                src_pts = np.array([tl, tr, br, bl], dtype=np.float32)
                # 绘制A4纸轮廓和中心
                cv2.drawContours(img_display, [a4_contour], -1, (0, 255, 0), 1)
                center = (int((tl[0]+br[0])/2), int((tl[1]+br[1])/2))
                cv2.circle(img_display, center, 2, (0, 0, 255), -1)
                cv2.putText(img_display, "A4 Paper", (int(tl[0]), int(tl[1]-10)),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                # 计算目标尺寸（保持A4比例）
                width = int(np.linalg.norm(tl - tr))
                height = int(width / A4_ASPECT_RATIO)
                dst_pts = np.array([
                    [0, 0], [width - 1, 0],
                    [width - 1, height - 1], [0, height - 1]
                ], dtype=np.float32)
                # 计算透视变换矩阵
                M = cv2.getPerspectiveTransform(src_pts, dst_pts)
                ret, M_inv = cv2.invert(M)
                if not ret:
                    continue
                # 生成三角形
                tri_center_x = int(width * TRIANGLE_POS_X)
                tri_center_y = int(height * TRIANGLE_POS_Y)
                tri_size = int(min(width, height) * TRIANGLE_SCALE)
                tri_h = int(tri_size * 0.866)  # 等边三角形的高
                tri_pts = np.array([
                    [tri_center_x, tri_center_y - tri_h // 2],
                    [tri_center_x - tri_size // 2, tri_center_y + tri_h // 2],
                    [tri_center_x + tri_size // 2, tri_center_y + tri_h // 2]
                ], dtype=np.float32)
                # 生成三角形边上的点
                generated_points = []
                for i in range(3):
                    p1, p2 = tri_pts[i], tri_pts[(i+1) % 3]
                    for j in range(POINTS_PER_EDGE + 1):
                        t = j / POINTS_PER_EDGE
                        x = p1[0] + t * (p2[0] - p1[0])
                        y = p1[1] + t * (p2[1] - p1[1])
                        generated_points.append((x, y))
                # 将点映射到原图坐标并显示
                if generated_points:
                    points_array = np.array([generated_points], dtype=np.float32)
                    mapped_points = cv2.perspectiveTransform(points_array, M_inv)[0]
                    # 格式化输出点坐标（串口发送）
                    point_count = len(mapped_points)
                    point_str = ",".join([f"{int(x)},{int(y)}" for x, y in mapped_points])
                    micu_printf(f"M,{point_count},{point_str}")
                    # 绘制点（蓝色，2像素）
                    for x, y in mapped_points:
                        x, y = int(x), int(y)
                        cv2.circle(img_display, (x, y), 2, (255, 0, 0), -1)

        # --------------------------- 模式2：激光检测 ---------------------------
        else:
            # 激光检测（紫色）
            laser_img, laser_points = detector.detect(img_cv.copy())
            # 叠加激光标记到显示图像 (这部分逻辑可以简化，因为我们只返回一个点)
            # 原来的叠加方式可能不太适用，因为我们直接在img上绘制了
            # 如果需要更精确的叠加，可以在detect方法中不直接修改img，而是返回坐标和掩码
            # 这里保留原逻辑，但只处理第一个(也是唯一一个)检测到的点
            # if laser_points:
            #     laser_mask = cv2.inRange(laser_img, (250, 0, 250), (255, 0, 255))
            #     img_display[laser_mask > 0] = laser_img[laser_mask > 0]
            # 实际上，detect方法已经修改了img_cv.copy()的副本，所以直接用laser_img即可
            img_display = laser_img # 因为detect返回的是修改后的图像副本

            # 打印激光的实时坐标（串口发送）
            if laser_points:
                 # 因为只返回一个点，所以只发送第一个
                 x, y = laser_points[0]
                 micu_printf(f"P,{x},{y}")

        # --------------------------- 显示统计信息 ---------------------------
        current_time = time.time()
        fps = int(frame_count / (current_time - last_time)) if (current_time - last_time) > 0 else 0
        stats_text = f"FPS:{fps} | A4 Papers:{a4_count}" if current_mode == MODE_A4 else f"FPS:{fps} | Lasers:{len(laser_points)}"
        cv2.putText(img_display, stats_text, (10, 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # --------------------------- 显示图像 ---------------------------
        img_show = image.cv2image(img_display, bgr=True, copy=False)
        disp.show(img_show)
