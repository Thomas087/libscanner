"""
Web scraping module for extracting data from government websites.
Contains only the web scraping, HTTP requests, and HTML parsing functionality.
"""

from __future__ import annotations

import io
import logging
import os
import random
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin

import PyPDF2
import fitz  # PyMuPDF
import requests
import sys
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

@dataclass(frozen=True)
class ScraperConfig:
    max_redirects: int = 5
    max_pdf_bytes: int = 15 * 1024 * 1024  # 15MB
    request_timeout: int = 30
    head_timeout: int = 15
    max_retries: int = 3
    icpe_pdf_cap: int = 5
    cleanup_window_days: int = 30
    page_step: int = 10
    max_offset: int = 1000
    cache_ttl_seconds: int = 600  # 10 minutes
    db_batch_size: int = 500  # Batch size for database operations
    cache_max_memory_mb: int = 100  # Maximum cache memory in MB
    cache_max_items: int = 512  # Maximum number of cached items


CONFIG = ScraperConfig()

# ------------------------------------------------------------------------------
# User-Agent handling
# ------------------------------------------------------------------------------

# Try to import fake-useragent for better user agent rotation
try:
    from fake_useragent import UserAgent

    FAKE_USERAGENT_AVAILABLE = True
except Exception:
    FAKE_USERAGENT_AVAILABLE = False

USER_AGENTS: Tuple[str, ...] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
)


def get_random_user_agent() -> str:
    if FAKE_USERAGENT_AVAILABLE:
        try:
            return UserAgent().random
        except Exception as e:
            logger.debug(f"fake-useragent failed, using static list: {e}")
    return random.choice(USER_AGENTS)


def get_headers() -> Dict[str, str]:
    return {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }


def configure_proxy_env() -> Dict[str, str]:
    http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    proxies = {}
    if http_proxy:
        proxies["http"] = http_proxy
    if https_proxy:
        proxies["https"] = https_proxy
    return proxies


# ------------------------------------------------------------------------------
# Requester with mounted retries
# ------------------------------------------------------------------------------

class Requester:
    def __init__(self, session: Optional[requests.Session] = None):
        self.s = session or requests.Session()
        self.s.max_redirects = CONFIG.max_redirects
        self.mount_retries()
        proxies = configure_proxy_env()
        if proxies:
            self.s.proxies.update(proxies)

    def mount_retries(self) -> None:
        retry = Retry(
            total=CONFIG.max_retries,
            backoff_factor=1.0,  # exponential-ish backoff via urllib3
            status_forcelist=[408, 429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        self.s.mount("http://", adapter)
        self.s.mount("https://", adapter)

    def update_headers(self) -> None:
        self.s.headers.update(get_headers())

    def get(self, url: str, timeout: Optional[int] = None) -> requests.Response:
        # brief jitter even on first attempt to avoid bursty patterns
        time.sleep(random.uniform(0.3, 1.2))
        self.update_headers()
        resp = self.s.get(url, timeout=timeout or CONFIG.request_timeout)
        # If urllib3 didn't raise, explicitly raise for non-2xx so caller can decide
        resp.raise_for_status()
        return resp

    def head(self, url: str, timeout: Optional[int] = None) -> requests.Response:
        self.update_headers()
        return self.s.head(url, allow_redirects=True, timeout=timeout or CONFIG.head_timeout)

    def reset(self) -> None:
        try:
            self.s.close()
        except Exception:
            pass
        self.__init__(None)  # re-init fresh session


# Single module-level requester (can be swapped in tests)
_requester = Requester()

# ------------------------------------------------------------------------------
# Memory-aware TTL cache decorator
# ------------------------------------------------------------------------------

def ttl_cache(seconds: int = CONFIG.cache_ttl_seconds, maxsize: int = CONFIG.cache_max_items):
    """
    Memory-aware TTL cache that evicts based on both time, count, and memory size.

    Improvements:
    - Tracks approximate memory usage
    - Evicts LRU items when memory limit is reached
    - Evicts expired items proactively
    - More aggressive cleanup to prevent memory bloat
    """
    def deco(fn):
        cache: Dict[Any, Tuple[float, Any, int]] = {}  # key -> (timestamp, value, size_bytes)
        order: List[Any] = []  # LRU order
        total_size_bytes: int = 0
        max_size_bytes = CONFIG.cache_max_memory_mb * 1024 * 1024

        def get_size(obj: Any) -> int:
            """Estimate object size in bytes."""
            try:
                return sys.getsizeof(obj)
            except Exception:
                # Fallback for objects that don't support getsizeof
                if isinstance(obj, str):
                    return len(obj.encode('utf-8'))
                return 1024  # Conservative default

        def evict_oldest():
            """Evict the oldest item from cache."""
            nonlocal total_size_bytes
            if order:
                oldest = order.pop(0)
                if oldest in cache:
                    _, _, size = cache.pop(oldest)
                    total_size_bytes -= size

        def evict_expired(now: float):
            """Proactively evict all expired items."""
            nonlocal total_size_bytes
            expired_keys = [k for k, (ts, _, _) in cache.items() if now - ts >= seconds]
            for key in expired_keys:
                if key in cache:
                    _, _, size = cache.pop(key)
                    total_size_bytes -= size
                if key in order:
                    order.remove(key)

        def wrapper(*args):
            nonlocal total_size_bytes

            now = time.time()
            key = args

            # Proactively clean expired items every 10 calls
            if len(cache) % 10 == 0:
                evict_expired(now)

            # Check for cache hit
            hit = cache.get(key)
            if hit is not None:
                timestamp, value, _ = hit
                if now - timestamp < seconds:
                    # Move to end of LRU order
                    if key in order:
                        order.remove(key)
                    order.append(key)
                    return value
                else:
                    # Expired, remove it
                    _, _, size = cache.pop(key)
                    total_size_bytes -= size
                    if key in order:
                        order.remove(key)

            # Cache miss - compute value
            value = fn(*args)
            value_size = get_size(value)

            # Evict items if over memory limit
            while total_size_bytes + value_size > max_size_bytes and order:
                evict_oldest()

            # Evict items if over count limit
            while len(order) >= maxsize and order:
                evict_oldest()

            # Add to cache
            cache[key] = (now, value, value_size)
            order.append(key)
            total_size_bytes += value_size

            logger.debug(f"Cache stats: {len(cache)} items, {total_size_bytes / 1024 / 1024:.2f}MB")

            return value

        def cache_info():
            """Get cache statistics."""
            return {
                'size': len(cache),
                'memory_mb': total_size_bytes / 1024 / 1024,
                'max_items': maxsize,
                'max_memory_mb': CONFIG.cache_max_memory_mb
            }

        wrapper.cache_clear = lambda: (cache.clear(), order.clear())
        wrapper.cache_info = cache_info
        return wrapper

    return deco


# ------------------------------------------------------------------------------
# HTML parsing & URL helpers
# ------------------------------------------------------------------------------

def first_text(soup: BeautifulSoup, *selectors: str) -> str:
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            return el.get_text(strip=True)
    return ""


def first_attr(soup: BeautifulSoup, selector: str, attr: str) -> str:
    el = soup.select_one(selector)
    return el.get(attr, "") if el else ""


def absolutize(href: str, domain: Optional[str]) -> str:
    if not href:
        return ""
    if href.startswith("http"):
        return href
    base = f"https://www.{domain}" if domain else ""
    return urljoin(base + "/", href)


# ------------------------------------------------------------------------------
# Data shape for cards
# ------------------------------------------------------------------------------

@dataclass
class ScrapedCard:
    title: str
    link: str
    description: str = ""
    date_label: Optional[str] = None
    metadata: Optional[Dict[str, List[str]]] = None
    html_content: Optional[str] = None


# ------------------------------------------------------------------------------
# Fetching & extraction (with TTL caches)
# ------------------------------------------------------------------------------

def head_pdf_ok(url: str) -> bool:
    """HEAD probe for PDF content-type and reasonable size."""
    try:
        r = _requester.head(url, timeout=CONFIG.head_timeout)
        ct = (r.headers.get("Content-Type") or "").lower()
        cl = r.headers.get("Content-Length")
        if "pdf" not in ct:
            logger.debug(f"HEAD indicates non-PDF ({ct}): {url}")
            return False
        if cl and cl.isdigit() and int(cl) > CONFIG.max_pdf_bytes:
            logger.info(f"Skip large PDF (HEAD Content-Length {cl} bytes): {url}")
            return False
        return True
    except Exception as e:
        # Some servers block HEAD; be permissive and rely on body-size check later
        logger.debug(f"HEAD failed for {url}: {e}")
        return True

@ttl_cache(seconds=CONFIG.cache_ttl_seconds)
def fetch_page_soup(url: str) -> BeautifulSoup:
    rsp = _requester.get(url, timeout=CONFIG.request_timeout)
    return BeautifulSoup(rsp.content, "html.parser")


@ttl_cache(seconds=CONFIG.cache_ttl_seconds)
def fetch_page_text(url: str) -> str:
    soup = fetch_page_soup(url)
    return soup.get_text()


def extract_pdf_links_from_page(url: str) -> List[str]:
    """Extract all PDF links from a webpage (cross-domain allowed by request)."""
    try:
        soup = fetch_page_soup(url)
        links: List[str] = []
        for a in soup.find_all("a", href=True):
            href = urljoin(url, a["href"])
            if href.lower().endswith(".pdf") or "pdf" in href.lower():
                links.append(href)
        logger.debug(f"Found {len(links)} PDF links on {url}")
        return links
    except Exception as e:
        logger.error(f"Error extracting PDF links from {url}: {e}")
        return []


@ttl_cache(seconds=CONFIG.cache_ttl_seconds)
def extract_text_from_pdf(pdf_url: str) -> str:
    """Extract text from PDF via PyMuPDF; fallback to PyPDF2. Enforces size limits."""
    try:
        if not head_pdf_ok(pdf_url):
            return ""

        resp = _requester.get(pdf_url, timeout=CONFIG.request_timeout)
        content = resp.content or b""
        if len(content) > CONFIG.max_pdf_bytes:
            logger.info(f"Skip large PDF body ({len(content)} bytes): {pdf_url}")
            return ""

        pdf_file = io.BytesIO(content)

        # Try PyMuPDF first
        try:
            doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
            texts: List[str] = []
            for i in range(doc.page_count):
                try:
                    texts.append(doc[i].get_text())
                except Exception as page_error:
                    logger.debug(f"Error extracting page {i} from {pdf_url}: {page_error}")
                    # Continue with other pages even if one fails
                    continue
            doc.close()
            return "\n".join(texts)
        except Exception as fitz_error:
            logger.warning(f"PyMuPDF failed for {pdf_url}, fallback to PyPDF2: {fitz_error}")
            pdf_file.seek(0)
            try:
                reader = PyPDF2.PdfReader(pdf_file)
                texts: List[str] = []
                for i in range(len(reader.pages)):
                    try:
                        page = reader.pages[i]
                        texts.append(page.extract_text() or "")
                    except Exception as page_error:
                        logger.debug(f"Error extracting page {i} with PyPDF2: {page_error}")
                        continue
                return "\n".join(texts)
            except Exception as pypdf_error:
                logger.error(f"Both PyMuPDF and PyPDF2 failed for {pdf_url}: {pypdf_error}")
                return ""

    except Exception as e:
        logger.error(f"Error extracting text from PDF {pdf_url}: {e}")
        return ""


# ------------------------------------------------------------------------------
# Card extraction
# ------------------------------------------------------------------------------

def extract_card_data(card_element, domain: Optional[str] = None) -> Optional[ScrapedCard]:
    try:
        # Title
        title = first_text(card_element, "h3", "h2", "h1")
        # Link
        href = first_attr(card_element, "a", "href")
        link = absolutize(href, domain)
        # Desc
        desc = first_text(card_element, "p", ".fr-card__desc")
        # Date label (raw)
        date_label = first_text(card_element, "time", "span.date")

        # Metadata buckets (optional)
        metadata: Dict[str, List[str]] = {}
        for cls in ("fr-card__title", "fr-card__content", "fr-card__detail"):
            els = card_element.find_all(class_=cls)
            if els:
                metadata[cls] = [el.get_text(strip=True) for el in els]
        if not title and not link:
            return None

        html_content = str(card_element)
        return ScrapedCard(
            title=title or "",
            link=link or "",
            description=desc or "",
            date_label=date_label or None,
            metadata=metadata or None,
            html_content=html_content,
        )
    except Exception as e:
        logger.error(f"Error extracting card data: {e}")
        return None


# ------------------------------------------------------------------------------
# Scraping flows
# ------------------------------------------------------------------------------

def build_search_url(domain: str, keyword: str, offset: int = 0) -> str:
    if offset > 0:
        return f"https://www.{domain}/contenu/recherche/(offset)/{offset}/(searchtext)/{keyword}?SearchText={keyword}"
    return f"https://www.{domain}/contenu/recherche/(searchtext)/{keyword}?SearchText={keyword}"


def scrape_government_site(domain: str, keyword: str, offset: int = 0) -> List[ScrapedCard]:
    """
    Scrape a single search results page and return cards.
    """
    try:
        url = build_search_url(domain, keyword, offset)
        logger.info(f"Scraping page at offset {offset}: {url}")
        soup = fetch_page_soup(url)
        cards = soup.find_all("div", class_="fr-card")
        logger.debug(f"Found {len(cards)} card elements on page")
        results: List[ScrapedCard] = []
        for card in cards:
            sc = extract_card_data(card, domain)
            if sc:
                results.append(sc)
        logger.info(f"Extracted {len(results)} valid cards from offset {offset}")
        return results
    except requests.RequestException as e:
        logger.error(f"Request error while scraping {domain} offset {offset}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error while scraping {domain} offset {offset}: {e}")
        return []


def iterate_search_pages(
    domain: str, keyword: str, *, start: int = 0, step: int = CONFIG.page_step, limit: int = CONFIG.max_offset
) -> Iterable[List[ScrapedCard]]:
    """
    Generator that yields results page-by-page until exhaustion or limit.
    """
    logger.info(f"Starting pagination for {domain} with keyword '{keyword}' (start={start}, step={step}, limit={limit})")
    offset = start
    page_count = 0
    while offset <= limit:
        page = scrape_government_site(domain, keyword, offset)
        if not page:
            logger.info(f"No more results found at offset {offset}, stopping pagination")
            break
        yield page
        offset += step
        page_count += 1
        if page_count % 5 == 0:
            # Periodic session reset to reduce detection risk
            logger.debug(f"Resetting session after {page_count} pages")
            _requester.reset()

    logger.info(f"Pagination complete: scraped {page_count} pages for {domain}")


def scrape_url(domain: str, keyword: str, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Backwards-compatible wrapper (returns dicts).
    """
    cards = scrape_government_site(domain, keyword, offset)
    return [card.__dict__ for card in cards]