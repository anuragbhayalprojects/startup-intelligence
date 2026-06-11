import sys
sys.path.append("/Users/anurag/Projects/startup-intelligence")
try:
    from curl_cffi import requests
except ImportError:
    import requests
from bs4 import BeautifulSoup
import os

url = "https://www.google.com/search?q=Riko+AI"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

try:
    response = requests.get(url, impersonate="chrome120", headers=headers, timeout=10)
    print("Status Code:", response.status_code)
    # Check if page is blocked
    if "did not match any documents" in response.text:
        print("Page loaded, but no results found.")
    elif "detected unusual traffic" in response.text or "captcha" in response.text.lower():
        print("Blocked by CAPTCHA / Unusual Traffic detection!")
    else:
        soup = BeautifulSoup(response.text, "html.parser")
        print("Title tag:", soup.title)
        print("Body length:", len(response.text))
        # Find all divs and classes
        print("Divs with class 'g':", len(soup.find_all("div", class_="g")))
        print("Divs with class containing 'VwiC3b':", len(soup.find_all("div", class_=lambda c: c and "VwiC3b" in c)))
        
        # Save HTML to local scratch space instead of non-existent artifacts dir
        scratch_dir = "/Users/anurag/.gemini/antigravity-ide/brain/c1fe2cf4-fbe8-4295-bf1f-da524739fa85"
        os.makedirs(scratch_dir, exist_ok=True)
        with open(os.path.join(scratch_dir, "google_response.html"), "w") as f:
            f.write(response.text)
        print("Saved HTML to scratch dir.")
except Exception as e:
    print("Error:", e)
