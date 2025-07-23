from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

import requests
import re


def is_internal_link(link, base_url):
    parsed_base = urlparse(base_url)
    parsed_link = urlparse(link)
    # 같은 도메인 or 상대경로
    return (parsed_link.netloc == "" or parsed_link.netloc == parsed_base.netloc)


def crawl_all_depth(url, visited=None):
    if visited is None:
        visited = set()
    if url in visited:
        return []

    try:
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        html = res.text
    except Exception:
        return []

    visited.add(url)
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for tag in soup.find_all("a", href=True):
        link = urljoin(url, tag['href']).split('#')[0]
        if is_internal_link(link, url):
            links.add(link)
    results = [url]
    for link in links:
        results += crawl_all_depth(link, visited)
    return results


def validate_url(string: str) -> bool:
    """Validates if the given string matches URL pattern."""
    url_regex = re.compile(
        r"^(https?:\/\/)?" r"(www\.)?" r"([a-zA-Z0-9.-]+)" r"(\.[a-zA-Z]{2,})?" r"(:\d+)?" r"(\/[^\s]*)?$",
        re.IGNORECASE,
    )
    return bool(url_regex.match(string))


def ensure_url(url: str) -> str:
    """Ensures the given string is a valid URL."""
    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    if not validate_url(url):
        error_msg = "Invalid URL - " + url
        raise ValueError(error_msg)

    return url


def extract_url(url: str):
    """
    Extract URLs and crawl for additional links.

    This function processes the given URL, ensures it is valid, and crawls all
    data at various depths from the provided URL. If any errors occur during this
    process, it raises a ValueError with an appropriate error message.

    Parameters:
        url (str): The URL to process and crawl.

    Returns:
        list: A list of all crawled URLs.

    Raises:
        ValueError: If there is an error during the crawling or URL processing.
    """
    urls = ensure_url(url.strip())

    try:
        processed_url = urls
        all_urls = crawl_all_depth(processed_url)
        return all_urls

    except Exception as e:
        raise ValueError(f"Error processing URLs: {e}") from e