import http.client
import json
import os
import tempfile
import threading
import unittest

import server


class BackendApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database_file = tempfile.NamedTemporaryFile(delete=False)
        cls.database_file.close()
        server.DATABASE_PATH = cls.database_file.name
        server.EventHandler.sessions.clear()
        server.initialize_database()
        cls.http_server = server.ThreadingHTTPServer(("127.0.0.1", 0), server.EventHandler)
        cls.thread = threading.Thread(target=cls.http_server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.http_server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.http_server.shutdown()
        cls.http_server.server_close()
        cls.thread.join(timeout=2)
        os.unlink(cls.database_file.name)

    def request(self, method, path, payload=None, token=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port)
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        body = json.dumps(payload) if payload is not None else None
        connection.request(method, path, body, headers)
        response = connection.getresponse()
        raw = response.read()
        connection.close()
        return response.status, json.loads(raw or b"{}")

    def signup(self, email, role):
        status, result = self.request("POST", "/api/auth/signup", {"name": role, "email": email, "password": "password123", "role": role})
        self.assertEqual(status, 201)
        status, result = self.request("POST", "/api/auth/signin", {"email": email, "password": "password123"})
        self.assertEqual(status, 200)
        return result["token"]

    def test_health_and_authentication(self):
        status, result = self.request("GET", "/health")
        self.assertEqual((status, result), (200, {"status": "ok"}))
        status, _ = self.request("GET", "/api/me")
        self.assertEqual(status, 401)
        head_token = self.signup("head@example.com", "HEAD_USER")
        status, result = self.request("GET", "/api/me", token=head_token)
        self.assertEqual(status, 200)
        self.assertEqual(result["role"], "HEAD_USER")
        status, _ = self.request("POST", "/api/auth/signout", token=head_token)
        self.assertEqual(status, 204)
        status, _ = self.request("GET", "/api/me", token=head_token)
        self.assertEqual(status, 401)

    def test_event_lifecycle_visibility_and_ownership(self):
        head_token = self.signup("owner@example.com", "HEAD_USER")
        other_head_token = self.signup("other@example.com", "HEAD_USER")
        viewer_token = self.signup("viewer@example.com", "VIEWER")
        event = {"title": "Launch", "description": "Product launch", "start_time": "2099-01-01T10:00:00+00:00", "end_time": "2099-01-01T11:00:00+00:00", "timezone": "UTC", "venue_name": "Hall", "address": "1 Main St", "organizer_name": "Owner", "organizer_email": "owner@example.com", "capacity": 1}
        status, result = self.request("POST", "/api/events", event, head_token)
        self.assertEqual(status, 201)
        event_id = result["id"]
        status, result = self.request("GET", "/api/events")
        self.assertEqual((status, result["items"]), (200, []))
        status, _ = self.request("POST", f"/api/events/{event_id}/publish", token=other_head_token)
        self.assertEqual(status, 404)
        status, _ = self.request("PATCH", f"/api/events/{event_id}", {"title": "Updated Launch"}, token=head_token)
        self.assertEqual(status, 200)
        status, _ = self.request("POST", f"/api/events/{event_id}/publish", token=head_token)
        self.assertEqual(status, 200)
        status, result = self.request("GET", "/api/events?search=Updated")
        self.assertEqual(status, 200)
        self.assertEqual(result["items"][0]["title"], "Updated Launch")
        status, _ = self.request("GET", f"/api/events/{event_id}", token=viewer_token)
        self.assertEqual(status, 200)

    def test_registration_capacity_duplicate_cancel_and_attendees(self):
        head_token = self.signup("organizer@example.com", "HEAD_USER")
        viewer_token = self.signup("attendee@example.com", "VIEWER")
        second_viewer_token = self.signup("second@example.com", "VIEWER")
        event = {"title": "Small Event", "description": "One seat", "start_time": "2099-02-01T10:00:00+00:00", "end_time": "2099-02-01T11:00:00+00:00", "timezone": "UTC", "venue_name": "Room", "address": "2 Main St", "organizer_name": "Organizer", "organizer_email": "organizer@example.com", "capacity": 1}
        status, result = self.request("POST", "/api/events", event, head_token)
        event_id = result["id"]
        self.assertEqual(self.request("POST", f"/api/events/{event_id}/publish", token=head_token)[0], 200)
        self.assertEqual(self.request("POST", f"/api/events/{event_id}/registrations", token=viewer_token)[0], 201)
        status, result = self.request("POST", f"/api/events/{event_id}/registrations", token=viewer_token)
        self.assertEqual((status, result["error"]["code"]), (409, "ALREADY_REGISTERED"))
        status, result = self.request("POST", f"/api/events/{event_id}/registrations", token=second_viewer_token)
        self.assertEqual((status, result["error"]["code"]), (409, "EVENT_FULL"))
        status, result = self.request("GET", f"/api/events/{event_id}/attendees", token=head_token)
        self.assertEqual((status, len(result["items"])), (200, 1))
        self.assertEqual(self.request("DELETE", f"/api/events/{event_id}/registrations", token=viewer_token)[0], 200)
        self.assertEqual(self.request("POST", f"/api/events/{event_id}/registrations", token=second_viewer_token)[0], 201)
        self.assertEqual(self.request("POST", f"/api/events/{event_id}/cancel", {"reason": "Venue unavailable"}, token=head_token)[0], 200)
        status, result = self.request("POST", f"/api/events/{event_id}/registrations", token=viewer_token)
        self.assertEqual((status, result["error"]["code"]), (409, "REGISTRATION_CLOSED"))

    def test_validation_and_role_protection(self):
        viewer_token = self.signup("validation-viewer@example.com", "VIEWER")
        status, result = self.request("POST", "/api/events", {}, token=viewer_token)
        self.assertEqual((status, result["error"]["code"]), (403, "FORBIDDEN"))
        head_token = self.signup("validation-head@example.com", "HEAD_USER")
        status, result = self.request("POST", "/api/events", {"title": "Bad", "description": "Bad", "start_time": "2099-01-01T11:00:00+00:00", "end_time": "2099-01-01T10:00:00+00:00", "timezone": "UTC", "organizer_name": "Owner", "organizer_email": "bad", "capacity": 0}, token=head_token)
        self.assertEqual(status, 422)
        self.assertIn("capacity", result["error"]["fields"])
        self.assertIn("end_time", result["error"]["fields"])
        self.assertIn("organizer_email", result["error"]["fields"])


if __name__ == "__main__":
    unittest.main()
