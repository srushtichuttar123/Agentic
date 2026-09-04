"""Minimal event management API for the documented MVP."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

DATABASE_PATH = os.getenv("EVENT_DATABASE", "events.db")
HOST = os.getenv("EVENT_HOST", "127.0.0.1")
PORT = int(os.getenv("EVENT_PORT", "8000"))
TOKEN_TTL_SECONDS = 60 * 60 * 24


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exception_type, exception_value, traceback):
        try:
            return super().__exit__(exception_type, exception_value, traceback)
        finally:
            self.close()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, salt_hex, digest_hex = stored.split("$", 2)
        if algorithm != "scrypt":
            return False
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=16384, r=8, p=1)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH, factory=ClosingConnection)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    with connect() as database:
        database.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('HEAD_USER', 'VIEWER')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                created_by TEXT NOT NULL REFERENCES users(id),
                title TEXT NOT NULL,
                short_description TEXT,
                description TEXT NOT NULL,
                cover_image_url TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                timezone TEXT NOT NULL,
                venue_name TEXT,
                address TEXT,
                meeting_url TEXT,
                organizer_name TEXT NOT NULL,
                organizer_email TEXT NOT NULL,
                capacity INTEGER NOT NULL CHECK (capacity > 0),
                registration_start TEXT,
                registration_end TEXT,
                status TEXT NOT NULL CHECK (status IN ('DRAFT', 'PUBLISHED', 'UNPUBLISHED', 'CANCELLED')),
                published_at TEXT,
                cancellation_reason TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                CHECK (end_time > start_time),
                CHECK (registration_start IS NULL OR registration_end IS NULL OR registration_start < registration_end)
            );
            CREATE TABLE IF NOT EXISTS registrations (
                id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                viewer_id TEXT NOT NULL REFERENCES users(id),
                status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'CANCELLED')),
                registered_at TEXT NOT NULL,
                cancelled_at TEXT,
                UNIQUE (event_id, viewer_id)
            );
            CREATE INDEX IF NOT EXISTS events_public_listing ON events(status, start_time);
            CREATE INDEX IF NOT EXISTS events_owner_status ON events(created_by, status, updated_at);
            CREATE INDEX IF NOT EXISTS registrations_event_status ON registrations(event_id, status);
            CREATE INDEX IF NOT EXISTS registrations_viewer_status ON registrations(viewer_id, status);
            """
        )


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, fields: dict[str, str] | None = None):
        self.status = status
        self.code = code
        self.message = message
        self.fields = fields or {}


class EventHandler(BaseHTTPRequestHandler):
    server_version = "EventManagementAPI/0.1"
    sessions: dict[str, tuple[str, float]] = {}

    def send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def error(self, error: ApiError) -> None:
        self.send_json(error.status, {"error": {"code": error.code, "message": error.message, "fields": error.fields}})

    def body(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 1_000_000:
                raise ApiError(413, "PAYLOAD_TOO_LARGE", "Request body is too large.")
            payload = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(payload, dict):
                raise ValueError
            return payload
        except (json.JSONDecodeError, ValueError):
            raise ApiError(400, "INVALID_JSON", "Request body must be a JSON object.")

    def session_user(self, required_role: str | None = None) -> sqlite3.Row:
        header = self.headers.get("Authorization", "")
        token = header.removeprefix("Bearer ").strip()
        session = self.sessions.get(token)
        if not session or session[1] < datetime.now(timezone.utc).timestamp():
            raise ApiError(401, "UNAUTHORIZED", "Authentication is required.")
        with connect() as database:
            user = database.execute("SELECT * FROM users WHERE id = ?", (session[0],)).fetchone()
        if not user:
            raise ApiError(401, "UNAUTHORIZED", "Authentication is required.")
        if required_role and user["role"] != required_role:
            raise ApiError(403, "FORBIDDEN", "This action is not allowed for your role.")
        return user

    def route_parts(self) -> list[str]:
        return [part for part in urlparse(self.path).path.split("/") if part]

    def do_GET(self) -> None:
        try:
            parts = self.route_parts()
            if parts == ["health"]:
                self.send_json(200, {"status": "ok"})
            elif parts == ["api", "me"]:
                user = self.session_user()
                self.send_json(200, {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]})
            elif parts == ["api", "events"]:
                self.list_events()
            elif len(parts) == 3 and parts[:2] == ["api", "events"]:
                self.get_public_event(parts[2])
            elif parts == ["api", "manage", "events"]:
                self.list_managed_events()
            elif len(parts) == 4 and parts[:2] == ["api", "events"] and parts[3] == "attendees":
                self.list_attendees(parts[2])
            elif parts == ["api", "me", "registrations"]:
                self.list_registrations()
            else:
                raise ApiError(404, "NOT_FOUND", "Route not found.")
        except ApiError as error:
            self.error(error)

    def do_POST(self) -> None:
        try:
            parts = self.route_parts()
            if parts == ["api", "auth", "signup"]:
                self.signup()
            elif parts == ["api", "auth", "signin"]:
                self.signin()
            elif parts == ["api", "auth", "signout"]:
                self.signout()
            elif parts == ["api", "events"]:
                self.create_event()
            elif len(parts) == 4 and parts[:2] == ["api", "events"] and parts[3] == "publish":
                self.change_event_status(parts[2], "PUBLISHED")
            elif len(parts) == 4 and parts[:2] == ["api", "events"] and parts[3] == "unpublish":
                self.change_event_status(parts[2], "UNPUBLISHED")
            elif len(parts) == 4 and parts[:2] == ["api", "events"] and parts[3] == "cancel":
                self.cancel_event(parts[2])
            elif len(parts) == 4 and parts[:2] == ["api", "events"] and parts[3] == "registrations":
                self.register(parts[2])
            else:
                raise ApiError(404, "NOT_FOUND", "Route not found.")
        except ApiError as error:
            self.error(error)

    def do_PATCH(self) -> None:
        try:
            parts = self.route_parts()
            if len(parts) == 3 and parts[:2] == ["api", "events"]:
                self.update_event(parts[2])
            else:
                raise ApiError(404, "NOT_FOUND", "Route not found.")
        except ApiError as error:
            self.error(error)

    def do_DELETE(self) -> None:
        try:
            parts = self.route_parts()
            if len(parts) == 4 and parts[:2] == ["api", "events"] and parts[3] == "registrations":
                self.cancel_registration(parts[2])
            elif len(parts) == 3 and parts[:2] == ["api", "events"]:
                self.delete_event(parts[2])
            else:
                raise ApiError(404, "NOT_FOUND", "Route not found.")
        except ApiError as error:
            self.error(error)

    def signup(self) -> None:
        payload = self.body()
        name, email, password = str(payload.get("name", "")).strip(), str(payload.get("email", "")).strip().lower(), str(payload.get("password", ""))
        role = str(payload.get("role", "VIEWER"))
        fields = {}
        if not name: fields["name"] = "Name is required."
        if not email or "@" not in email: fields["email"] = "A valid email is required."
        if len(password) < 8: fields["password"] = "Password must contain at least 8 characters."
        if role not in {"HEAD_USER", "VIEWER"}: fields["role"] = "Role is invalid."
        if fields: raise ApiError(422, "VALIDATION_ERROR", "The request contains invalid fields.", fields)
        user_id = str(uuid.uuid4())
        try:
            with connect() as database:
                database.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", (user_id, name, email, hash_password(password), role, utc_now(), utc_now()))
        except sqlite3.IntegrityError:
            raise ApiError(409, "EMAIL_EXISTS", "An account with this email already exists.")
        self.send_json(201, {"id": user_id, "name": name, "email": email, "role": role})

    def signin(self) -> None:
        payload = self.body()
        email, password = str(payload.get("email", "")).strip().lower(), str(payload.get("password", ""))
        with connect() as database:
            user = database.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not user or not verify_password(password, user["password_hash"]):
            raise ApiError(401, "INVALID_CREDENTIALS", "Email or password is incorrect.")
        token = secrets.token_urlsafe(32)
        self.sessions[token] = (user["id"], datetime.now(timezone.utc).timestamp() + TOKEN_TTL_SECONDS)
        self.send_json(200, {"token": token, "user": {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]}})

    def signout(self) -> None:
        self.session_user()
        token = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        self.sessions.pop(token, None)
        self.send_json(204, {})

    def validate_event_payload(self, payload: dict[str, Any], require_all: bool = True) -> dict[str, str]:
        required = ["title", "description", "start_time", "end_time", "timezone", "organizer_name", "organizer_email", "capacity"]
        fields = {field: "This field is required." for field in required if require_all and payload.get(field) in (None, "")}
        if "capacity" in payload:
            try:
                if int(payload["capacity"]) <= 0:
                    fields["capacity"] = "Capacity must be greater than zero."
            except (TypeError, ValueError):
                fields["capacity"] = "Capacity must be an integer."
        if payload.get("start_time") and payload.get("end_time") and payload["end_time"] <= payload["start_time"]:
            fields["end_time"] = "End time must be after start time."
        if payload.get("organizer_email") and "@" not in str(payload["organizer_email"]):
            fields["organizer_email"] = "A valid email is required."
        return fields

    def create_event(self) -> None:
        user = self.session_user("HEAD_USER")
        payload = self.body()
        fields = self.validate_event_payload(payload)
        try: capacity = int(payload.get("capacity", 0))
        except (TypeError, ValueError): capacity = 0
        if fields: raise ApiError(422, "VALIDATION_ERROR", "The request contains invalid fields.", fields)
        event_id, now = str(uuid.uuid4()), utc_now()
        values = (event_id, user["id"], payload["title"], payload.get("short_description"), payload["description"], payload.get("cover_image_url"), payload["start_time"], payload["end_time"], payload["timezone"], payload.get("venue_name"), payload.get("address"), payload.get("meeting_url"), payload["organizer_name"], payload["organizer_email"], capacity, payload.get("registration_start"), payload.get("registration_end"), "DRAFT", None, None, now, now)
        try:
            with connect() as database:
                database.execute("INSERT INTO events (id, created_by, title, short_description, description, cover_image_url, start_time, end_time, timezone, venue_name, address, meeting_url, organizer_name, organizer_email, capacity, registration_start, registration_end, status, published_at, cancellation_reason, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", values)
        except sqlite3.IntegrityError as error:
            raise ApiError(422, "VALIDATION_ERROR", str(error))
        self.send_json(201, {"id": event_id, "status": "DRAFT"})

    def update_event(self, event_id: str) -> None:
        self.owned_event(event_id)
        payload = self.body()
        allowed = {"title", "short_description", "description", "cover_image_url", "start_time", "end_time", "timezone", "venue_name", "address", "meeting_url", "organizer_name", "organizer_email", "capacity", "registration_start", "registration_end"}
        updates = {key: value for key, value in payload.items() if key in allowed}
        if not updates:
            raise ApiError(422, "VALIDATION_ERROR", "At least one editable field is required.")
        fields = self.validate_event_payload(updates, require_all=False)
        if fields:
            raise ApiError(422, "VALIDATION_ERROR", "The request contains invalid fields.", fields)
        assignments = ", ".join(f"{key} = ?" for key in updates)
        values = list(updates.values()) + [utc_now(), event_id]
        with connect() as database:
            database.execute(f"UPDATE events SET {assignments}, updated_at = ? WHERE id = ?", values)
        self.send_json(200, {"id": event_id, "status": "UPDATED"})

    def owned_event(self, event_id: str) -> sqlite3.Row:
        user = self.session_user("HEAD_USER")
        with connect() as database: event = database.execute("SELECT * FROM events WHERE id = ? AND created_by = ?", (event_id, user["id"])).fetchone()
        if not event: raise ApiError(404, "NOT_FOUND", "Event not found.")
        return event

    def change_event_status(self, event_id: str, status: str) -> None:
        event = self.owned_event(event_id)
        if status == "PUBLISHED" and (not event["title"] or not event["description"]): raise ApiError(422, "VALIDATION_ERROR", "Required event fields are missing.")
        if event["status"] == "CANCELLED": raise ApiError(409, "INVALID_STATUS", "Cancelled events cannot be published or changed.")
        with connect() as database: database.execute("UPDATE events SET status = ?, published_at = COALESCE(published_at, ?), updated_at = ? WHERE id = ?", (status, utc_now() if status == "PUBLISHED" else None, utc_now(), event_id))
        self.send_json(200, {"id": event_id, "status": status})

    def cancel_event(self, event_id: str) -> None:
        self.owned_event(event_id)
        reason = str(self.body().get("reason", "")).strip()
        if not reason: raise ApiError(422, "VALIDATION_ERROR", "Cancellation reason is required.", {"reason": "Reason is required."})
        with connect() as database: database.execute("UPDATE events SET status = 'CANCELLED', cancellation_reason = ?, updated_at = ? WHERE id = ?", (reason, utc_now(), event_id))
        self.send_json(200, {"id": event_id, "status": "CANCELLED", "cancellation_reason": reason})

    def list_events(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        search = query.get("search", [""])[0]
        with connect() as database:
            events = database.execute("SELECT id, title, short_description, start_time, end_time, timezone, venue_name, address, capacity, status FROM events WHERE status = 'PUBLISHED' AND start_time >= ? AND (title LIKE ? OR description LIKE ?) ORDER BY start_time LIMIT 100", (utc_now(), f"%{search}%", f"%{search}%")).fetchall()
        self.send_json(200, {"items": [dict(event) for event in events]})

    def get_public_event(self, event_id: str) -> None:
        with connect() as database: event = database.execute("SELECT id, title, short_description, description, cover_image_url, start_time, end_time, timezone, venue_name, address, meeting_url, organizer_name, organizer_email, capacity, registration_start, registration_end, status, cancellation_reason FROM events WHERE id = ? AND status = 'PUBLISHED'", (event_id,)).fetchone()
        if not event: raise ApiError(404, "NOT_FOUND", "Event not found.")
        self.send_json(200, dict(event))

    def list_attendees(self, event_id: str) -> None:
        self.owned_event(event_id)
        with connect() as database:
            attendees = database.execute("SELECT r.id, r.status, r.registered_at, u.id AS viewer_id, u.name, u.email FROM registrations r JOIN users u ON u.id = r.viewer_id WHERE r.event_id = ? ORDER BY r.registered_at", (event_id,)).fetchall()
        self.send_json(200, {"items": [dict(attendee) for attendee in attendees]})

    def list_managed_events(self) -> None:
        user = self.session_user("HEAD_USER")
        with connect() as database: events = database.execute("SELECT * FROM events WHERE created_by = ? ORDER BY start_time", (user["id"],)).fetchall()
        self.send_json(200, {"items": [dict(event) for event in events]})

    def register(self, event_id: str) -> None:
        user = self.session_user("VIEWER")
        with connect() as database:
            database.execute("BEGIN IMMEDIATE")
            event = database.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
            if not event: raise ApiError(404, "NOT_FOUND", "Event not found.")
            if event["status"] != "PUBLISHED": raise ApiError(409, "REGISTRATION_CLOSED", "This event is not available for registration.")
            active = database.execute("SELECT COUNT(*) AS count FROM registrations WHERE event_id = ? AND status = 'ACTIVE'", (event_id,)).fetchone()["count"]
            existing = database.execute("SELECT id FROM registrations WHERE event_id = ? AND viewer_id = ? AND status = 'ACTIVE'", (event_id, user["id"])).fetchone()
            if existing: raise ApiError(409, "ALREADY_REGISTERED", "You are already registered for this event.")
            if active >= event["capacity"]: raise ApiError(409, "EVENT_FULL", "This event is full.")
            registration_id = str(uuid.uuid4())
            database.execute("INSERT INTO registrations VALUES (?, ?, ?, 'ACTIVE', ?, NULL)", (registration_id, event_id, user["id"], utc_now()))
            database.commit()
        self.send_json(201, {"id": registration_id, "event_id": event_id, "status": "ACTIVE"})

    def list_registrations(self) -> None:
        user = self.session_user("VIEWER")
        with connect() as database: registrations = database.execute("SELECT r.*, e.title, e.start_time FROM registrations r JOIN events e ON e.id = r.event_id WHERE r.viewer_id = ? ORDER BY e.start_time", (user["id"],)).fetchall()
        self.send_json(200, {"items": [dict(item) for item in registrations]})

    def cancel_registration(self, event_id: str) -> None:
        user = self.session_user("VIEWER")
        with connect() as database:
            event = database.execute("SELECT start_time FROM events WHERE id = ?", (event_id,)).fetchone()
            if not event:
                raise ApiError(404, "NOT_FOUND", "Event not found.")
            if event["start_time"] <= utc_now():
                raise ApiError(409, "EVENT_STARTED", "Registration cannot be cancelled after the event starts.")
            result = database.execute("UPDATE registrations SET status = 'CANCELLED', cancelled_at = ? WHERE event_id = ? AND viewer_id = ? AND status = 'ACTIVE'", (utc_now(), event_id, user["id"]))
        if result.rowcount == 0: raise ApiError(404, "NOT_FOUND", "Active registration not found.")
        self.send_json(200, {"event_id": event_id, "status": "CANCELLED"})

    def delete_event(self, event_id: str) -> None:
        event = self.owned_event(event_id)
        if event["status"] != "DRAFT": raise ApiError(409, "INVALID_STATUS", "Only draft events can be deleted.")
        with connect() as database: database.execute("DELETE FROM events WHERE id = ?", (event_id,))
        self.send_json(204, {})


def run() -> None:
    initialize_database()
    server = ThreadingHTTPServer((HOST, PORT), EventHandler)
    print(f"Event Management API running at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    run()
