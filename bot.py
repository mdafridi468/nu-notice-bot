import os
import json
import requests
import fitz  # PyMuPDF
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Webhook URLs from GitHub Secrets
WEBHOOKS = {
    "exam": os.getenv("WEBHOOK_EXAM"),
    "admission": os.getenv("WEBHOOK_ADMISSION"),
    "notice": os.getenv("WEBHOOK_NOTICE"),
    "results": os.getenv("WEBHOOK_RESULTS"),
    "news": os.getenv("WEBHOOK_NEWS")
}

HISTORY_FILE = "sent_notices.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

def convert_pdf_to_image(pdf_url, output_image_path="notice.png"):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(pdf_url, headers=headers, timeout=25, verify=False)
        if response.status_code == 200:
            doc = fitz.open(stream=response.content, filetype="pdf")
            page = doc[0]  # Render page 1
            pix = page.get_pixmap(dpi=150)
            pix.save(output_image_path)
            return True
    except Exception as e:
        print(f"Error converting PDF: {e}")
    return False

def send_to_discord(webhook_url, title, pdf_url, image_path=None):
    if not webhook_url:
        print(f"⚠️ Webhook URL missing for notice: {title[:30]}")
        # Fallback to notice or exam webhook if missing
        webhook_url = WEBHOOKS["notice"] or WEBHOOKS["exam"]

    if not webhook_url:
        print("❌ No valid Webhook URL found at all!")
        return

    payload = {
        "embeds": [{
            "title": title,
            "description": f"📄 [অফিশিয়াল নোটিশ (PDF) ডাউনলোড করুন]({pdf_url})",
            "color": 3447003
        }]
    }

    try:
        if image_path and os.path.exists(image_path):
            payload["embeds"][0]["image"] = {"url": "attachment://notice.png"}
            with open(image_path, "rb") as f:
                files = {"file": ("notice.png", f, "image/png")}
                res = requests.post(webhook_url, data={"payload_json": json.dumps(payload)}, files=files)
        else:
            res = requests.post(webhook_url, json=payload)
            
        print(f"Discord Response Code: {res.status_code} for '{title[:25]}...'")
    except Exception as e:
        print(f"Error sending to Discord: {e}")

def get_category_webhook(title):
    title_lower = title.lower()
    
    # Bengali & English Keyword Detection for Exams/Routines
    if any(k in title_lower for k in ["পরীক্ষা", "ইনকোর্স", "রুটিন", "কেন্দ্র", "ডিগ্রী", "অনার্স", "মাষ্টার্স", "ফর্ম পূরণ", "exam", "routine"]):
        return WEBHOOKS["exam"] or WEBHOOKS["notice"]
        
    # Admission Keywords
    elif any(k in title_lower for k in ["ভর্তি", "মেধা তালিকা", "রিলিজ স্লিপ", "আবেদন", "admission", "apply"]):
        return WEBHOOKS["admission"] or WEBHOOKS["notice"]
        
    # Results Keywords
    elif any(k in title_lower for k in ["ফলাফল", "রেজাল্ট", "সিজিপিএ", "মার্ক", "result", "gpa"]):
        return WEBHOOKS["results"] or WEBHOOKS["notice"]
        
    # News/Press Keywords
    elif any(k in title_lower for k in ["সংবাদ", "প্রেস", "প্রতিবেদন", "news", "press"]):
        return WEBHOOKS["news"] or WEBHOOKS["notice"]
        
    return WEBHOOKS["notice"] or WEBHOOKS["exam"]

def check_nu_notices():
    url = "https://www.nu.ac.bd/recent-news-notice.php"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=25, verify=False)
        if res.status_code != 200:
            print(f"Failed connection to NU Website. Status code: {res.status_code}")
            return

        soup = BeautifulSoup(res.content, "html.parser")
        rows = soup.select("table tr")
        
        # Fresh fetch list
        history = []

        for row in reversed(rows[:8]):
            link = row.find("a")
            if not link or "href" not in link.attrs:
                continue

            title = link.text.strip()
            pdf_link = link["href"]
            if not pdf_link.startswith("http"):
                pdf_link = "https://www.nu.ac.bd/" + pdf_link.lstrip("/")

            print(f"Processing Notice: {title[:40]}...")
            webhook_url = get_category_webhook(title)

            has_image = convert_pdf_to_image(pdf_link)
            image_path = "notice.png" if has_image else None

            send_to_discord(webhook_url, title, pdf_link, image_path)

            if os.path.exists("notice.png"):
                os.remove("notice.png")

            history.append(pdf_link)

        save_history(history)

    except Exception as e:
        print(f"Error checking notices: {e}")

if __name__ == "__main__":
    check_nu_notices()
