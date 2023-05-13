import cv2
import numpy as np
import pyvirtualcam


# Define the dimensions of the virtual camera
WIDTH = 640
HEIGHT = 480


with pyvirtualcam.Camera(width=WIDTH, height=HEIGHT, fps=30) as cam:
    print(f'Virtual camera created ({cam.width}x{cam.height} @ {cam.fps}fps)')

    while True:
        # Capture a frame from a source, such as a webcam or an IP camera
        # Here, we'll generate a simple test pattern
        img = np.zeros((HEIGHT, WIDTH, 3), np.uint8)
        cv2.rectangle(img, (50, 50), (WIDTH-50, HEIGHT-50), (0, 255, 0), 3)
        cv2.line(img, (50, 50), (WIDTH-50, HEIGHT-50), (255, 0, 0), 3)
        cv2.line(img, (50, HEIGHT-50), (WIDTH-50, 50), (255, 0, 0), 3)

        # Send the frame to the virtual camera
        cam.send(img)

        # Wait for the next frame
        cam.sleep_until_next_frame()