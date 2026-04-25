"""
Price scraper — ดึงราคาสินค้าจาก external_link

วิธีการ:
1. ดึง HTML ของหน้าเว็บด้วย requests (+ User-Agent เหมือน browser)
2. หา price จาก meta tags ตามลำดับความน่าเชื่อถือ:
   - Open Graph:  <meta property="og:price:amount" content="...">
   - Product meta: <meta property="product:price:amount" content="...">
   - JSON-LD schema.org/Product: offers.price
   - Twitter:     <meta name="twitter:data1" content="฿...">
   - Regex fallback: หา ฿xxx หรือ THBxxx ในเนื้อ HTML
3. คืน Decimal หรือ None

หมายเหตุ: Shopee/Lazada ใช้ JS render ราคาบ่อย → อาจจะดึงไม่ได้
         แต่เว็บร้านส่วนใหญ่ (Shopify, WooCommerce, PetExpress ฯลฯ) ใส่ meta ให้
"""
import re
import json
from decimal import Decimal, InvalidOperation

try:
    import requests
    from bs4 import BeautifulSoup
    _HAS_DEPS = True
except ImportError:
    _HAS_DEPS = False


UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def _to_decimal(val):
    if val is None:
        return None
    s = str(val).replace(',', '').replace('฿', '').replace('THB', '').strip()
    # เอาแค่ตัวเลข + จุดทศนิยม
    m = re.search(r'\d+(?:\.\d+)?', s)
    if not m:
        return None
    try:
        return Decimal(m.group(0))
    except InvalidOperation:
        return None


def scrape_price(url: str, timeout: int = 10):
    """
    คืน (price: Decimal | None, note: str) — note ใช้ log/debug
    """
    if not _HAS_DEPS:
        return None, "ต้องติดตั้ง: pip install requests beautifulsoup4"
    if not url:
        return None, "ไม่มี URL"

    try:
        resp = requests.get(url, headers={'User-Agent': UA}, timeout=timeout)
        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}"
    except Exception as e:
        return None, f"fetch error: {e}"

    soup = BeautifulSoup(resp.text, 'html.parser')

    # 1. Open Graph / product meta
    for prop in ('og:price:amount', 'product:price:amount', 'og:price'):
        tag = soup.find('meta', property=prop)
        if tag and tag.get('content'):
            price = _to_decimal(tag['content'])
            if price:
                return price, f"meta[{prop}]"

    # 2. itemprop="price"
    tag = soup.find(attrs={'itemprop': 'price'})
    if tag:
        val = tag.get('content') or tag.get_text()
        price = _to_decimal(val)
        if price:
            return price, "itemprop=price"

    # 3. JSON-LD schema.org/Product
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or '{}')
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            offers = item.get('offers')
            if isinstance(offers, list) and offers:
                offers = offers[0]
            if isinstance(offers, dict):
                p = _to_decimal(offers.get('price') or offers.get('lowPrice'))
                if p:
                    return p, "json-ld"

    # 4. Twitter data
    for name in ('twitter:data1', 'twitter:label1'):
        tag = soup.find('meta', attrs={'name': name})
        if tag and tag.get('content'):
            p = _to_decimal(tag['content'])
            if p and p > 1:
                return p, f"meta[{name}]"

    # 5. Regex fallback — หา ฿ หรือ THB ตามด้วยเลข
    text = soup.get_text(' ', strip=True)[:20000]
    m = re.search(r'(?:฿|THB\s*)([\d,]+(?:\.\d+)?)', text)
    if m:
        p = _to_decimal(m.group(1))
        if p:
            return p, "regex"

    return None, "ไม่พบราคาใน meta/ld-json/text (อาจเป็นหน้า JS-rendered เช่น Shopee)"
