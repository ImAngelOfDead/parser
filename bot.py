import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time, os
import re

TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"}
SENT_FILE = "sent_news.txt"

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
    try:
        r = requests.post(url, data=data)
        r.raise_for_status()
    except Exception as e:
        print(f"Telegram error: {e}")

def championat_get_news_list(page):
    base_url = "https://www.championat.ru"
    page_url = f"{base_url}/news/{page}.html"
    response = requests.get(page_url, headers=HEADERS)
    if response.status_code != 200:
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    news = []
    for item in soup.find_all("div", class_="news-item"):
        a_tag = item.find("a", class_=lambda v: v and "news-item__title" in v)
        if a_tag:
            link = urljoin(base_url, a_tag.get("href"))
            title = a_tag.get_text(strip=True)
            news.append({"link": link, "title": title})
    return news

def championat_get_news_content(news_url):
    response = requests.get(news_url, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    article = soup.find("div", id="articleBody")
    if article:
        for rm in article.find_all("div", class_="match-embed"):
            rm.decompose()
        for ext in article.find_all("div", class_="external-article"):
            ext.decompose()
        return article.get_text(separator="\n", strip=True)
    return ""

def sex_get_news_list(page):
    base_url = "https://www.sport-express.ru"
    page_url = f"{base_url}/news/page{page}/"
    response = requests.get(page_url, headers=HEADERS)
    if response.status_code != 200:
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    news = []
    for item in soup.select("div.se-news-list-page__item"):
        title_tag = item.select_one("div.se-material__title.se-material__title--size-middle a")
        if title_tag:
            link = title_tag.get("href")
            if link.startswith("/"):
                link = base_url + link
            title = title_tag.get_text(strip=True)
            news.append({"link": link, "title": title})
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
    for a in container.find_all("a", class_="node-news-list__item"):
        link = a.get("href")
        if link.startswith("/"):
            link = base_url + link
        title = a.get("title")
        if not title:
            title_tag = a.find("div", class_="node-news-list__title")
            title = title_tag.get_text(strip=True) if title_tag else ""
        news.append({"link": link, "title": title})
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
    page_url = f"{base_url}/articles" if page == 1 else f"{base_url}/articles/page{page}"
    response = requests.get(page_url, headers=HEADERS)
    if response.status_code != 200:
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    news = []
    items = soup.find_all("div", class_="content-widget-line-item_grid-item__O1JP3")
    for item in items:
        a_tag = item.find("a")
        if not a_tag:
            continue
        link = a_tag.get("href")
        if link.startswith("/"):
            link = base_url + link
        title_tag = a_tag.find("div", class_="content-widget-line-item_truncate___zJNC")
        title = title_tag.get_text(strip=True) if title_tag else a_tag.get("title", "")
        news.append({"link": link, "title": title})
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
    page_url = f"{base_url}/sport" if page == 1 else f"{base_url}/sport?page={page}"
    response = requests.get(page_url, headers=HEADERS)
    if response.status_code != 200:
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    news = []
    container = soup.find("div", id="infinite_listing")
    if not container:
        return news
    for a in container.find_all("a", class_="tass_pkg_link-v5WdK"):
        link = a.get("href")
        if link.startswith("/"):
            link = base_url + link
        title_tag = a.find("span", class_="tass_pkg_title-xVUT1")
        title = title_tag.get_text(strip=True) if title_tag else a.get("title", "")
        news.append({"link": link, "title": title})
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
    # Удаляем URL-адреса изображений (jpg, jpeg, png, gif, webp)
    text = re.sub(r'https?://\S+\.(?:jpg|jpeg|png|gif|webp)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def parse_and_send_all_news():
    sent_links = load_sent_links()
    for parser in PARSERS:
        print(f"Parsing: {parser['name']}")
        page = 1
        while True:
            news_list = parser["get_list"](page)
            if not news_list:
                break
            for news in news_list:
                if news["link"] in sent_links:
                    continue
                try:
                    content = parser["get_content"](news["link"])
                except Exception as e:
                    print(f"Error fetching content from {news['link']}: {e}")
                    content = ""
                content = clean_content(content)
                message = f'<a href="{news["link"]}"><b>{news["title"]}</b></a>\n\n{content[:4000]}'
                send_telegram_message(message)
                print(f"Sent: {news['title']}")
                sent_links.add(news["link"])
                save_sent_link(news["link"])
                time.sleep(5)
            page += 1
            time.sleep(1)
    print("All sites parsed.")


def main():
    while True:
        print("Starting cycle...")
        parse_and_send_all_news()
        print("Waiting 5 minutes...")
        time.sleep(5 * 60)

if __name__ == "__main__":
    main()
