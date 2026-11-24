import base64
from datetime import datetime
import io
import os
import re
import time
from PIL import Image
import requests

PAGE_1_URL = os.environ.get("PAGE_1_URL", "").strip()
default_name = f"issue2pdf_github_{datetime.now().strftime('%d%m%Y')}.pdf"
raw_output = os.environ.get("OUTPUT_PDF", "").strip()
OUTPUT_PDF = raw_output if raw_output else default_name
if not OUTPUT_PDF.lower().endswith(".pdf"):
  OUTPUT_PDF += ".pdf"

MAX_PAGES = 200

clean_url = PAGE_1_URL.split("?")[0]
match = re.match(r"^(.*?/)page_\d+(\.svg)$", clean_url)

if not match:
  raise ValueError(
      "PAGE_1_URL must look like: https://svg.issuu.com/<doc_id>/page_1.svg"
  )

url_prefix, url_suffix = match.group(1), match.group(2)
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        " (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://new.marexmedia.com/",
}

img_pattern = re.compile(
    r"data:image/(jpeg|jpg|png|webp)[^\"']*?base64,([A-Za-z0-9+/=\s]+)",
    re.IGNORECASE,
)

pdf_pages = []

for page_num in range(1, MAX_PAGES + 1):
  page_url = f"{url_prefix}page_{page_num}{url_suffix}"
  response = requests.get(page_url, headers=headers, timeout=20)

  if response.status_code == 404:
    print(f"Reached end of document after page {page_num - 1}.")
    break

  if response.status_code != 200:
    print(
        f"Stopped at page {page_num} with HTTP status {response.status_code}."
    )
    break

  matches = img_pattern.findall(response.text)
  if not matches:
    print(f"No embedded images on page {page_num}; skipping.")
    continue

  best_img = None
  best_pixels = 0

  for _, b64_data in matches:
    try:
      clean_b64 = re.sub(r"\s+", "", b64_data)
      raw_bytes = base64.b64decode(clean_b64)
      img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
      pixels = img.width * img.height
      if pixels > best_pixels:
        best_pixels = pixels
        best_img = img
    except Exception:
      continue

  if best_img is not None:
    pdf_pages.append(best_img)
    print(f"Added page {page_num} ({best_img.width}x{best_img.height})")
  else:
    print(f"Could not decode image on page {page_num}; skipping.")

  time.sleep(0.2)

if not pdf_pages:
  raise RuntimeError("No pages could be extracted. Check the Page 1 URL.")

first_page, rest_pages = pdf_pages[0], pdf_pages[1:]
first_page.save(
    OUTPUT_PDF,
    "PDF",
    resolution=150.0,
    save_all=True,
    append_images=rest_pages,
)
print(f"Saved {len(pdf_pages)} pages to {OUTPUT_PDF}")
