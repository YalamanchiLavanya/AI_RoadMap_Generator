"""Check that recommended links work before they are presented as curated.

The model is told never to invent URLs, but it can still be wrong. Every link in a
roadmap is checked here, and only links that actually answered are shown as
verified. Everything else is labelled honestly.

Because the server makes these requests, links that point at private, loopback, or
link-local addresses are refused (including after a redirect).
"""
from __future__ import annotations

import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

VERIFIED = "verified"      # the page answered with a 2xx/3xx status
BROKEN = "broken"          # the page answered 404/410 (or another clear client error)
UNVERIFIED = "unverified"  # timeout, DNS failure, bot-blocking, 5xx - unknown
INVALID = "invalid"        # not a usable http(s) URL
NO_LINK = "no_link"        # the model gave no URL

_USER_AGENT = "Mozilla/5.0 (compatible; RoadmapLinkChecker/1.0)"
# Statuses where the site is probably just refusing automated checks.
_BLOCKED_CODES = {401, 403, 407, 408, 429, 451, 999}


@dataclass(frozen=True)
class LinkResult:
    url: str
    status: str
    detail: str = ""
    code: int | None = None

    @property
    def verified(self) -> bool:
        return self.status == VERIFIED


def validate_url(url: str, *, allow_private: bool = False) -> str | None:
    """Return an error message when the URL must not be fetched, else None."""
    parsed = urlparse(url or "")
    if parsed.scheme not in ("http", "https"):
        return "only http and https links are supported"
    host = parsed.hostname
    if not host:
        return "the link has no host name"
    if allow_private:
        return None
    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror:
            return None  # let the real request fail and be reported as "unverified"
        addresses = [ipaddress.ip_address(info[4][0]) for info in infos]
    for address in addresses:
        mapped = getattr(address, "ipv4_mapped", None)
        address = mapped or address
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
            or address.is_multicast
            or address.is_unspecified
        ):
            return "the link points to a private or local address"
    return None


class _SafeRedirectHandler(HTTPRedirectHandler):
    def __init__(self, allow_private: bool):
        super().__init__()
        self._allow_private = allow_private

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        problem = validate_url(newurl, allow_private=self._allow_private)
        if problem:
            raise URLError(f"redirect blocked: {problem}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _classify_http(url: str, code: int) -> LinkResult:
    if 200 <= code < 400:
        return LinkResult(url, VERIFIED, f"HTTP {code}", code)
    if code in (404, 410):
        return LinkResult(url, BROKEN, f"HTTP {code} - page not found", code)
    if code in _BLOCKED_CODES:
        return LinkResult(url, UNVERIFIED, f"HTTP {code} - the site may block automated checks", code)
    if code >= 500:
        return LinkResult(url, UNVERIFIED, f"HTTP {code} - server error", code)
    return LinkResult(url, BROKEN, f"HTTP {code}", code)


def check_url(url: str, *, timeout: float = 6.0, allow_private: bool = False, opener=None) -> LinkResult:
    url = (url or "").strip()
    if not url:
        return LinkResult("", NO_LINK, "no link provided")
    problem = validate_url(url, allow_private=allow_private)
    if problem:
        return LinkResult(url, INVALID, problem)

    opener = opener or build_opener(_SafeRedirectHandler(allow_private))
    last_detail = ""
    for method in ("HEAD", "GET"):
        request = Request(url, method=method, headers={"User-Agent": _USER_AGENT, "Accept": "*/*"})
        try:
            with opener.open(request, timeout=timeout) as response:
                code = getattr(response, "status", None) or response.getcode()
                return _classify_http(url, int(code))
        except HTTPError as exc:
            if method == "HEAD" and exc.code in (400, 403, 405, 501):
                last_detail = f"HTTP {exc.code} on HEAD"
                continue  # many sites reject HEAD; try a normal GET
            return _classify_http(url, exc.code)
        except URLError as exc:
            reason = exc.reason
            if isinstance(reason, socket.gaierror):
                return LinkResult(url, UNVERIFIED, "domain could not be resolved (or you are offline)")
            if isinstance(reason, (TimeoutError, socket.timeout)):
                return LinkResult(url, UNVERIFIED, "timed out")
            return LinkResult(url, UNVERIFIED, str(reason)[:120])
        except (TimeoutError, socket.timeout):
            return LinkResult(url, UNVERIFIED, "timed out")
        except Exception as exc:  # noqa: BLE001 - never let one bad link break the app
            return LinkResult(url, UNVERIFIED, f"{type(exc).__name__}: {str(exc)[:100]}")
    return LinkResult(url, UNVERIFIED, last_detail or "could not be checked")


def check_links(
    urls,
    *,
    timeout: float = 6.0,
    max_workers: int = 8,
    max_urls: int = 40,
    allow_private: bool = False,
    fetch: Callable[[str], LinkResult] | None = None,
) -> dict[str, LinkResult]:
    """Check many links in parallel. Returns {url: LinkResult} for every unique URL."""
    unique: list[str] = []
    for url in urls:
        url = (url or "").strip() if isinstance(url, str) else ""
        if url and url not in unique:
            unique.append(url)

    to_check, skipped = unique[:max_urls], unique[max_urls:]
    fetch = fetch or (lambda link: check_url(link, timeout=timeout, allow_private=allow_private))
    results: dict[str, LinkResult] = {}
    if to_check:
        with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(to_check)))) as pool:
            for url, result in zip(to_check, pool.map(fetch, to_check)):
                results[url] = result
    for url in skipped:
        results[url] = LinkResult(url, UNVERIFIED, "not checked (too many links)")
    return results


def resource_cells(resource: dict, results: dict[str, LinkResult] | None) -> tuple[str, str]:
    """Return (resource_cell, status_cell) as Markdown for one resource.

    Only a verified link is clickable. Unverified links are shown as plain code text
    so a learner is never nudged toward a link nobody has confirmed.
    """
    title = str(resource.get("title") or "Untitled resource").strip()
    url = (resource.get("url") or "").strip() if isinstance(resource.get("url"), str) else ""
    if not url:
        return title, "⚠️ No link given - search for the exact title"
    result = (results or {}).get(url)
    if result is None:
        return title, f"⚠️ Not checked: `{url}`"
    if result.status == VERIFIED:
        return f"[{title}]({url})", f"✅ Verified ({result.detail})"
    if result.status == BROKEN:
        return title, f"❌ Link is broken ({result.detail}) - search for the exact title"
    if result.status == INVALID:
        return title, f"❌ Invalid link ({result.detail}) - search for the exact title"
    return title, f"⚠️ Could not verify ({result.detail}): `{url}`"
