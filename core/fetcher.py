import requests
import subprocess
import urllib3
from config.settings import REQUEST_TIMEOUT, USER_AGENT
from api.logger import root_logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_html_robust(url, timeout=REQUEST_TIMEOUT):
    """Fetch HTML with requests -> curl -> Playwright fallback."""
    
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    root_logger.debug(f"Fetching HTML: {url}")
    
    # Try requests with SSL verification first
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            root_logger.debug(f"Successfully fetched {url} with requests")
            return resp.text
        root_logger.warning(f"HTTP {resp.status_code} for {url}")
    except requests.exceptions.SSLError as e:
        root_logger.warning(f"SSL error for {url}, retrying without verification: {e}")
        try:
            resp = requests.get(url, headers=headers, timeout=timeout, verify=False)
            if resp.status_code == 200:
                root_logger.debug(f"Successfully fetched {url} with SSL bypass")
                return resp.text
        except Exception as e:
            root_logger.warning(f"SSL bypass failed for {url}: {e}")
    except Exception as e:
        root_logger.warning(f"Requests failed for {url}: {e}")

    # Fallback to curl (with -k for SSL bypass)
    root_logger.info(f"Trying curl fallback for {url}")
    try:
        result = subprocess.run(
            ['curl', '-s', '-L', '-k', url, '--max-time', str(timeout),
             '-H', f'User-Agent: {USER_AGENT}'],
            capture_output=True, text=True, timeout=timeout+5
        )
        if result.returncode == 0 and result.stdout:
            root_logger.debug(f"Successfully fetched {url} with curl")
            return result.stdout
        root_logger.warning(f"curl returned empty for {url}")
    except Exception as e:
        root_logger.error(f"curl fallback failed for {url}: {e}")
    
    # Final: Playwright
    root_logger.info(f"Using Playwright for {url}")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=timeout*1000)
            content = page.content()
            browser.close()
            root_logger.debug(f"Successfully fetched {url} with Playwright")
            return content
    except Exception as e:
        root_logger.error(f"Playwright failed for {url}: {e}", exc_info=True)
        return None

def fetch_article_text(url):
    """Fetch and extract article text using robust HTML fetcher + trafilatura."""
    root_logger.debug(f"Extracting article text: {url}")
    html = fetch_html_robust(url)
    if not html:
        root_logger.warning(f"No HTML fetched for {url}")
        return None
    
    import trafilatura
    text = trafilatura.extract(html, favor_recall=True)
    if text and len(text) > 200:
        root_logger.debug(f"Extracted {len(text)} chars from {url}")
        return text
    else:
        root_logger.warning(f"Insufficient text ({len(text) if text else 0} chars) from {url}")
        return None