"""
Scraper module for extracting data from government websites.
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import logging
from datetime import datetime
import re
import time
import random
from django.utils import timezone
from .models import GovernmentDocument, NegativeKeyword
from .constants import get_prefecture_by_domain
import io
import PyPDF2
import fitz  # PyMuPDF
from urllib.parse import urljoin

# Try to import fake-useragent for better user agent rotation
try:
    from fake_useragent import UserAgent
    FAKE_USERAGENT_AVAILABLE = True
except ImportError:
    FAKE_USERAGENT_AVAILABLE = False

logger = logging.getLogger(__name__)

# User agents for rotation to avoid detection
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0'
]

# Session for persistent connections and cookie handling
session = requests.Session()

# Configure session with better defaults
session.max_redirects = 5

def get_random_user_agent():
    """Get a random user agent from the list or fake-useragent library."""
    if FAKE_USERAGENT_AVAILABLE:
        try:
            ua = UserAgent()
            return ua.random
        except Exception as e:
            logger.warning(f"Failed to get user agent from fake-useragent: {e}")
            return random.choice(USER_AGENTS)
    else:
        return random.choice(USER_AGENTS)

def get_headers():
    """Get realistic browser headers."""
    return {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }

def make_request_with_retry(url: str, max_retries: int = 3, timeout: int = 30) -> requests.Response:
    """
    Make a request with retry logic and exponential backoff.
    
    Args:
        url (str): The URL to request
        max_retries (int): Maximum number of retries
        timeout (int): Request timeout in seconds
        
    Returns:
        requests.Response: The response object
        
    Raises:
        requests.RequestException: If all retries fail
    """
    for attempt in range(max_retries + 1):
        try:
            # Add random delay between requests to avoid rate limiting
            if attempt > 0:
                delay = random.uniform(1, 3) * (2 ** attempt)  # Exponential backoff
                logger.info(f"Waiting {delay:.2f} seconds before retry {attempt}")
                time.sleep(delay)
            else:
                # Random delay even for first attempt to avoid detection
                delay = get_request_delay()
                time.sleep(delay)
            
            # Update headers with new user agent for each attempt
            session.headers.update(get_headers())
            
            logger.info(f"Making request to {url} (attempt {attempt + 1}/{max_retries + 1})")
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            
            logger.info(f"Request successful - Status: {response.status_code}")
            return response
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on attempt {attempt + 1} for {url}")
            if attempt == max_retries:
                raise
        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection error on attempt {attempt + 1} for {url}")
            if attempt == max_retries:
                raise
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Rate limited
                logger.warning(f"Rate limited on attempt {attempt + 1} for {url}")
                if attempt == max_retries:
                    raise
                # Wait longer for rate limit
                time.sleep(random.uniform(5, 10))
            else:
                logger.error(f"HTTP error {e.response.status_code} on attempt {attempt + 1} for {url}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1} for {url}: {e}")
            if attempt == max_retries:
                raise
    
    raise requests.RequestException(f"All {max_retries + 1} attempts failed for {url}")

def throttle_request():
    """Add random delay between requests to avoid being blocked."""
    delay = random.uniform(1, 3)  # Random delay between 1-3 seconds
    logger.debug(f"Throttling request for {delay:.2f} seconds")
    time.sleep(delay)

def configure_proxy():
    """Configure proxy settings if available."""
    import os
    
    # Check for proxy environment variables
    http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    
    if http_proxy or https_proxy:
        proxies = {
            'http': http_proxy,
            'https': https_proxy
        }
        session.proxies.update(proxies)
        logger.info(f"Configured proxies: {proxies}")
    else:
        logger.debug("No proxy configuration found")

def reset_session():
    """Reset the session to clear cookies and start fresh."""
    global session
    session.close()
    session = requests.Session()
    session.max_redirects = 5
    configure_proxy()
    logger.info("Session reset completed")

def get_request_delay():
    """Get a random delay for requests to avoid detection."""
    return random.uniform(0.5, 2.5)

def initialize_scraper():
    """Initialize the scraper with proper configuration."""
    configure_proxy()
    session.headers.update(get_headers())
    logger.info("Scraper initialized with anti-detection measures")


def contains_icpe_keywords(text: str) -> bool:
    """
    Check if the text contains ICPE-related keywords.

    Args:
        text (str): The text to check for ICPE keywords

    Returns:
        bool: True if ICPE keywords are found, False otherwise
    """
    if not text:
        logger.debug("No text provided for ICPE keyword check")
        return False

    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()
    logger.debug(
        f"Checking ICPE keywords in text (length: {len(text_lower)} characters)"
    )

    # Check for ICPE-related keywords
    icpe_keywords = [
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
    ]

    for keyword in icpe_keywords:
        if keyword in text_lower:
            logger.info(f"Found ICPE keyword '{keyword}' in text")
            return True

    logger.debug("No ICPE keywords found in text")
    return False


def extract_pdf_links_from_page(url: str) -> List[str]:
    """
    Extract all PDF links from a webpage.

    Args:
        url (str): The URL to check for PDF links

    Returns:
        List[str]: List of PDF URLs found on the page
    """
    try:
        # Add throttling before request
        throttle_request()
        
        response = make_request_with_retry(url, max_retries=2, timeout=30)
        soup = BeautifulSoup(response.content, "html.parser")

        pdf_links = []
        # Find all links
        for link in soup.find_all("a", href=True):
            href = link["href"]
            # Convert relative URLs to absolute
            if not href.startswith("http"):
                href = urljoin(url, href)

            # Check if it's a PDF link
            if href.lower().endswith(".pdf") or "pdf" in href.lower():
                pdf_links.append(href)

        logger.info(f"Found {len(pdf_links)} PDF links on {url}")
        return pdf_links

    except Exception as e:
        logger.error(f"Error extracting PDF links from {url}: {e}")
        return []


def extract_text_from_pdf(pdf_url: str) -> str:
    """
    Extract text content from a PDF file using PyMuPDF (fitz) for better performance.
    Falls back to PyPDF2 if PyMuPDF fails.

    Args:
        pdf_url (str): The URL of the PDF file

    Returns:
        str: Extracted text content from the PDF
    """
    try:
        # Add throttling before request
        throttle_request()
        
        response = make_request_with_retry(pdf_url, max_retries=2, timeout=30)

        # Create a file-like object from the PDF content
        pdf_file = io.BytesIO(response.content)

        # Try PyMuPDF first (much faster)
        try:
            doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
            text_content = ""

            for page_num in range(doc.page_count):
                page = doc[page_num]
                text_content += page.get_text() + "\n"

            doc.close()
            logger.info(
                f"Extracted {len(text_content)} characters from PDF using PyMuPDF: {pdf_url}"
            )
            return text_content

        except Exception as fitz_error:
            logger.warning(
                f"PyMuPDF failed for {pdf_url}, falling back to PyPDF2: {fitz_error}"
            )

            # Fallback to PyPDF2
            pdf_file.seek(0)  # Reset file pointer
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text_content = ""

            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text_content += page.extract_text() + "\n"

            logger.info(
                f"Extracted {len(text_content)} characters from PDF using PyPDF2 fallback: {pdf_url}"
            )
            return text_content

    except Exception as e:
        logger.error(f"Error extracting text from PDF {pdf_url}: {e}")
        return ""


def check_pdfs_for_icpe(pdf_urls: List[str]) -> bool:
    """
    Check if any of the PDFs contain ICPE keywords.

    Args:
        pdf_urls (List[str]): List of PDF URLs to check

    Returns:
        bool: True if any PDF contains ICPE keywords, False otherwise
    """
    for pdf_url in pdf_urls:
        try:
            logger.info(f"Checking PDF for ICPE content: {pdf_url}")
            pdf_text = extract_text_from_pdf(pdf_url)

            if pdf_text and contains_icpe_keywords(pdf_text):
                logger.info(f"Found ICPE content in PDF: {pdf_url}")
                return True

        except Exception as e:
            logger.error(f"Error checking PDF {pdf_url} for ICPE: {e}")
            continue

    return False


def check_page_for_icpe(url: str) -> bool:
    """
    Check if a page contains ICPE keywords by scraping the full content.

    Args:
        url (str): The URL to check

    Returns:
        bool: True if ICPE keywords are found on the page, False otherwise
    """
    try:
        # Add throttling before request
        throttle_request()
        
        response = make_request_with_retry(url, max_retries=2, timeout=30)
        soup = BeautifulSoup(response.content, "html.parser")

        # Get all text content from the page
        page_text = soup.get_text()

        # Check if page contains ICPE keywords
        return contains_icpe_keywords(page_text)

    except Exception as e:
        logger.error(f"Error checking page for ICPE content at {url}: {e}")
        return False


def contains_negative_keywords(title: str, description: str) -> bool:
    """
    Check if the title or description contains any negative keywords.

    Args:
        title (str): The document title
        description (str): The document description

    Returns:
        bool: True if negative keywords are found, False otherwise
    """
    try:
        # Get all negative keywords from the database
        negative_keywords = NegativeKeyword.objects.all()

        # Combine title and description for checking
        text_to_check = f"{title} {description}".lower()

        for negative_keyword in negative_keywords:
            if negative_keyword.keyword.lower() in text_to_check:
                logger.info(
                    f"Document contains negative keyword '{negative_keyword.keyword}': {title}"
                )
                return True

        return False

    except Exception as e:
        logger.error(f"Error checking negative keywords: {e}")
        return False


def remove_documents_with_negative_keywords():
    """
    Remove existing documents from the database that contain negative keywords.
    This function should be called periodically to clean up the database.

    Returns:
        int: Number of documents removed
    """
    removed_count = 0

    try:
        # Get all documents
        documents = GovernmentDocument.objects.all()

        for document in documents:
            if contains_negative_keywords(document.title, document.description or ""):
                logger.info(
                    f"Removing document with negative keywords: {document.title}"
                )
                document.delete()
                removed_count += 1

        logger.info(f"Removed {removed_count} documents containing negative keywords")

    except Exception as e:
        logger.error(f"Error removing documents with negative keywords: {e}")

    return removed_count


def parse_date_from_detail(detail_text: str) -> datetime:
    """
    Parse date from fr-card__detail field.
    Expected format: "Mis à jour le DD/MM/YYYY"

    Args:
        detail_text (str): The detail text containing the date

    Returns:
        datetime: Parsed datetime object, or current time if parsing fails
    """
    logger.debug(f"Starting date parsing from detail text: '{detail_text}'")

    try:
        # Look for pattern "Mis à jour le DD/MM/YYYY"
        date_pattern = r"Mis à jour le (\d{1,2})/(\d{1,2})/(\d{4})"
        logger.debug(f"Using regex pattern: {date_pattern}")

        match = re.search(date_pattern, detail_text)

        if match:
            day, month, year = match.groups()
            logger.debug(f"Found date match - Day: {day}, Month: {month}, Year: {year}")

            parsed_date = datetime(
                int(year), int(month), int(day), tzinfo=timezone.get_current_timezone()
            )
            logger.info(
                f"Successfully parsed date: {parsed_date.strftime('%Y-%m-%d')} from '{detail_text}'"
            )
            return parsed_date
        else:
            logger.warning(f"No date pattern found in detail text: '{detail_text}'")
            logger.info(
                f"Using current time as fallback: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            return timezone.now()
    except Exception as e:
        logger.error(f"Error parsing date from '{detail_text}': {e}")
        logger.info(
            f"Using current time as fallback: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return timezone.now()


def save_to_database(scraped_data: List[Dict[str, Any]], domain: str) -> int:
    """
    Save scraped data to the database using GovernmentDocument model.

    Args:
        scraped_data (List[Dict[str, Any]]): List of scraped items
        domain (str): The domain name to extract prefecture info from

    Returns:
        int: Number of items saved to database
    """
    logger.info(
        f"Starting database save process for {len(scraped_data)} items from domain: {domain}"
    )
    saved_count = 0

    # Extract prefecture info from domain
    logger.debug(f"Extracting prefecture info for domain: {domain}")
    prefecture_info = get_prefecture_by_domain(domain)
    prefecture_name = prefecture_info["name"] if prefecture_info else None
    prefecture_code = prefecture_info["code"] if prefecture_info else None
    region_name = prefecture_info["region"] if prefecture_info else None
    logger.info(
        f"Prefecture info - Name: {prefecture_name}, Code: {prefecture_code}, Region: {region_name}"
    )

    for item in scraped_data:
        try:
            # Extract basic information first
            title = item.get("title", "")
            description = item.get("description", "")
            link = item.get("link", "")

            # Extract date from fr-card__detail metadata
            date_updated = timezone.now()  # Default to current time
            if "metadata" in item and "fr-card__detail" in item["metadata"]:
                detail_text = " ".join(item["metadata"]["fr-card__detail"])
                date_updated = parse_date_from_detail(detail_text)

            # Check if document contains negative keywords first
            if contains_negative_keywords(title, description):
                logger.info(f"Document contains negative keywords: {title}")

                # Check if document already exists and delete it if it does
                existing_document = GovernmentDocument.objects.filter(link=link).first()
                if existing_document:
                    logger.info(
                        f"Removing existing document that now contains negative keywords: {title}"
                    )
                    existing_document.delete()
                continue

            # Check if document already exists with same link and date
            existing_document = GovernmentDocument.objects.filter(
                link=link, date_updated=date_updated
            ).first()

            if existing_document:
                logger.info(
                    f"Document already exists with same link and date, skipping: {title}"
                )
                continue

            # Check for ICPE content (only for new/updated documents)
            is_icpe = False

            # First check title and description
            combined_text = f"{title} {description}".strip()
            if contains_icpe_keywords(combined_text):
                is_icpe = True
                logger.info(
                    f"Document marked as ICPE based on title/description: {title}"
                )
            else:
                # If not found in title/description, check the full page
                if link:
                    logger.info(f"Checking full page content for ICPE: {link}")
                    if check_page_for_icpe(link):
                        is_icpe = True
                        logger.info(
                            f"Document marked as ICPE based on full page content: {title}"
                        )
                    else:
                        # Third step: Check PDFs linked from the page
                        logger.info(f"Checking PDFs linked from page for ICPE: {link}")
                        pdf_links = extract_pdf_links_from_page(link)
                        if pdf_links:
                            if check_pdfs_for_icpe(pdf_links):
                                is_icpe = True
                                logger.info(
                                    f"Document marked as ICPE based on PDF content: {title}"
                                )
                        else:
                            logger.info(f"No PDF links found on page: {link}")

            # Check if document exists with same link but different date (update case)
            existing_document = GovernmentDocument.objects.filter(link=link).first()

            if existing_document:
                # Update existing document
                existing_document.title = title
                existing_document.description = description
                existing_document.date_updated = date_updated
                existing_document.is_icpe = is_icpe
                # Update prefecture info if provided
                if prefecture_name:
                    existing_document.prefecture_name = prefecture_name
                if prefecture_code:
                    existing_document.prefecture_code = prefecture_code
                if region_name:
                    existing_document.region_name = region_name
                existing_document.save()
                saved_count += 1
                logger.info(
                    f"Updated existing document: {existing_document.title} (ICPE: {is_icpe})"
                )
            else:
                # Create new document
                document = GovernmentDocument.objects.create(
                    title=title,
                    description=description,
                    link=link,
                    date_updated=date_updated,
                    prefecture_name=prefecture_name,
                    prefecture_code=prefecture_code,
                    region_name=region_name,
                    is_icpe=is_icpe,
                )
                saved_count += 1
                logger.info(f"Created new document: {document.title} (ICPE: {is_icpe})")

        except Exception as e:
            logger.error(f"Error saving item to database: {e}")
            continue

    return saved_count


def scrape_government_site(
    domain: str, keyword: str, offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Scrape a government website for keyword-related content.

    Args:
        domain (str): The domain name (e.g., 'morbihan.gouv.fr')
        keyword (str): The search keyword
        offset (int): The pagination offset (default: 0)

    Returns:
        List[Dict[str, Any]]: List of dictionaries containing scraped data
    """
    # Initialize scraper with anti-detection measures
    initialize_scraper()
    
    logger.info(
        f"Starting government site scraping - Domain: {domain}, Keyword: '{keyword}', Offset: {offset}"
    )

    try:
        # Construct the URL based on parameters
        if offset > 0:
            url = f"https://www.{domain}/contenu/recherche/(offset)/{offset}/(searchtext)/{keyword}?SearchText={keyword}"
            logger.debug(f"Constructed paginated URL: {url}")
        else:
            url = f"https://www.{domain}/contenu/recherche/(searchtext)/{keyword}?SearchText={keyword}"
            logger.debug(f"Constructed initial URL: {url}")

        # Add throttling before request
        throttle_request()
        
        # Make the request with retry logic
        logger.info(f"Making HTTP request to: {url}")
        response = make_request_with_retry(url, max_retries=3, timeout=30)
        logger.info(
            f"HTTP request successful - Status: {response.status_code}, Content length: {len(response.content)} bytes"
        )

        # Parse the HTML
        logger.debug("Parsing HTML content with BeautifulSoup")
        soup = BeautifulSoup(response.content, "html.parser")
        logger.debug(
            f"HTML parsing complete - Document title: '{soup.title.string if soup.title else 'No title'}'"
        )

        # Find all div elements with fr-card class
        results = []

        # Look for div elements with fr-card class
        logger.debug("Searching for fr-card elements in the HTML")
        fr_cards = soup.find_all("div", class_="fr-card")
        logger.info(f"Found {len(fr_cards)} fr-card elements on the page")

        for i, card in enumerate(fr_cards, 1):
            logger.debug(f"Processing card {i}/{len(fr_cards)}")
            card_data = extract_card_data(card, domain)
            if card_data:
                results.append(card_data)
                logger.debug(f"Successfully extracted data from card {i}")
            else:
                logger.warning(f"Failed to extract data from card {i}")

        logger.info(f"Successfully scraped {len(results)} items from {url}")

        # Save to database
        if results:
            logger.info(f"Starting database save process for {len(results)} items")
            saved_count = save_to_database(results, domain)
            logger.info(
                f"Database save complete - Saved {saved_count} items to database"
            )
        else:
            logger.warning(f"No results to save to database from {url}")

        return results

    except requests.RequestException as e:
        logger.error(f"Request error while scraping {url}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error while scraping {url}: {e}")
        return []


def extract_card_data(card_element, domain: str = None) -> Dict[str, Any]:
    """
    Extract data from a single fr-card element.

    Args:
        card_element: BeautifulSoup element representing a fr-card
        domain: The domain name to use for relative links (e.g., 'morbihan.gouv.fr')

    Returns:
        Dict[str, Any]: Extracted data from the card
    """
    logger.debug(f"Starting card data extraction with domain: {domain}")

    try:
        card_data = {}

        # Extract title
        logger.debug("Extracting title from card element")
        title_element = (
            card_element.find("h3")
            or card_element.find("h2")
            or card_element.find("h1")
        )
        if title_element:
            title_text = title_element.get_text(strip=True)
            card_data["title"] = title_text
            logger.debug(
                f"Found title: '{title_text[:50]}{'...' if len(title_text) > 50 else ''}'"
            )
        else:
            logger.debug("No title element found in card")

        # Extract link
        logger.debug("Extracting link from card element")
        link_element = card_element.find("a")
        if link_element:
            original_link = link_element.get("href", "")
            card_data["link"] = original_link
            logger.debug(f"Found original link: '{original_link}'")

            if original_link and not original_link.startswith("http") and domain:
                full_link = f"https://www.{domain}" + original_link
                card_data["link"] = full_link
                logger.debug(f"Converted relative link to absolute: '{full_link}'")
            elif original_link and original_link.startswith("http"):
                logger.debug(f"Link is already absolute: '{original_link}'")
        else:
            logger.debug("No link element found in card")

        # Extract description/summary
        logger.debug("Extracting description from card element")
        description_element = card_element.find("p") or card_element.find(
            "div", class_="fr-card__desc"
        )
        if description_element:
            description_text = description_element.get_text(strip=True)
            card_data["description"] = description_text
            logger.debug(
                f"Found description: '{description_text[:100]}{'...' if len(description_text) > 100 else ''}'"
            )
        else:
            logger.debug("No description element found in card")

        # Extract date if available
        logger.debug("Extracting date from card element")
        date_element = card_element.find("time") or card_element.find(
            "span", class_="date"
        )
        if date_element:
            date_text = date_element.get_text(strip=True)
            card_data["date"] = date_text
            logger.debug(f"Found date: '{date_text}'")
        else:
            logger.debug("No date element found in card")

        # Extract any additional metadata
        logger.debug("Extracting metadata from card element")
        metadata = {}

        # Look for specific classes that might contain useful info
        for class_name in ["fr-card__title", "fr-card__content", "fr-card__detail"]:
            elements = card_element.find_all(class_=class_name)
            if elements:
                metadata[class_name] = [elem.get_text(strip=True) for elem in elements]
                logger.debug(
                    f"Found {len(elements)} elements with class '{class_name}'"
                )

        if metadata:
            card_data["metadata"] = metadata
            logger.debug(f"Extracted metadata with keys: {list(metadata.keys())}")
        else:
            logger.debug("No metadata found in card")

        # Get the full HTML content for debugging
        card_data["html_content"] = str(card_element)
        logger.debug(
            f"Card HTML content length: {len(card_data['html_content'])} characters"
        )

        logger.info(
            f"Successfully extracted card data - Title: '{card_data.get('title', 'No title')[:30]}...', Link: '{card_data.get('link', 'No link')[:50]}...'"
        )
        return card_data

    except Exception as e:
        logger.error(f"Error extracting card data: {e}")
        logger.debug(f"Card element HTML: {str(card_element)[:200]}...")
        return {}


def scrape_url(domain: str, keyword: str, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Main function to scrape a government website and return structured data.

    Args:
        domain (str): The domain name (e.g., 'morbihan.gouv.fr')
        keyword (str): The search keyword
        offset (int): The pagination offset (default: 0)

    Returns:
        List[Dict[str, Any]]: List of scraped items
    """
    return scrape_government_site(domain, keyword, offset)


def scrape_all_results(domain: str, keyword: str) -> List[Dict[str, Any]]:
    """
    Scrape all results from a government website by incrementing offset until no more results.

    Args:
        domain (str): The domain name (e.g., 'morbihan.gouv.fr')
        keyword (str): The search keyword

    Returns:
        List[Dict[str, Any]]: List of all scraped items from all pages
    """
    # Initialize scraper with anti-detection measures
    initialize_scraper()
    
    all_results = []
    offset = 0
    page_count = 0

    logger.info(
        f"Starting to scrape all results for domain: {domain}, keyword: {keyword}"
    )

    while True:
        logger.info(f"Scraping offset {offset}...")

        # Scrape current page
        page_results = scrape_government_site(domain, keyword, offset)

        # If no results found, we've reached the end
        if not page_results:
            logger.info(f"No more results found at offset {offset}. Scraping complete.")
            break

        # Add results to our collection
        all_results.extend(page_results)
        logger.info(
            f"Found {len(page_results)} items at offset {offset}. Total so far: {len(all_results)}"
        )

        # Increment offset by 10 for next page
        offset += 10
        page_count += 1

        # Reset session every 5 pages to avoid detection
        if page_count % 5 == 0:
            logger.info(f"Resetting session after {page_count} pages to avoid detection")
            reset_session()

        # Safety check to prevent infinite loops (max 1000 results)
        if offset > 1000:
            logger.warning(
                "Reached maximum offset limit of 1000. Stopping to prevent infinite loop."
            )
            break

    logger.info(f"Scraping complete. Total results found: {len(all_results)}")

    # Save all results to database
    if all_results:
        saved_count = save_to_database(all_results, domain)
        logger.info(f"Saved {saved_count} total items to database")

    # Clean up existing documents that contain negative keywords
    removed_count = remove_documents_with_negative_keywords()
    if removed_count > 0:
        logger.info(
            f"Removed {removed_count} existing documents containing negative keywords"
        )

    return all_results


def scrape_generic(url: str) -> List[Dict[str, Any]]:
    """
    Generic scraper for any URL.

    Args:
        url (str): The URL to scrape

    Returns:
        List[Dict[str, Any]]: List of dictionaries containing scraped data
    """
    try:
        # Add throttling before request
        throttle_request()
        
        response = make_request_with_retry(url, max_retries=2, timeout=30)
        soup = BeautifulSoup(response.content, "html.parser")

        # Extract domain from URL for relative link handling
        from urllib.parse import urlparse

        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace("www.", "") if parsed_url.netloc else None

        # Look for fr-card elements
        fr_cards = soup.find_all("div", class_="fr-card")
        results = []

        for card in fr_cards:
            card_data = extract_card_data(card, domain)
            if card_data:
                results.append(card_data)

        logger.info(f"Successfully scraped {len(results)} items from {url}")

        # Note: scrape_generic doesn't save to database as it doesn't have prefecture context
        # Use scrape_government_site or scrape_all_results for database saving

        return results

    except Exception as e:
        logger.error(f"Error while scraping {url}: {e}")
        return []
