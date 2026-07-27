"""
navigation.py
--------------
Vision-guided navigation loop for the simulated AUV pipe-following system.

Captures a screen region as the agent's "camera" feed, isolates the pipe using
HSV masking, estimates its angle via contour + minimum-area-rectangle, and uses
that to correct the agent's heading (visual servoing). The agent then walks the
pipe autonomously via simulated keyboard/mouse input.

Environment: Minecraft (used as a visual testbed).
Tech: OpenCV, NumPy, PyAutoGUI.
"""

import cv2
import pyautogui as pg
import numpy as np
import math
import time


# ---------------------------------------------------------------------------
# Movement primitives
# ---------------------------------------------------------------------------

def walk():
    """Take a short step forward."""
    pg.keyDown("w")
    time.sleep(0.003)
    pg.keyUp("w")


def left():
    """Turn the view left while nudging forward."""
    time.sleep(0.1)
    pg.keyDown("w")
    time.sleep(0.3)
    pg.keyUp("w")
    for _ in range(65):
        x, y = pg.position()
        x -= 10
        pg.moveTo(x, y)
    time.sleep(0.1)
    pg.keyDown("w")
    time.sleep(0.5)
    pg.keyUp("w")


def right():
    """Turn the view right while nudging forward."""
    walk()
    for _ in range(65):
        x, y = pg.position()
        x += 10
        pg.moveTo(x, y)
    time.sleep(0.1)
    pg.keyDown("w")
    time.sleep(0.5)
    pg.keyUp("w")


def align(angle, x, y):
    """Nudge the view horizontally to correct heading toward vertical (90 deg)."""
    if angle < 90:
        x -= 1
        pg.moveTo(x, y)
    elif angle > 90:
        x += 1
        pg.moveTo(x, y)
    return x, y


def autocenter(center_x, center_y, screen_width=700, tolerance=10):
    """Strafe left/right to keep the pipe centered horizontally."""
    screen_center_x = screen_width // 2
    offset = center_x - screen_center_x
    if abs(offset) > tolerance:
        if offset > 0:
            pg.keyDown("a")
            pg.keyUp("a")
        else:
            pg.keyDown("d")
            pg.keyUp("d")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Region of the screen to capture: (left, top, width, height)
region = (100, 100, 700, 500)
mid = 300

# HSV range used to mask the pipe from the background
lower_hsv = np.array([0, 0, 0])
upper_hsv = np.array([35, 255, 255])

# Reduce PyAutoGUI's built-in pause between calls
pg.PAUSE = 0.01

# Give the user time to switch focus to the game window
time.sleep(5)


# ---------------------------------------------------------------------------
# Initial alignment pass
# ---------------------------------------------------------------------------

screen = pg.screenshot(region=region)
img = np.array(screen)
img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
binary_mask = cv2.inRange(hsv, lower_hsv, upper_hsv)
contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

for contour in contours:
    area = cv2.contourArea(contour)
    if 3000 < area < 400000:
        rect = cv2.minAreaRect(contour)
        (center_x, center_y), (width, height), angle = rect
        if width < height:
            angle = angle + 90
        x, y = pg.position()
        x, y = align(angle, x, y)
        break

oriented = False
aligned = False


# ---------------------------------------------------------------------------
# Main perception-to-control loop
# ---------------------------------------------------------------------------

while True:
    # Capture the current frame
    screen = pg.screenshot(region=region)
    img = np.array(screen)
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    binary_mask = cv2.inRange(hsv, lower_hsv, upper_hsv)

    # Sample two probe points on the mask to detect when the pipe turns
    pixel1 = binary_mask[50, 550]  # right probe
    pixel2 = binary_mask[50, 200]  # left probe

    # Hough-line overlay (visualization / alignment aid)
    hough_display = img_bgr.copy()
    blurred = cv2.GaussianBlur(img_bgr, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)
    if lines is not None:
        for rho, theta in lines[0]:
            a = np.cos(theta)
            b = np.sin(theta)
            x0 = a * rho
            y0 = b * rho
            x1 = int(x0 + 1000 * (-b))
            y1 = int(y0 + 1000 * (a))
            x2 = int(x0 - 1000 * (-b))
            y2 = int(y0 - 1000 * (a))
            cv2.line(hough_display, (x1, y1), (x2, y2), (0, 0, 255), 2)

    # Find the pipe contour
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    image_color = img_bgr.copy()

    contour_found = False
    for contour in contours:
        area = cv2.contourArea(contour)
        if 3000 < area < 100000:
            contour_found = True
            rect = cv2.minAreaRect(contour)
            (center_x, center_y), (width, height), angle = rect

            if width < height:
                angle = angle + 90

            angle_from_vertical = angle
            box = cv2.boxPoints(rect)
            box = np.array(box, dtype=int)
            cv2.drawContours(image_color, [box], 0, (0, 255, 0), 2)

            # Correct heading until the pipe reads as vertical (90 deg)
            if angle != 90:
                aligned = False
                x, y = pg.position()
                x, y = align(angle, x, y)
            if angle == 90:
                aligned = True
                if center_x > 440:
                    print("Right")
                    pg.keyDown("d")
                    pg.keyUp("d")
                    time.sleep(0.1)
                elif center_x < 340:
                    print("Left")
                    pg.keyDown("a")
                    pg.keyUp("a")
                    time.sleep(0.1)
                else:
                    walk()

            # Consider the agent "oriented" when the pipe is roughly centered
            oriented = center_x in range(320, 430)
            if aligned and oriented:
                walk()

            text = f"Angle: {angle_from_vertical:.2f} deg"
            cv2.putText(image_color, text, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            break

    # No pipe in view: use the probe points to decide which way it turned
    if not contour_found:
        if pixel1 != 0:
            print("Turning Right")
            right()
        elif pixel2 != 0:
            print("Turning Left")
            left()
        else:
            walk()
        print(pixel1, pixel2)
        pg.keyUp("w")
        cv2.putText(image_color, "No contours > 3000 px found", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # Debug overlays
    cv2.circle(image_color, (550, 400), 10, (0, 255, 255), -1)
    cv2.circle(image_color, (200, 400), 10, (0, 0, 255), -1)

    cv2.imshow("HSV Mask", binary_mask)
    cv2.imshow("Hough Lines", hough_display)
    cv2.imshow("Pipeline with Angle", image_color)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
