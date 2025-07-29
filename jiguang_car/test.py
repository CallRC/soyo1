from maix import camera, display ,image

cam = camera.Camera(640, 480)
disp = display.Display()

while 1:
    img = cam.read()
    img.draw_rect(203, 238, 8, 7, color=image.Color.from_rgb(255, 0, 0))
    disp.show(img)
