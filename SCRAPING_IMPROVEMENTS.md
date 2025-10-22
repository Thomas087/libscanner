# Scraping Behavior Improvements

This document outlines the improvements made to reduce the chances of being blocked by websites during scraping operations.

## Key Improvements

### 1. Request Headers and Browser Simulation

- **Realistic Headers**: Added comprehensive browser headers including `Accept`, `Accept-Language`, `Accept-Encoding`, `DNT`, `Connection`, `Upgrade-Insecure-Requests`, and security headers
- **User Agent Rotation**: Implemented rotation of user agents from a pool of realistic browser user agents
- **Enhanced User Agent Support**: Added support for `fake-useragent` library for even more diverse user agent selection

### 2. Request Throttling and Rate Limiting

- **Random Delays**: Added random delays between requests (0.5-2.5 seconds) to avoid detection
- **Exponential Backoff**: Implemented exponential backoff for retry attempts
- **Request Throttling**: Added throttling function that introduces random delays before each request

### 3. Session Management

- **Persistent Sessions**: Using `requests.Session()` for cookie persistence and connection reuse
- **Session Rotation**: Automatic session reset every 5 pages to avoid detection patterns
- **Cookie Handling**: Proper cookie management to maintain session state

### 4. Retry Logic and Error Handling

- **Retry Mechanism**: Implemented retry logic with configurable maximum attempts (default: 3)
- **Exponential Backoff**: Progressive delay increases for retry attempts
- **Rate Limit Handling**: Special handling for HTTP 429 (rate limited) responses
- **Timeout Management**: Configurable timeout settings with proper error handling

### 5. Proxy Support

- **Environment Variable Support**: Automatic proxy configuration from `HTTP_PROXY` and `HTTPS_PROXY` environment variables
- **Proxy Rotation**: Support for proxy rotation to distribute requests

### 6. Anti-Detection Measures

- **Request Patterns**: Randomized request timing to avoid predictable patterns
- **Header Variation**: Dynamic header updates for each request
- **Session Management**: Regular session resets to avoid long-term detection

## Implementation Details

### New Functions Added

1. **`get_random_user_agent()`**: Returns a random user agent from the pool or fake-useragent library
2. **`get_headers()`**: Generates realistic browser headers
3. **`make_request_with_retry()`**: Handles requests with retry logic and error handling
4. **`throttle_request()`**: Adds random delays between requests
5. **`configure_proxy()`**: Sets up proxy configuration from environment variables
6. **`reset_session()`**: Resets the session to clear cookies and start fresh
7. **`get_request_delay()`**: Returns random delay values for requests
8. **`initialize_scraper()`**: Initializes the scraper with anti-detection measures

### Updated Functions

All HTTP request functions have been updated to use the new retry logic and throttling:

- `extract_pdf_links_from_page()`
- `extract_text_from_pdf()`
- `check_page_for_icpe()`
- `scrape_government_site()`
- `scrape_generic()`

### Session Management

The scraper now uses a global session object that:

- Maintains cookies across requests
- Handles connection pooling
- Supports proxy configuration
- Automatically resets every 5 pages during bulk scraping

## Configuration

### Environment Variables

- `HTTP_PROXY`: HTTP proxy URL
- `HTTPS_PROXY`: HTTPS proxy URL

### Dependencies Added

- `fake-useragent==1.4.0`: For enhanced user agent rotation
- `urllib3==2.0.7`: For better HTTP handling

## Usage Examples

### Basic Scraping

```python
from scraper.scraper import scrape_government_site

# The scraper will automatically apply anti-detection measures
results = scrape_government_site('morbihan.gouv.fr', 'environment')
```

### Bulk Scraping with Session Management

```python
from scraper.scraper import scrape_all_results

# Session will be automatically reset every 5 pages
all_results = scrape_all_results('morbihan.gouv.fr', 'environment')
```

### Manual Session Management

```python
from scraper.scraper import reset_session, initialize_scraper

# Initialize with anti-detection measures
initialize_scraper()

# Reset session when needed
reset_session()
```

## Best Practices

1. **Use Environment Variables**: Set proxy environment variables for distributed scraping
2. **Monitor Logs**: Check logs for rate limiting and retry attempts
3. **Respect Robots.txt**: Always check robots.txt before scraping
4. **Rate Limiting**: The scraper includes built-in rate limiting, but monitor target site responses
5. **Session Rotation**: Sessions are automatically rotated during bulk operations

## Monitoring and Debugging

The scraper includes comprehensive logging for:

- Request attempts and retries
- Rate limiting detection
- Session resets
- Proxy configuration
- User agent rotation

Check the logs for any issues or patterns that might indicate detection.

## Future Enhancements

Potential future improvements could include:

- IP rotation with proxy pools
- CAPTCHA solving integration
- JavaScript rendering support
- Advanced fingerprinting avoidance
- Machine learning-based request pattern optimization
