import cv2
import datetime
import os
import time
import sqlite3
import json
from ultralytics import YOLO
from telegram_alert import send_message, send_photo

CAMERA_INDEX = 0
CAMERA_WARMUP_TIME = 3
IMAGES_FOLDER = "images"
DB_PATH = "autoguard.db"
CONFIG_PATH = "config.json"

os.makedirs(IMAGES_FOLDER, exist_ok=True)

# YOLO model
model = YOLO("yolov8n.pt")


def log_info(message):
    print(f"[INFO] {message}")


def log_error(message):
    print(f"[ERROR] {message}")


def cleanup_old_images(folder="images", days=30):
    try:
        if not os.path.exists(folder):
            return

        now = time.time()
        cutoff = now - (days * 86400)

        for filename in os.listdir(folder):
            filepath = os.path.join(folder, filename)

            if os.path.isfile(filepath):
                file_time = os.path.getmtime(filepath)

                if file_time < cutoff:
                    try:
                        os.remove(filepath)
                        print(f"[HOUSEKEEPING] Deleted: {filename}")
                    except Exception as e:
                        print(f"[HOUSEKEEPING ERROR] {e}")

    except Exception as e:
        log_error(f"Housekeeping Error: {e}")


def load_config():
    default_config = {
        "motion_area_threshold": 5000,
        "cooldown_seconds": 10
    }

    try:
        if not os.path.exists(CONFIG_PATH):
            log_info("config.json not found. Using default configuration.")
            return default_config

        with open(CONFIG_PATH, "r", encoding="utf-8") as file:
            config = json.load(file)

        return {
            "motion_area_threshold": config.get("motion_area_threshold", 5000),
            "cooldown_seconds": config.get("cooldown_seconds", 10)
        }

    except Exception as e:
        log_error(f"Failed to read config : {e}")
        return default_config


def save_event(image_path, timestamp):
    connection = None
    try:
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO events (timestamp, image_path)
            VALUES (?, ?)
            """,
            (timestamp, image_path)
        )
        connection.commit()
        log_info("Event saved to database.")
    except Exception as e:
        log_error(f"Database save error: {e}")
    finally:
        if connection:
            connection.close()


def send_telegram_alert(image_path):
    try:
        send_message("Person detected by AutoGuard!")
        send_photo(image_path)
        log_info("Telegram notification  sent.")
    except Exception as e:
        log_error(f"Telegram error: {e}")


def save_motion_image(frame):
    try:
        filename = os.path.join(
            IMAGES_FOLDER,
            f"motion_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.jpg"
        )

        success = cv2.imwrite(filename, frame)

        if not success:
            log_error("Failed to save image.")
            return None

        log_info(f"Image saved: {filename}")
        return filename

    except Exception as e:
        log_error(f"Image save error: {e}")
        return None


def detect_person(frame):
    try:
        results = model(frame, verbose=False)

        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])

                if class_id == 0:
                    confidence = float(box.conf[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    box_width = x2 - x1
                    box_height = y2 - y1
                    box_area = box_width * box_height

                    if confidence >= 0.80 and box_area >= 25000:
                        return True

        return False

    except Exception as e:
        log_error(f"YOLO detection  error: {e}")
        return False


def draw_person_boxes(frame):
    try:
        results = model(frame, verbose=False)

        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])

                if class_id == 0:
                    confidence = float(box.conf[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    box_width = x2 - x1
                    box_height = y2 - y1
                    box_area = box_width * box_height

                    if confidence >= 0.80 and box_area >= 25000:
                        label = f"Person {confidence:.2f}"

                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                        cv2.putText(
                            frame,
                            label,
                            (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (0, 0, 255),
                            2
                        )

        return frame

    except Exception as e:
        log_error(f"YOLO box drawing error: {e}")
        return frame


def main():
    cleanup_old_images()

    log_info("Starting AutoGuard motion detector...")
    log_info("YOLOv8 model loaded")

    config = load_config()
    motion_area_threshold = config["motion_area_threshold"]
    cooldown_seconds = config["cooldown_seconds"]

    log_info(f"Motion threshold: {motion_area_threshold}")
    log_info(f"Cooldown seconds: {cooldown_seconds}")

    camera = None

    try:
        camera = cv2.VideoCapture(CAMERA_INDEX)

        if not camera.isOpened():
            log_error("Failed to open camera.")
            return

        log_info("Camera warming up...")
        time.sleep(CAMERA_WARMUP_TIME)

        ret1, frame1 = camera.read()
        ret2, frame2 = camera.read()

        if not ret1 or not ret2 or frame1 is None or frame2 is None:
            log_error("Failed to read initial frames from the camera.")
            return

        last_capture_time = 0

        while True:
            try:
                diff = cv2.absdiff(frame1, frame2)
                gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                blur = cv2.GaussianBlur(gray, (5, 5), 0)
                _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
                dilated = cv2.dilate(thresh, None, iterations=3)

                contours, _ = cv2.findContours(
                    dilated,
                    cv2.RETR_TREE,
                    cv2.CHAIN_APPROX_SIMPLE
                )

                motion_detected = False

                for contour in contours:
                    if cv2.contourArea(contour) < motion_area_threshold:
                        continue

                    motion_detected = True
                    x, y, w, h = cv2.boundingRect(contour)
                    cv2.rectangle(frame1, (x, y), (x + w, y + h), (0, 255, 0), 2)

                current_time = time.time()

                if motion_detected and (current_time - last_capture_time) > cooldown_seconds:
                    log_info("Motion detected. Running YOLO detection...")

                    person_count = 0

                    if detect_person(frame1):
                        person_count += 1

                    if detect_person(frame2):
                        person_count += 1

                    ret_extra, frame3 = camera.read()
                    if ret_extra and frame3 is not None:
                        if detect_person(frame3):
                            person_count += 1

                    if person_count >= 2:
                        log_info("Person detected.")

                        frame1 = draw_person_boxes(frame1)
                        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        saved_image = save_motion_image(frame1)

                        if saved_image:
                            send_telegram_alert(saved_image)
                            save_event(saved_image, timestamp)
                            last_capture_time = current_time
                    else:
                        log_info("Person not confirmed. Alarm was not sent.")

                cv2.imshow("AutoGuard Motion Detection", frame1)

                frame1 = frame2
                ret, frame2 = camera.read()

                if not ret or frame2 is None:
                    log_error("Failed to read a new frame from the camera. Stopping system.")
                    break

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    log_info("System terminated.")
                    break

            except Exception as e:
                log_error(f"Loop error: {e}")
                time.sleep(1)

    except Exception as e:
        log_error(f"General camera error: {e}")

    finally:
        if camera is not None:
            try:
                camera.release()
            except Exception:
                pass

        cv2.destroyAllWindows()
        log_info("Resources released. System shut down.")


if __name__ == "__main__":
    main()