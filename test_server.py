import json
import threading
import tempfile
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

import server


class NotesServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data_dir = tempfile.TemporaryDirectory()
        self.log_dir = tempfile.TemporaryDirectory()
        server.DATA_DIR = Path(self.data_dir.name)
        server.LOG_DIR = Path(self.log_dir.name)
        server.DATA_DIR.mkdir(exist_ok=True)
        server.LOG_DIR.mkdir(exist_ok=True)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        self.data_dir.cleanup()
        self.log_dir.cleanup()

    def api_get(self, path: str):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        conn.close()
        return resp.status, json.loads(body)

    def api_post(self, path: str, payload: dict):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        conn.request("POST", path, body=data, headers=headers)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        conn.close()
        return resp.status, json.loads(body)

    def test_create_and_list_files(self) -> None:
        status, body = self.api_post("/create_file", {"name": "note1", "content": "hello"})
        self.assertEqual(status, 201)
        self.assertEqual(body["status"], "created")

        status, body = self.api_get("/list_files")
        self.assertEqual(status, 200)
        self.assertEqual(len(body["files"]), 1)
        self.assertEqual(body["files"][0]["name"], "note1.txt")
        self.assertEqual(body["files"][0]["content"], "hello")

    def test_search_files_by_name_and_content(self) -> None:
        self.api_post("/create_file", {"name": "alpha", "content": "first"})
        self.api_post("/create_file", {"name": "beta", "content": "second target"})

        status, body = self.api_post("/search_files", {"query": "alpha"})
        self.assertEqual(status, 200)
        names = [item["name"] for item in body["files"]]
        self.assertEqual(names, ["alpha.txt"])

        status, body = self.api_post("/search_files", {"query": "target"})
        self.assertEqual(status, 200)
        names = sorted(item["name"] for item in body["files"])
        self.assertEqual(names, ["beta.txt"])

    def test_update_file(self) -> None:
        self.api_post("/create_file", {"name": "note2", "content": "old"})

        status, body = self.api_post("/update_file", {"name": "note2.txt", "content": "new"})
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "updated")

        status, body = self.api_get("/list_files")
        self.assertEqual(status, 200)
        self.assertEqual(body["files"][0]["content"], "new")

    def test_delete_file(self) -> None:
        self.api_post("/create_file", {"name": "note3", "content": "to delete"})

        status, body = self.api_post("/delete_file", {"name": "note3"})
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "deleted")

        status, body = self.api_get("/list_files")
        self.assertEqual(status, 200)
        self.assertEqual(body["files"], [])

    def test_reject_duplicate_create(self) -> None:
        self.api_post("/create_file", {"name": "dupe", "content": "a"})
        status, body = self.api_post("/create_file", {"name": "dupe", "content": "b"})
        self.assertEqual(status, 400)
        self.assertIn("error", body)


if __name__ == "__main__":
    unittest.main()
