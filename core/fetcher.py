import requests
import subprocess
import urllib3
from config.settings import REQUEST_TIMEOUT, USER_AGENT

# Disable SSL warnings globally
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_html_robust(url, timeout=REQUEST_TIMEOUT):
    """Fetch HTML with requests -> curl -> Playwright fallback."""
    
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    # Try requests with SSL verification first
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            return resp.text
        print(f"    ⚠️ HTTP {resp.status_code} for {url}")
    except requests.exceptions.SSLError:
        print(f"    ⚠️ SSL error, retrying without verification...")
        try:
            resp = requests.get(url, headers=headers, timeout=timeout, verify=False)
            if resp.status_code == 200:
                return resp.text
        except Exception as e:
            print(f"    ⚠️ SSL bypass failed: {e}")
    except Exception as e:
        print(f"    ⚠️ requests failed: {e}")
    
    # Fallback to curl (with -k for SSL bypass)
    try:
        result = subprocess.run(
            ['curl', '-s', '-L', '-k', url, '--max-time', str(timeout),
             '-H', f'User-Agent: {USER_AGENT}'],
            capture_output=True, text=True, timeout=timeout+5
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
    except Exception as e:
        print(f"    ⚠️ curl fallback failed: {e}")
    
    # Final: Playwright
    print(f"    🌐 Using Playwright for {url}")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=timeout*1000)
            content = page.content()
            browser.close()
            return content
    except Exception as e:
        print(f"    ❌ Playwright failed: {e}")
        return None

def fetch_article_text(url):
    """Fetch and extract article text using robust HTML fetcher + trafilatura."""
    html = fetch_html_robust(url)
    if not html:
        return None
    import trafilatura
    text = trafilatura.extract(html, favor_recall=True)
    return text if text and len(text) > 200 else None