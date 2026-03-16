from flask import Flask, render_template, send_from_directory, redirect, url_for, request, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import json

app = Flask(__name__)
app.secret_key = "autoguard_secret_key"

# Admin bilgileri
ADMIN_USERNAME = "admin"

# Şifre: 12345
# İstersen sonra kendi hash'inle değiştirebilirsin.
ADMIN_PASSWORD_HASH = generate_password_hash("12345")

DB_PATH = "autoguard.db"
CONFIG_PATH = "config.json"
IMAGES_FOLDER = "images"


def get_db_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def get_events():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM events ORDER BY id DESC")
    rows = cursor.fetchall()
    connection.close()
    return rows


def get_stats():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM events")
    total_events = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM events WHERE status = 'unreviewed'")
    unreviewed = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM events WHERE status = 'reviewed'")
    reviewed = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM events WHERE status = 'false alarm'")
    false_alarm = cursor.fetchone()[0]

    connection.close()
    return total_events, unreviewed, reviewed, false_alarm


def load_config():
    if not os.path.exists(CONFIG_PATH):
        default_config = {
            "motion_area_threshold": 5000,
            "cooldown_seconds": 10
        }
        save_config(default_config)
        return default_config

    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def save_config(config_data):
    with open(CONFIG_PATH, "w", encoding="utf-8") as file:
        json.dump(config_data, file, indent=4)


@app.route("/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(IMAGES_FOLDER, filename)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session["admin_logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid username or password"

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("login"))


@app.route("/")
def dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    events = get_events()
    total_events, unreviewed, reviewed, false_alarm = get_stats()
    config = load_config()

    return render_template(
        "dashboard.html",
        events=events,
        total_events=total_events,
        unreviewed=unreviewed,
        reviewed=reviewed,
        false_alarm=false_alarm,
        config=config
    )


@app.route("/mark_reviewed/<int:event_id>")
def mark_reviewed(event_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE events SET status = 'reviewed' WHERE id = ?", (event_id,))
    connection.commit()
    connection.close()

    return redirect(url_for("dashboard"))


@app.route("/mark_false_alarm/<int:event_id>")
def mark_false_alarm(event_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE events SET status = 'false alarm' WHERE id = ?", (event_id,))
    connection.commit()
    connection.close()

    return redirect(url_for("dashboard"))


@app.route("/delete_event/<int:event_id>")
def delete_event(event_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT image_path FROM events WHERE id = ?", (event_id,))
    row = cursor.fetchone()

    if row:
        image_path = row["image_path"] if isinstance(row, sqlite3.Row) else row[0]

        if image_path and os.path.exists(image_path):
            os.remove(image_path)

        cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
        connection.commit()

    connection.close()
    return redirect(url_for("dashboard"))


@app.route("/add_note/<int:event_id>", methods=["POST"])
def add_note(event_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    note = request.form.get("note", "")

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE events SET note = ? WHERE id = ?", (note, event_id))
    connection.commit()
    connection.close()

    return redirect(url_for("dashboard"))


@app.route("/update_settings", methods=["POST"])
def update_settings():
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    motion_area_threshold = int(request.form.get("motion_area_threshold", 5000))
    cooldown_seconds = int(request.form.get("cooldown_seconds", 10))

    config_data = {
        "motion_area_threshold": motion_area_threshold,
        "cooldown_seconds": cooldown_seconds
    }

    save_config(config_data)
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True)