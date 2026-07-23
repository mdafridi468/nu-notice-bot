import os
import json
import requests
import fitz  # PyMuPDF
from bs4 import BeautifulSoup

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
        response = requests.get(pdf_url, timeout=15)
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
        print("Webhook URL missing.")
        return

    payload = {
        "embeds": [{
            "title": title,
            "description": f"📄 [Download Official PDF Notice]({pdf_url})",
            "color": 3447003
        }]
    }

    if image_path and os.path.exists(image_path):
        payload["embeds"][0]["image"] = {"url": "attachment://notice.png"}
        with open(image_path, "rb") as f:
            files = {"file": ("notice.png", f, "image/png")}
            requests.post(webhook_url, data={"payload_json": json.dumps(payload)}, files=files)
    else:
        requests.post(webhook_url, json=payload)

def get_category_webhook(title):
    title_lower = title.lower()
    if any(k in title_lower for k in ["exam", "routine", "centre"]):
        return WEBHOOKS["exam"]
    elif any(k in title_lower for k in ["admission", "apply", "merit"]):
        return WEBHOOKS["admission"]
    elif any(k in title_lower for k in ["result", "mark", "gpa"]):
        return WEBHOOKS["results"]
    elif any(k in title_lower for k in ["news", "press"]):
        return WEBHOOKS["news"]
    return WEBHOOKS["notice"]

def check_nu_notices():
    url = "https://www.nu.ac.bd/recent-news-notice.php"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200:
            return

        soup = BeautifulSoup(res.content, "html.parser")
        rows = soup.select("table tr")
        history = load_history()

        for row in reversed(rows[:10]):
            link = row.find("a")
            if not link or "href" not in link.attrs:
                continue

            title = link.text.strip()
            pdf_link = link["href"]
            if not pdf_link.startswith("http"):
                pdf_link = "https://www.nu.ac.bd/" + pdf_link.lstrip("/")

            if pdf_link in history:
                continue

            print(f"New Notice Found: {title}")
            webhook_url = get_category_webhook(title)

            # Convert PDF 1st page to Image
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
