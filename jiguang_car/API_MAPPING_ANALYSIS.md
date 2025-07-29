# MaixCAM到K230 API映射分析文档

## 概述
本文档详细分析了MaixCAM和K230平台的API差异，制定了完整的API映射表和适配策略。

## 1. 摄像头模块映射

### MaixCAM API
```python
from maix import camera, image
cam = camera.Camera(CAM_WIDTH, CAM_HEIGHT, image.Format.FMT_BGR888, fps=DISPLAY_FPS)
img = cam.read()
```

### K230 API
```python
from media.sensor import *
from media.media import *
import image

# 初始化
sensor.reset()
sensor.set_pixformat(sensor.RGB565)  # 或其他格式
sensor.set_framesize(sensor.QQVGA)   # 160x120
sensor.skip_frames(time=2000)

# 获取图像
img = sensor.snapshot()
```

### 映射关系
- `camera.Camera()` → `sensor.reset()` + `sensor.set_pixformat()` + `sensor.set_framesize()`
- `cam.read()` → `sensor.snapshot()`
- 图像格式：`image.Format.FMT_BGR888` → `sensor.RGB565`

## 2. 显示模块映射

### MaixCAM API
```python
from maix import display
disp = display.Display()
disp.show(img)
```

### K230 API
```python
from media.display import *
Display.init(Display.ST7701, width=800, height=480)  # 根据屏幕类型
Display.show_image(img)
```

### 映射关系
- `display.Display()` → `Display.init(Display.ST7701)`
- `disp.show()` → `Display.show_image()`

## 3. 图像处理映射

### MaixCAM API
```python
from maix import image
img_cv = image.image2cv(img, ensure_bgr=False, copy=False)
img_show = image.cv2image(img_display, bgr=True, copy=False)
```

### K230 API
```python
import image
# K230直接使用image对象，无需转换
# 使用K230原生图像处理方法：
blobs = img.find_blobs([threshold])  # 替代OpenCV的颜色检测
rects = img.find_rects()             # 替代OpenCV的轮廓检测
img.draw_circle(x, y, r, color=(255,0,255))  # 替代cv2.circle
img.draw_string(x, y, text, color=(255,255,255))  # 替代cv2.putText
```

### 映射关系
- `image.image2cv()` → 直接使用K230 image对象
- `image.cv2image()` → 直接使用K230 image对象
- OpenCV方法 → K230原生image方法

## 4. UART通信映射

### MaixCAM API
```python
from maix import uart
serial = uart.UART(device, baudrate)
serial.set_received_callback(callback)
serial.write_str(data)
```

### K230 API
```python
from machine import UART
uart = UART(UART.UART1, 115200, 8, None, 1, timeout=1000, read_buf_len=4096)
uart.write(data.encode())
data = uart.read(128)
```

### 映射关系
- `uart.UART(device, baudrate)` → `UART(UART.UART1, baudrate, bits, parity, stop)`
- `serial.set_received_callback()` → 使用定时器轮询替代回调
- `serial.write_str()` → `uart.write()`

## 5. 时间管理映射

### MaixCAM API
```python
from maix import time
time.sleep_ms(5)
timestamp = time.ticks_ms()
current_time = time.time()
```

### K230 API
```python
import utime
utime.sleep_ms(5)
timestamp = utime.ticks_ms()
current_time = utime.time()
```

### 映射关系
- `from maix import time` → `import utime`
- 所有time方法直接对应utime方法

## 6. 应用程序控制映射

### MaixCAM API
```python
from maix import app
while not app.need_exit():
    # 主循环
```

### K230 API
```python
# K230使用标准Python循环控制
import os
while True:
    try:
        # 主循环
        os.exitpoint()  # 检查退出点
    except KeyboardInterrupt:
        break
```

## 7. 检测算法映射

### A4纸检测
**MaixCAM (OpenCV)**:
```python
import cv2
hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
white_mask = cv2.inRange(hsv, LOWER_WHITE_HSV, UPPER_WHITE_HSV)
contours, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
```

**K230 (原生)**:
```python
# 使用矩形检测
rectangles = img.find_rects(threshold=10000)
# 或使用颜色阈值+blob检测
white_threshold = (220, 255)  # 灰度阈值
blobs = img.find_blobs([white_threshold])
```

### 激光检测
**MaixCAM (OpenCV)**:
```python
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
mask_purple = cv2.inRange(hsv, LOWER_PURPLE, UPPER_PURPLE)
contours_purple, _ = cv2.findContours(mask_purple, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
```

**K230 (原生)**:
```python
# 使用LAB颜色空间进行紫色检测
purple_threshold = (30, 100, 15, 127, 15, 127)  # LAB阈值
blobs = img.find_blobs([purple_threshold], pixels_threshold=LASER_MIN_AREA)
```

## 8. 关键差异和注意事项

### 图像格式差异
- MaixCAM支持BGR888格式，K230主要使用RGB565
- K230支持更多格式：ARGB8888, RGB888, RGBP888, YUV420等

### 内存管理差异
- K230有多种内存分配方式：ALLOC_MMZ, ALLOC_VB, ALLOC_HEAP等
- 需要考虑内存池和物理地址管理

### 性能考虑
- K230原生图像处理方法通常比OpenCV更高效
- 需要调整检测参数以适应K230的处理能力

### 硬件差异
- UART设备路径不同：MaixCAM使用"/dev/ttyS0"，K230使用UART.UART1
- 显示屏类型不同，需要选择合适的Display类型

## 9. 适配策略

### 分层适配策略
1. **底层适配**：创建适配层封装K230 API
2. **中间层优化**：重构图像处理算法
3. **上层兼容**：保持原有接口尽可能不变

### 风险评估
- **高风险**：图像处理算法重构，可能影响检测精度
- **中风险**：UART通信机制变化，需要重新实现回调
- **低风险**：时间管理和基础API替换

### 测试验证策略
- 分模块测试各个适配层
- 对比检测精度和性能
- 验证UART通信稳定性

## 10. 实施计划

1. **第一阶段**：基础API适配（时间、配置管理）
2. **第二阶段**：UART通信库重构
3. **第三阶段**：摄像头和显示适配层
4. **第四阶段**：图像处理算法重构
5. **第五阶段**：整合测试和优化

此映射分析为后续的适配工作提供了详细的技术指导。
