"""Regression coverage for browser downloads and direct file clients."""
import os
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from jinja2 import FileSystemLoader

import app as yodelkey


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        directory = self.stack.enter_context(tempfile.TemporaryDirectory())
        original_cwd = Path.cwd()
        os.chdir(directory)
        self.stack.callback(os.chdir, original_cwd)
        templates = Path(yodelkey.__file__).parent / "templates"
        self.stack.enter_context(patch.object(yodelkey.app, "root_path", directory))
        self.stack.enter_context(patch.object(
            yodelkey.app, "jinja_loader", FileSystemLoader(templates),
        ))
        self.stack.enter_context(patch.dict(yodelkey.items, {}, clear=True))
        self.stack.enter_context(patch.dict(yodelkey.word_pools, {
            name: list(pool) for name, pool in yodelkey.word_pools.items()
        }))
        self.client = yodelkey.app.test_client()
        self.browser = {"User-Agent": "Mozilla/5.0"}

    def upload(self, query=""):
        response = self.client.put("/example.txt" + query, data=b"file contents\x00\xff")
        self.assertEqual(response.status_code, 200)
        return response.text.strip()

    def assert_file(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"file contents\x00\xff")
        self.assertIn("attachment; filename=example.txt", response.headers["Content-Disposition"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        response.close()

    def test_curl_receives_file_over_http_and_https(self):
        key = self.upload()
        for scheme in ("http", "https"):
            with self.subTest(scheme=scheme):
                self.assert_file(self.client.get(
                    f"/{key}", base_url=f"{scheme}://localhost",
                    headers={"User-Agent": "curl/8.0"},
                ))
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_browser_receives_page_then_worker_receives_file(self):
        key = self.upload()
        response = self.client.get(f"/{key}", headers=self.browser)
        self.assertEqual(response.status_code, 200)
        self.assertIn("/static/download.js", response.text)
        self.assertIn("/static/download-worker.js", response.text)
        self.assertNotIn("Content-Disposition", response.headers)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assert_file(self.client.get(f"/{key}?download=1", headers=self.browser))

    def test_password_required_for_page_and_file(self):
        key = self.upload("?pass=a%26b")
        for query in ("", "?download=1", "?pass=wrong&download=1"):
            with self.subTest(query=query):
                self.assertEqual(self.client.get(
                    f"/{key}{query}", headers=self.browser,
                ).status_code, 403)
        for alias in ("pass", "code", "password"):
            with self.subTest(alias=alias):
                response = self.client.get(
                    f"/{key}?{alias}=a%26b&download=0", headers=self.browser,
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn(f"{alias}=a%26b&amp;download=1", response.text)
                self.assert_file(self.client.get(
                    f"/{key}?{alias}=a%26b&download=1", headers=self.browser,
                ))

    def test_burn_file_survives_page_and_failed_password_until_fetch(self):
        key = self.upload("?burn=1&pass=secret")
        item = yodelkey.items[key]
        path = Path("uploads") / str(item.uuid)
        self.client.get(f"/{key}?pass=secret", headers=self.browser)
        denied = self.client.get(f"/{key}?download=1", headers=self.browser)
        self.assertEqual(denied.status_code, 403)
        self.assertIn(key, yodelkey.items)
        self.assertTrue(path.exists())
        self.assert_file(self.client.get(
            f"/{key}?pass=secret&download=1", headers=self.browser,
        ))
        self.assertNotIn(key, yodelkey.items)
        self.assertFalse(path.exists())
        self.assertEqual(self.client.get(f"/{key}?download=1").location, "/404")

    def test_curl_burn_file_is_consumed_directly(self):
        key = self.upload("?burn=1")
        self.assert_file(self.client.get(f"/{key}"))
        self.assertNotIn(key, yodelkey.items)

    def test_text_and_url_browser_responses_are_unchanged(self):
        for content in ("hello", "https://example.com"):
            key = self.client.get("/create", query_string={"content": content}).text.strip()
            response = self.client.get(f"/{key}", headers=self.browser)
            if content.startswith("https:"):
                self.assertEqual(response.location, content)
            else:
                self.assertEqual(response.text, content)
                self.assertEqual(response.content_type, "text/plain")


if __name__ == "__main__":
    unittest.main()
