"""
Scraper module for extracting data from government websites.
Clean, DRY, and efficient version:
- Centralized config
- Requester class with mounted retries (urllib3 Retry)
- Precompiled constants/regex
- Small parsing/url helpers
- Dataclass for scraped cards
- TTL caches for fetched page/PDF text
- Declarative ICPE pipeline
- Cross-domain PDF lookups preserved (by request)
- DB prefetch + no-op update skips
- Lightweight negative keyword cache
"""

from __future__ import annotations

import io
import logging
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import PyPDF2
import fitz  # PyMuPDF
import requests
from bs4 import BeautifulSoup
from django.utils import timezone
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .constants import get_prefecture_by_domain
from .models import GovernmentDocument, NegativeKeyword

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
# TTL cache decorator (simple, dependency-free)
# ------------------------------------------------------------------------------

def ttl_cache(seconds: int = CONFIG.cache_ttl_seconds, maxsize: int = 1024):
    def deco(fn):
        cache: Dict[Any, Tuple[float, Any]] = {}
        order: List[Any] = []

        def wrapper(*args):
            now = time.time()
            key = args
            hit = cache.get(key)
            if hit is not None and now - hit[0] < seconds:
                return hit[1]
            value = fn(*args)
            cache[key] = (now, value)
            order.append(key)
            if len(order) > maxsize:
                oldest = order.pop(0)
                cache.pop(oldest, None)
            return value

        wrapper.cache_clear = lambda: (cache.clear(), order.clear())
        return wrapper

    return deco


# ------------------------------------------------------------------------------
# Precompiled constants & regex
# ------------------------------------------------------------------------------

ICPE_KEYWORDS: Tuple[str, ...] = tuple(
    kw.lower()
    for kw in (
        "icpe",
        "installations classées",
        "installation classée",
        "déclaration icpe",
        "autorisation environnementale",
        "régime d'autorisation",
        "régime d'enregistrement",
        "régime de déclaration",
        "rubriques des activités",
        "nomenclature des installations",
        "code de l'environnement",
        "déclaration initiale dicpe",
        "dicpe",
    )
)

import re

DATE_PATTERNS: Tuple[re.Pattern, ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"Mis à jour le (\d{1,2})/(\d{1,2})/(\d{4})",
        r"Publié le (\d{1,2})/(\d{1,2})/(\d{4})",
        r"Le (\d{1,2})/(\d{1,2})/(\d{4})",
    )
)

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
# Keyword checks & date parse
# ------------------------------------------------------------------------------

def contains_icpe_keywords(text: Optional[str]) -> bool:
    if not text:
        return False
    t = text.lower()
    return any(k in t for k in ICPE_KEYWORDS)


def parse_date_from_detail(detail_text: str) -> datetime:
    for pat in DATE_PATTERNS:
        m = pat.search(detail_text or "")
        if m:
            day, month, year = m.groups()
            try:
                return datetime(
                    int(year), int(month), int(day), tzinfo=timezone.get_current_timezone()
                )
            except Exception:
                # fall through to now()
                break
    return timezone.now()


# ------------------------------------------------------------------------------
# Negative keyword caching
# ------------------------------------------------------------------------------

from functools import lru_cache


@lru_cache(maxsize=1)
def _negative_keywords_lower() -> List[str]:
    try:
        return [nk.keyword.lower() for nk in NegativeKeyword.objects.all()]
    except Exception as e:
        logger.error(f"Error loading negative keywords: {e}")
        return []


def refresh_negative_keywords_cache() -> None:
    _negative_keywords_lower.cache_clear()


def contains_negative_keywords(title: str, description: str) -> bool:
    text = f"{title} {description}".lower()
    for kw in _negative_keywords_lower():
        if kw and kw in text:
            return True
    return False


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
def fetch_page_text(url: str) -> str:
    rsp = _requester.get(url, timeout=CONFIG.request_timeout)
    return BeautifulSoup(rsp.content, "html.parser").get_text()


def extract_pdf_links_from_page(url: str) -> List[str]:
    """Extract all PDF links from a webpage (cross-domain allowed by request)."""
    try:
        rsp = _requester.get(url, timeout=CONFIG.request_timeout)
        soup = BeautifulSoup(rsp.content, "html.parser")
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


def check_page_for_icpe(url: str) -> bool:
    try:
        text = fetch_page_text(url)
        return contains_icpe_keywords(text)
    except Exception as e:
        logger.error(f"Error checking page for ICPE at {url}: {e}")
        return False


def check_pdfs_for_icpe(pdf_urls: List[str]) -> bool:
    for u in pdf_urls:
        try:
            text = extract_text_from_pdf(u)
            if text and contains_icpe_keywords(text):
                return True
        except Exception as e:
            logger.error(f"Error checking PDF {u} for ICPE: {e}")
    return False


# ------------------------------------------------------------------------------
# ICPE pipeline (declarative)
# ------------------------------------------------------------------------------

def icpe_flag_for_item(title: str, description: str, link: Optional[str], domain: Optional[str]) -> bool:
    """Cheap -> deeper ICPE detection with short-circuits and capped PDF checks."""
    if contains_icpe_keywords(f"{title} {description}"):
        return True
    if not link:
        return False

    parsed = urlparse(link)
    same_domain = bool(parsed.netloc and domain and parsed.netloc.endswith(domain))

    if same_domain and check_page_for_icpe(link):
        return True

    pdf_links = extract_pdf_links_from_page(link)
    if not pdf_links:
        return False

    # Cap to first N PDFs to avoid heavy scans
    return check_pdfs_for_icpe(pdf_links[: CONFIG.icpe_pdf_cap])


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
# Persistence
# ------------------------------------------------------------------------------

def save_to_database(scraped_cards: List[ScrapedCard], domain: str, *, now=timezone.now) -> int:
    """
    Persist scraped items with minimal DB churn:
    - Preload existing by link
    - Skip no-op updates
    - Negative keyword filtering
    """
    if not scraped_cards:
        return 0

    prefecture_info = get_prefecture_by_domain(domain)
    pref_name = prefecture_info["name"] if prefecture_info else None
    pref_code = prefecture_info["code"] if prefecture_info else None
    region_name = prefecture_info["region"] if prefecture_info else None

    links = [c.link for c in scraped_cards if c.link]
    existing_by_link = {d.link: d for d in GovernmentDocument.objects.filter(link__in=links)}

    saved = 0
    for card in scraped_cards:
        try:
            # Date from metadata if present
            date_updated = now()
            detail_text = None
            if card.metadata and "fr-card__detail" in card.metadata:
                detail_text = " ".join(card.metadata["fr-card__detail"])
                date_updated = parse_date_from_detail(detail_text)

            if contains_negative_keywords(card.title, card.description):
                existing = existing_by_link.get(card.link)
                if existing:
                    existing.delete()
                    existing_by_link.pop(card.link, None)
                continue

            is_icpe = icpe_flag_for_item(card.title, card.description, card.link, domain)

            existing = existing_by_link.get(card.link)
            if existing:
                changed = (
                    existing.title != card.title
                    or (existing.description or "") != (card.description or "")
                    or existing.date_updated != date_updated
                    or existing.is_icpe != is_icpe
                    or (pref_name and existing.prefecture_name != pref_name)
                    or (pref_code and existing.prefecture_code != pref_code)
                    or (region_name and existing.region_name != region_name)
                )
                if not changed:
                    continue
                existing.title = card.title
                existing.description = card.description
                existing.date_updated = date_updated
                existing.is_icpe = is_icpe
                if pref_name:
                    existing.prefecture_name = pref_name
                if pref_code:
                    existing.prefecture_code = pref_code
                if region_name:
                    existing.region_name = region_name
                existing.save()
                saved += 1
            else:
                doc = GovernmentDocument.objects.create(
                    title=card.title,
                    description=card.description,
                    link=card.link,
                    date_updated=date_updated,
                    prefecture_name=pref_name,
                    prefecture_code=pref_code,
                    region_name=region_name,
                    is_icpe=is_icpe,
                )
                existing_by_link[card.link] = doc
                saved += 1

        except Exception as e:
            logger.error(f"Error saving item '{card.title}' to database: {e}")
            continue

    return saved


def remove_documents_with_negative_keywords(days: int = CONFIG.cleanup_window_days) -> int:
    removed = 0
    try:
        cutoff = timezone.now() - timedelta(days=days)
        for d in GovernmentDocument.objects.filter(date_updated__gte=cutoff):
            if contains_negative_keywords(d.title, d.description or ""):
                d.delete()
                removed += 1
    except Exception as e:
        logger.error(f"Error during negative keyword cleanup: {e}")
    return removed


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
        rsp = _requester.get(url, timeout=CONFIG.request_timeout)
        soup = BeautifulSoup(rsp.content, "html.parser")
        cards = soup.find_all("div", class_="fr-card")
        results: List[ScrapedCard] = []
        for card in cards:
            sc = extract_card_data(card, domain)
            if sc:
                results.append(sc)
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
    offset = start
    page_count = 0
    while offset <= limit:
        page = scrape_government_site(domain, keyword, offset)
        if not page:
            break
        yield page
        offset += step
        page_count += 1
        if page_count % 5 == 0:
            # Periodic session reset to reduce detection risk
            _requester.reset()


def scrape_url(domain: str, keyword: str, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Backwards-compatible wrapper (returns dicts).
    """
    cards = scrape_government_site(domain, keyword, offset)
    return [card.__dict__ for card in cards]


def scrape_all_results(domain: str, keyword: str) -> List[Dict[str, Any]]:
    """
    Scrape all pages, persist results, run lightweight cleanup, and return all items (as dicts).
    """
    all_cards: List[ScrapedCard] = []
    for page in iterate_search_pages(domain, keyword):
        all_cards.extend(page)

    if all_cards:
        saved_count = save_to_database(all_cards, domain)
        logger.info(f"Saved {saved_count} items to database.")

    removed_count = remove_documents_with_negative_keywords(days=CONFIG.cleanup_window_days)
    if removed_count:
        logger.info(f"Removed {removed_count} negative-keyword documents (last {CONFIG.cleanup_window_days} days).")

    return [card.__dict__ for card in all_cards]


def scrape_generic(url: str) -> List[Dict[str, Any]]:
    """
    Generic scraper for any URL (no DB save, no prefecture context).
    Returns list of dicts for compatibility.
    """
    try:
        rsp = _requester.get(url, timeout=CONFIG.request_timeout)
        soup = BeautifulSoup(rsp.content, "html.parser")
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "") if parsed.netloc else None
        fr_cards = soup.find_all("div", class_="fr-card")
        results: List[ScrapedCard] = []
        for card in fr_cards:
            sc = extract_card_data(card, domain)
            if sc:
                results.append(sc)
        return [c.__dict__ for c in results]
    except Exception as e:
        logger.error(f"Error while scraping {url}: {e}")
        return []
