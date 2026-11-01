"""Link verification (against a local test server) and how links are presented."""
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from tests.helpers import clone, make_plan

import link_checker as lc
from roadmap_engine import collect_urls, plan_to_markdown


class Handler(BaseHTTPRequestHandler):
    def _respond(self):
        path = self.path
        if path == "/ok":
            self.send_response(200)
        elif path == "/missing":
            self.send_response(404)
        elif path == "/no-head":
            self.send_response(405 if self.command == "HEAD" else 200)
        elif path == "/blocked":
            self.send_response(403)
        elif path == "/error":
            self.send_response(503)
        elif path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/ok")
        else:
            self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    do_HEAD = do_GET = _respond

    def log_message(self, *args):  # keep test output quiet
        pass


class LocalServer:
    def __enter__(self):
        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()


class CheckUrl(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = LocalServer().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.__exit__()

    def check(self, path):
        return lc.check_url(self.ctx.base + path, allow_private=True, timeout=3)

    def test_working_page_is_verified(self):
        result = self.check("/ok")
        self.assertEqual((result.status, result.code), (lc.VERIFIED, 200))

    def test_redirect_to_a_working_page_is_verified(self):
        self.assertEqual(self.check("/redirect").status, lc.VERIFIED)

    def test_missing_page_is_broken(self):
        self.assertEqual(self.check("/missing").status, lc.BROKEN)

    def test_site_that_rejects_head_is_retried_with_get(self):
        self.assertEqual(self.check("/no-head").status, lc.VERIFIED)

    def test_bot_blocking_and_server_errors_are_unverified_not_broken(self):
        self.assertEqual(self.check("/blocked").status, lc.UNVERIFIED)
        self.assertEqual(self.check("/error").status, lc.UNVERIFIED)

    def test_unreachable_host_is_unverified(self):
        # port 9 on localhost is closed: connection refused
        result = lc.check_url("http://127.0.0.1:9/", allow_private=True, timeout=2)
        self.assertEqual(result.status, lc.UNVERIFIED)


class UrlSafety(unittest.TestCase):
    def test_private_and_local_addresses_are_refused_by_default(self):
        for url in (
            "http://127.0.0.1/", "http://10.0.0.5/",
            "http://169.254.169.254/latest/meta-data/", "http://192.168.1.1/", "http://[::1]/",
        ):
            with self.subTest(url=url):
                self.assertEqual(lc.check_url(url).status, lc.INVALID)

    def test_non_http_schemes_are_invalid(self):
        for url in ("ftp://example.com/file", "javascript:alert(1)", "file:///etc/passwd", "example.com"):
            with self.subTest(url=url):
                self.assertEqual(lc.check_url(url).status, lc.INVALID)

    def test_empty_link_is_reported_as_no_link(self):
        self.assertEqual(lc.check_url("").status, lc.NO_LINK)


class CheckLinks(unittest.TestCase):
    def test_duplicates_are_checked_once_and_the_cap_is_applied(self):
        seen = []

        def fake(url):
            seen.append(url)
            return lc.LinkResult(url, lc.VERIFIED, "HTTP 200", 200)

        urls = ["https://a.example/1", "https://a.example/1", "https://a.example/2", "https://a.example/3", None, ""]
        results = lc.check_links(urls, fetch=fake, max_urls=2)
        self.assertEqual(sorted(seen), ["https://a.example/1", "https://a.example/2"])
        self.assertEqual(results["https://a.example/3"].status, lc.UNVERIFIED)
        self.assertEqual(len(results), 3)


class Presentation(unittest.TestCase):
    def results_for(self, plan, statuses):
        urls = collect_urls(plan)
        return {u: lc.LinkResult(u, s, "HTTP 200" if s == lc.VERIFIED else "x") for u, s in zip(urls, statuses)}

    def test_only_verified_links_are_clickable_and_marked_verified(self):
        plan = make_plan(4, 8)
        results = self.results_for(plan, [lc.VERIFIED, lc.BROKEN, lc.UNVERIFIED, lc.INVALID])
        markdown = plan_to_markdown(plan, {"goal": "SQL"}, results, checked_on="1 Nov 2026")
        self.assertIn("[Resource 1](https://example.com/w1)", markdown)
        self.assertIn("✅ Verified", markdown)
        for n in (2, 3, 4):
            self.assertNotIn(f"](https://example.com/w{n})", markdown)
        self.assertIn("❌ Link is broken", markdown)
        self.assertIn("⚠️ Could not verify", markdown)
        self.assertIn("`https://example.com/w3`", markdown)
        self.assertIn("on 1 Nov 2026", markdown)

    def test_unchecked_links_are_never_presented_as_verified(self):
        markdown = plan_to_markdown(make_plan(4, 8), {"goal": "SQL"}, None)
        self.assertNotIn("✅ Verified", markdown)
        self.assertIn("Not checked", markdown)

    def test_resource_without_url_asks_the_learner_to_search(self):
        plan = make_plan(4, 8)
        plan["weeks"][0]["resources"][0]["url"] = None
        self.assertIn("No link given", plan_to_markdown(plan, {"goal": "SQL"}, {}))

    def test_pipes_in_text_do_not_break_tables(self):
        plan = make_plan(4, 8)
        plan["weeks"][0]["activities"][0]["task"] = "Compare A | B"
        self.assertIn("Compare A \\| B", plan_to_markdown(plan, {"goal": "SQL"}))

    def test_unrealistic_plan_shows_a_reality_check_with_the_achievable_outcome(self):
        markdown = plan_to_markdown(make_plan(4, 8, realistic=False), {"goal": "Become a Data Analyst"})
        self.assertIn("Reality check", markdown)
        self.assertIn("Write basic SQL queries for reports.", markdown)

    def test_document_page_references_are_rendered(self):
        plan = make_plan(4, 8)
        plan["reference"] = {"filename": "syllabus.pdf", "pages": [2, 3]}
        plan["weeks"][0]["source_pages"] = [2]
        markdown = plan_to_markdown(plan, {"goal": "SQL"})
        self.assertIn("syllabus.pdf, p. 2", markdown)
        self.assertIn("pages 2, 3", markdown)

    def test_display_and_download_use_the_same_text(self):
        plan = make_plan(4, 8)
        self.assertEqual(plan_to_markdown(clone(plan), {"goal": "SQL"}), plan_to_markdown(plan, {"goal": "SQL"}))


if __name__ == "__main__":
    unittest.main()
