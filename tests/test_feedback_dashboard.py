import http.client
from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest

from feedback_dashboard import make_handler
from x2_agent.dining_feedback import save_feedback


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "feedback.jsonl"
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.path))
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=.01), daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=1)
        self.tmp.cleanup()

    def get(self, route="/"):
        client = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
        try:
            client.request("GET", route)
            response = client.getresponse()
            return response.status, dict(response.getheaders()), response.read().decode("utf-8")
        finally:
            client.close()

    def test_page_reflects_confirmed_records_on_refresh_and_escapes_text(self):
        status, headers, body = self.get()
        self.assertEqual(status, 200)
        self.assertIn("尚无已确认的意见", body)
        save_feedback({"id": "one", "category": "taste", "item": "<script>汤</script>",
                       "observation": "有点咸", "request": "少放盐", "status": "new"}, self.path)
        status, headers, body = self.get()
        self.assertEqual(status, 200)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertIn("&lt;script&gt;汤&lt;/script&gt;", body)
        self.assertNotIn("<script>", body)
        self.assertIn("有点咸", body)
        self.assertIn("少放盐", body)

    def test_corrupt_records_return_503_instead_of_resetting_connection(self):
        for content in ("invalid json\n", "42\n"):
            with self.subTest(content=content):
                self.path.write_text(content, encoding="utf-8")
                status, _, _ = self.get()
                self.assertEqual(status, 503)

    def test_unrelated_routes_return_404(self):
        status, _, _ = self.get("/missing")
        self.assertEqual(status, 404)
