import logging
import time
import random

try:
    from curl_cffi import requests
except ImportError:
    import requests

# Configure logging
logger = logging.getLogger("scrapers.http_client")

def get_session(impersonate: str = "chrome120") -> requests.Session:
    """
    Returns a new requests session instance.
    Utilizes curl_cffi's Session if available for TLS fingerprint impersonation.
    """
    try:
        # Check if impersonate parameter is supported (curl_cffi)
        session = requests.Session(impersonate=impersonate)
        logger.info(f"Initialized curl_cffi Session with impersonation: {impersonate}")
    except TypeError:
        # Fallback to standard requests Session
        session = requests.Session()
        logger.info("Initialized standard requests Session (curl_cffi not available or doesn't support impersonate)")
    
    # Configure default headers to look like a standard browser request
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive"
    })
    return session

def safe_request(session: requests.Session, url: str, method: str = "GET", max_retries: int = 3, backoff_factor: float = 2.0, **kwargs) -> requests.Response:
    """
    Executes an HTTP request with exponential backoff retries on rate limits (429) and server errors (5xx).
    
    Args:
        session (requests.Session): The connection pool session.
        url (str): Target URL.
        method (str): HTTP method.
        max_retries (int): Maximum number of retries before propagating failure.
        backoff_factor (float): Multiplier for exponential backoff delays.
        **kwargs: Additional parameters passed to requests.Session.request.
    """
    # Set default timeout if not provided to prevent hanging
    if "timeout" not in kwargs:
        kwargs["timeout"] = 10
        
    retries = 0
    while True:
        try:
            logger.info(f"Sending {method} request to {url} (Attempt {retries + 1}/{max_retries + 1})...")
            response = session.request(method, url, **kwargs)
            
            # Successful response
            if response.status_code == 200:
                return response
                
            # If rate-limited (429) or encountering server failures (5xx)
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                if retries >= max_retries:
                    logger.error(f"HTTP request failed with status {response.status_code} after {max_retries} retries.")
                    return response
                
                # Calculate exponential delay with randomized jitter to prevent thundering herd
                delay = (backoff_factor ** retries) + random.uniform(0.5, 1.5)
                logger.warning(f"HTTP {response.status_code} encountered. Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
                retries += 1
                continue
                
            # For all other error codes (like 403, 404), return immediately without retrying
            return response
            
        except Exception as e:
            if retries >= max_retries:
                logger.error(f"Request failed with connection/timeout exception after {max_retries} retries: {e}")
                raise e
                
            delay = (backoff_factor ** retries) + random.uniform(0.5, 1.5)
            logger.warning(f"Connection/Timeout error: {e}. Retrying in {delay:.2f} seconds...")
            time.sleep(delay)
            retries += 1
