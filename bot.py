import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time, os, re
from datetime import datetime, timedelta
import dateparser

TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"}
SENT_FILE = "sent_news.txt"

MONTHS_RU = {
    'января': 1,
    'февраля': 2,
    'марта': 3,
    'апреля': 4,
    'мая': 5,
    'июня': 6,
    'июля': 7,
    'августа': 8,
    'сентября': 9,
    'октября': 10,
    'ноября': 11,
    'декабря': 12
}


def load_sent_links():
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_sent_link(link):
    with open(SENT_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    max_retries = 3
    for attempt in range(max_retries):
        try:
            r = requests.post(url, data=data)
            r.raise_for_status()
            return
        except requests.exceptions.HTTPError as e:
            if r.status_code == 429:

                retry_after = int(r.headers.get("Retry-After", 10))
                print(f"Telegram 429: waiting {retry_after} seconds...")
                time.sleep(retry_after)
            else:
                print(f"Telegram error: {e}")
                break

FRESH_INTERVAL = timedelta(minutes=20)

def championat_get_news_list(page):
    base_url = "https://www.championat.ru"
    page_url = f"{base_url}/news/1.html" 
    response = requests.get(page_url, headers=HEADERS)
    if response.status_code != 200:
        return []
    soup = BeautifulSoup(response.text, "html.parser")

    head_div = soup.find("div", class_="news-items__head")
    if head_div:
        date_str = head_div.get_text(strip=True)
        parts = date_str.split()
        if len(parts) == 3:
            day = int(parts[0])
            month = MONTHS_RU.get(parts[1].lower(), 0)
            year = int(parts[2])
        else:
            day, month, year = None, None, None
    else:
        day, month, year = None, None, None

    news = []
    for item in soup.find_all("div", class_="news-item"):
        time_div = item.find("div", class_="news-item__time")
        pub_date = None
        if time_div and day is not None:
            time_str = time_div.get_text(strip=True)
            try:
                hour, minute = map(int, time_str.split(":"))
                pub_date = datetime(year, month, day, hour, minute)
            except Exception:
                pub_date = None
        a_tag = item.find("a", class_="news-item__title")
        if a_tag:
            link = urljoin(base_url, a_tag.get("href"))
            title = a_tag.get_text(strip=True)
            news.append({"link": link, "title": title, "date": pub_date})

 
    now = datetime.now()
    news = [n for n in news if n.get("date") and (now - n["date"]) <= FRESH_INTERVAL]
    news.sort(key=lambda x: x["date"])
    return news

def championat_get_news_content(url):
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    content_div = soup.find("div", {"id": "articleBody"}) or soup.find("div", class_="article__content")
    if not content_div:
        return ""
    for tag in content_div.find_all(["script", "style", "aside", "noscript"]):
        tag.decompose()
    return content_div.get_text(separator="\n", strip=True)

def sex_get_news_list(page):
    url = f"https://www.sport-express.ru/news/page{page}/"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    news = []
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    items = soup.find_all("div", class_="se-news-list-page__item")
    for item in items:
        left_div = item.find("div", class_="se-news-list-page__item-left")
        pub_date = None
        if left_div:
            time_text = left_div.get_text(strip=True)
            match = re.search(r'(\d{1,2}):(\d{2})', time_text)
            if match:
                hour, minute = map(int, match.groups())
                pub_date = today.replace(hour=hour, minute=minute)
                if pub_date > now:
                    pub_date -= timedelta(days=1)
            else:
                print(f"Не удалось распарсить время: {time_text}")
        right_div = item.find("div", class_="se-news-list-page__item-right")
        if right_div:
            title_div = right_div.find("div", class_="se-material__title")
            a_tag = title_div.find("a") if title_div else right_div.find("a")
            if a_tag:
                link = urljoin("https://www.sport-express.ru", a_tag.get("href"))
                title = a_tag.get_text(strip=True)
                news.append({"link": link, "title": title, "date": pub_date})

    news = [n for n in news if n.get("date") and (now - n["date"]) <= FRESH_INTERVAL]
    news.sort(key=lambda x: x["date"])
    return news

def sex_get_news_content(news_url):
    response = requests.get(news_url, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    content_div = soup.find("div", class_="se-material-page__content")
    if content_div:
        for ad in content_div.find_all("div", class_="se-banner"):
            ad.decompose()
        return content_div.get_text(separator="\n", strip=True)
    return ""

def matchtv_get_news_list(page):
    base_url = "https://matchtv.ru"
    page_url = f"{base_url}/news" if page == 1 else f"{base_url}/news?page={page}"
    response = requests.get(page_url, headers=HEADERS)
    if response.status_code != 200:
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    news = []
    container = soup.find("div", class_="node-news-list")
    if not container:
        return news
    now = datetime.now()
    for a in container.find_all("a", class_="node-news-list__item"):
        link = a.get("href")
        if link.startswith("/"):
            link = base_url + link
        title = a.get("title")
        if not title:
            title_tag = a.find("div", class_="node-news-list__title")
            title = title_tag.get_text(strip=True) if title_tag else ""
        dt = None
        credits = a.find("div", class_="credits")
        if credits:
            li_items = credits.find_all("li", class_="credits__item")
            if li_items:
                time_str = li_items[0].get_text(strip=True)

                if not re.search(r'\d{4}', time_str):
                    time_str = time_str + f" {now.year}"
                dt = dateparser.parse(time_str, languages=['ru'])
        if dt and (now - dt) <= FRESH_INTERVAL:
            news.append({"link": link, "title": title, "datetime": dt})
    news.sort(key=lambda x: x["datetime"])
    return news

def matchtv_get_news_content(news_url):
    response = requests.get(news_url, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    content_div = soup.find("div", class_="article__content")
    if content_div:
        for tag in content_div.find_all(["script", "style"]):
            tag.decompose()
        return content_div.get_text(separator="\n", strip=True)
    return ""

def sovsport_get_news_list(page):
    base_url = "https://www.sovsport.ru"
    page_url = base_url if page == 1 else f"{base_url}/?page={page}"
    response = requests.get(page_url, headers=HEADERS)
    if response.status_code != 200:
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    news = []
    container = soup.find("div", class_="news_list-wrapper__I3i1I")
    if not container:
        return news
    date_line = container.find("div", class_="date-line_date-line__WX_gU")
    if date_line:
        date_text = date_line.get_text(strip=True)
        if "Сегодня" in date_text:
            date_part = datetime.today().strftime("%d %B %Y")
        elif "Вчера" in date_text:
            date_part = (datetime.today() - timedelta(days=1)).strftime("%d %B %Y")
        else:
            date_part = date_text
    else:
        date_part = ""
    items = container.find_all("div", class_="virtualized-list-item_main__pA9uw")
    for item in items:
        info = item.find("div", class_="virtualized-list-item_info__qHKxs")
        if not info:
            continue
        time_div = info.find("div", class_=lambda x: x and "typography-module__font-text" in x and "typography-module__font-table-tag" in x)
        if not time_div:
            continue
        time_str = time_div.get_text(strip=True)
        dt = dateparser.parse(f"{date_part} {time_str}", languages=["ru"])
        link_div = item.find("div", class_="virtualized-list-item_link__ihbkh")
        if not link_div:
            continue
        a_tag = link_div.find("a")
        if not a_tag:
            continue
        link = a_tag.get("href")
        if link.startswith("/"):
            link = base_url + link
        title = a_tag.get_text(strip=True)
        if dt and (datetime.now() - dt) <= FRESH_INTERVAL:
            news.append({"link": link, "title": title, "datetime": dt})
    news.sort(key=lambda x: x["datetime"])
    return news

def sovsport_get_news_content(news_url):
    response = requests.get(news_url, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    content_div = soup.find("div", class_="content-controller_text-editor__9ET6v")
    if content_div:
        for tag in content_div.find_all(["script", "style"]):
            tag.decompose()
        return content_div.get_text(separator="\n", strip=True)
    return ""

def tass_get_news_list(page):
    base_url = "https://tass.ru"
    page_url = base_url if page == 1 else f"{base_url}/?page={page}"
    response = requests.get(page_url, headers=HEADERS)
    if response.status_code != 200:
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    news = []
    container = soup.find("div", id="infinite_listing")
    if not container:
        return news
    news_items = container.find_all("a", class_="tass_pkg_link-v5WdK")
    now = datetime.now()
    for a in news_items:
        link = a.get("href")
        if link.startswith("/"):
            link = base_url + link
        title_tag = a.find("span", class_="tass_pkg_title-xVUT1")
        title = title_tag.get_text(strip=True) if title_tag else ""
        marks_container = a.find("div", class_="tass_pkg_marks-VHTfC")
        if not marks_container:
            continue
        time_tag = marks_container.find("div", class_=lambda c: c and "tass_pkg_marker--font_weight_black" in c)
        if not time_tag:
            continue
        time_text = time_tag.get_text(strip=True)
        pub_dt = None
        if "назад" in time_text:
            parts = time_text.split()
            try:
                amount = int(parts[0])
            except ValueError:
                continue
            if "минут" in time_text:
                pub_dt = now - timedelta(minutes=amount)
            elif "час" in time_text:
                pub_dt = now - timedelta(hours=amount)
        elif "Сегодня" in time_text or "Вчера" in time_text:
            if "Сегодня" in time_text:
                date_part = datetime.now().strftime("%d %B %Y")
            else:
                date_part = (datetime.now() - timedelta(days=1)).strftime("%d %B %Y")
            time_part = time_text.split(",")[-1].strip()
            dt_str = f"{date_part} {time_part}"
            pub_dt = dateparser.parse(dt_str, languages=["ru"])
        else:
            pub_dt = dateparser.parse(time_text, languages=["ru"])
        if not pub_dt:
            continue
        if (now - pub_dt).total_seconds() <= 20 * 60:
            news.append({"link": link, "title": title, "datetime": pub_dt})
    news.sort(key=lambda x: x["datetime"])
    return news

def tass_get_news_content(news_url):
    response = requests.get(news_url, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    content_div = soup.find("article", class_="Content_wrapper__DiAVL")
    if content_div:
        for tag in content_div.find_all(["script", "style"]):
            tag.decompose()
        return content_div.get_text(separator="\n", strip=True)
    return ""

def rbk_get_news_list(page):
    base_url = "https://sportrbc.ru"
    url = base_url + "/news" if page == 1 else f"{base_url}/news/page{page}"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    news = []
    container = soup.find("div", class_="g-overflow")
    if not container:
        return news
    for a in container.find_all("a", class_="item__link rm-cm-item-link js-rm-central-column-item-link"):
        link = a.get("href")
        if link.startswith("/"):
            link = base_url + link
        title_elem = a.find("span", class_="item__title rm-cm-item-text js-rm-central-column-item-text")
        title = title_elem.get_text(strip=True) if title_elem else a.get("title", "")
        news.append({"link": link, "title": title})
    return news

def rbk_get_news_content(news_url):
    resp = requests.get(news_url, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    content_div = soup.find("div", class_="article__text")
    return content_div.get_text(separator="\n", strip=True) if content_div else ""

def ria_get_news_list(page):
    base_url = "https://sn.ria.ru/sport/"
    page_url = base_url if page == 1 else f"{base_url}page/{page}/"
    r = requests.get(page_url, headers=HEADERS)
    if r.status_code != 200:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    news = []
    container = soup.find("div", class_="list list-tags")
    if not container:
        return news
    for item in container.find_all("div", class_="list-item"):
        title_link = item.find("a", class_="list-item__title")
        if not title_link:
            continue
        link = title_link.get("href")
        if link and not link.startswith("http"):
            link = "https://sn.ria.ru" + link
        title = title_link.get_text(strip=True)

        news.append({"link": link, "title": title})
    return news

def ria_get_news_content(news_url):
    r = requests.get(news_url, headers=HEADERS)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    content_div = soup.find("div", class_="article__text")
    if content_div:
        for tag in content_div.find_all(["script", "style"]):
            tag.decompose()
        return content_div.get_text(separator="\n", strip=True)
    return ""


PARSERS = [
    {"name": "Championat", "base_url": "https://www.championat.ru", "get_list": championat_get_news_list, "get_content": championat_get_news_content},
    {"name": "Sport-Express", "base_url": "https://www.sport-express.ru", "get_list": sex_get_news_list, "get_content": sex_get_news_content},
    {"name": "MatchTV", "base_url": "https://matchtv.ru", "get_list": matchtv_get_news_list, "get_content": matchtv_get_news_content},
    {"name": "Sovsport", "base_url": "https://www.sovsport.ru", "get_list": sovsport_get_news_list, "get_content": sovsport_get_news_content},
    {"name": "TASS", "base_url": "https://tass.ru", "get_list": tass_get_news_list, "get_content": tass_get_news_content},
    {"name": "SportRbc", "base_url": "https://sportrbc.ru/", "get_list": rbk_get_news_list, "get_content": rbk_get_news_content},
    {"name": "RIA Sport", "base_url": "https://sn.ria.ru/sport/", "get_list": ria_get_news_list, "get_content": ria_get_news_content}
]

def clean_content(text):
    text = re.sub(r'https?://\S+\.(?:jpg|jpeg|png|gif|webp)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def parse_and_send_all_news():
    sent_links = load_sent_links()
    cutoff = datetime.now() - timedelta(minutes=20)
    max_pages = 1
    for parser in PARSERS:
        print(f"Parsing: {parser['name']}")
        page = 1
        while page <= max_pages:
            news_list = parser["get_list"](page)
            if not news_list:
                break

            fresh_news = []
            for n in news_list:
                pub_time = n.get("date") or n.get("datetime")
                if pub_time and pub_time >= cutoff:
                    fresh_news.append(n)

            if not fresh_news:
                break

            for news in fresh_news:
                if news["link"] in sent_links:
                    continue
                try:
                    news["content"] = parser["get_content"](news["link"])
                except Exception as e:
                    print(f"Error: {news['link']}: {e}")
                    news["content"] = ""
                clean_text = clean_content(news["content"])
                message = f'<a href="{news["link"]}"><b>{news["title"]}</b></a>\n\n{clean_text[:4000]}'
                send_telegram_message(message)
                print(f"Sent: {news['title']}")
                sent_links.add(news["link"])
                save_sent_link(news["link"])
                time.sleep(5)
            page += 1
            time.sleep(1)
        print(f"{parser['name']} parsed.")
    print("All sites parsed.")

def main():
    while True:
        print("Starting cycle...")
        parse_and_send_all_news()
        print("Waiting 5 minutes...")
        time.sleep(5 * 60)

if __name__ == "__main__":
    main()
