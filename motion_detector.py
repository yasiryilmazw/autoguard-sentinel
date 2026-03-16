import cv2
import datetime
import os
import time
import sqlite3
import json
from telegram_alert import send_message, send_photo


CAMERA_INDEX = 0
CAMERA_WARMUP_TIME = 3


os.makedirs("images", exist_ok=True)


def load_config():
    with open("config.json", "r") as file:
        return json.load(file)


def save_event(image_path, timestamp):
    connection = sqlite3.connect("autoguard.db")
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO events (timestamp, image_path)
        VALUES (?, ?)
    """, (timestamp, image_path))

    connection.commit()
    connection.close()


def main():
    print("Starting AutoGuard motion detector...")

    config = load_config()
    motion_area_threshold = config["motion_area_threshold"]
    cooldown_seconds = config["cooldown_seconds"]

    print(f"Motion threshold: {motion_area_threshold}")
    print(f"Cooldown seconds: {cooldown_seconds}")

    camera = cv2.VideoCapture(CAMERA_INDEX)

    print("Camera warming up...")
    time.sleep(CAMERA_WARMUP_TIME)

    ret, frame1 = camera.read()
    ret, frame2 = camera.read()

    if not ret:
        print("Failed to access camera.")
        camera.release()
        return

    last_capture_time = 0

    while True:
        diff = cv2.absdiff(frame1, frame2)

        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)

        _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
        dilated = cv2.dilate(thresh, None, iterations=3)

        contours, _ = cv2.findContours(
            dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )

        motion_detected = False

        for contour in contours:
            if cv2.contourArea(contour) < motion_area_threshold:
                continue

            motion_detected = True

            x, y, w, h = cv2.boundingRect(contour)

            cv2.rectangle(
                frame1,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                2
            )

        current_time = time.time()

        if motion_detected and (current_time - last_capture_time) > cooldown_seconds:
            print("Motion detected!")

            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            filename = f"images/motion_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.jpg"

            cv2.imwrite(filename, frame1)

            try:
                send_message("🚨 Motion detected by AutoGuard!")
                send_photo(filename)
            except Exception as e:
                print("Telegram error:", e)

            save_event(filename, timestamp)

            print("Image saved:", filename)
            print("Event saved to database.")

            last_capture_time = current_time

        cv2.imshow("AutoGuard Motion Detection", frame1)

        frame1 = frame2
        ret, frame2 = camera.read()

        if not ret:
            break

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()