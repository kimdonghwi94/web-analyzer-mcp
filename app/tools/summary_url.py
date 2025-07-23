from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import Comment, BeautifulSoup, Tag
# from playwright.sync_api import sync_playwright
from difflib import get_close_matches

import re
import time


TAG_SCORES = {
    'h1': 3.0, 'h2': 2.5, 'h3': 2.0, 'h4': 1.5,
    'p': 1.5, 'li': 1.2, 'ul': 1.0, 'ol': 1.0,
    'table': 2.0, 'thead': 0.5, 'tbody': 0.5,
    'tr': 0.3, 'td': 0.2, 'th': 0.3,
    'img': 1.5, 'figure': 1.5, 'figcaption': 1.2,
    'blockquote': 1.0, 'code': 1.0, 'pre': 1.0,
    'strong': 0.5, 'em': 0.5, 'a': 0.0,
    'span': 0.3, 'div': 0.5,
}

# 상위 구조 (부모 태그) 가중치
CONTAINER_SCORES = {
    'main': 3,
    'article': 2,
    'section': 2,
    'body': 1,
    'div': 0.5,
}


def validate_url(string: str) -> bool:
    """Validates if the given string matches URL pattern."""
    url_regex = re.compile(
        r"^(https?:\/\/)?" r"(www\.)?" r"([a-zA-Z0-9.-]+)" r"(\.[a-zA-Z]{2,})?" r"(:\d+)?" r"(\/[^\s]*)?$",
        re.IGNORECASE,
    )
    return bool(url_regex.match(string))


def check_ensure_url(url: str) -> str:
    """Ensures the given string is a valid URL."""
    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    if not validate_url(url):
        error_msg = "Invalid URL - " + url
        raise ValueError(error_msg)
    return url


def build_html_content(url):
    # with sync_playwright() as p:
    #     browser = p.chromium.launch(headless=True)
    #     page = browser.new_page()
    #     page.goto(url)
    #     sample_html = page.content()
    #     browser.close()
    # print("여기")

    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    time.sleep(5)  # 렌더링 시간 대기 (필요시 조절)
    sample_html = driver.page_source
    driver.quit()

    return sample_html


def remove_unimportant_tags(soup, keep_attr: bool = False):
    def parse_popup_tag(soup) -> str:
        """
        - popup / modal 등의 클래스를 가진 요소를 찾아
          ‣ 팝업 ID, 클래스
          ‣ 포함된 <img> 태그의 alt·src
          ‣ 사용자가 볼 수 있는 텍스트(앞 80자)
        를 한 줄로 정리해 반환한다.
        """

        popup_keywords = [
            "popup", "overlay",
            "dialog", "lightbox", "toast"
        ]

        bs_popup_elements = []

        # 1) class 속성에서 키워드가 '정확히' 포함된 요소 수집
        for kw in popup_keywords:
            # class_='popup' 은 class 목록 중 popup 이 들어-있는 모든 태그를 반환
            bs_popup_elements.extend(soup.find_all(class_=kw.lower()))

        # 2) 중복 제거
        bs_popup_elements = list(dict.fromkeys(bs_popup_elements))
        if not bs_popup_elements:
            return ""

        popup_lines: list[str] = []
        for tag in bs_popup_elements:
            # ──────────────────────────────────────────────
            # (1) 기본 메타: id, class
            popup_id = tag.get("id", "")
            classes = " ".join(tag.get("class", []))

            # (2) 이미지 수집
            img_parts = []
            for img in tag.find_all("img"):
                alt = img.get("alt", "").strip()
                src = img.get("src", "").strip()
                img_parts.append(f'{alt} ({src})')
            imgs_text = "; ".join(img_parts) if img_parts else "no image"

            # (3) 팝업 내 노출 텍스트(앞 80자)
            visible_text = tag.get_text(strip=True, separator=" ")
            if len(visible_text) > 80:
                visible_text = visible_text[:80] + "…"

            # (4) 최종 라인 조립 – 기존 함수들과 같은 형식으로
            popup_lines.append(
                f'[Popup] {imgs_text} | text="{visible_text}"'
            )
            # ──────────────────────────────────────────────

        return "\n".join(popup_lines).strip()

    def parse_table_tag(soup):
        # soup = bs4.BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if table is None:
            return ""
        # 캡션 추출
        caption = table.caption.get_text(strip=True) if table.caption else False
        if not caption:
            return ""

        # 헤더 추출
        headers = []
        thed_tag = table.find("thead") is not None
        if thed_tag:
            for th in table.find("thead").find_all("th"):
                headers.append(th.get_text(strip=True))

        # 데이터 추출
        rows = []
        tbody_tag = table.find("tbody")
        if tbody_tag:
            for tr in table.find("tbody").find_all("tr"):
                row_data = []
                for td in tr.find_all("td"):
                    # reserve-time 처럼 여러 div로 나뉜 경우 합침
                    divs = td.find_all("div")
                    if divs:
                        combined = " ".join(div.get_text(strip=True) for div in divs)
                        row_data.append(combined)
                    else:
                        row_data.append(td.get_text(strip=True))
                if row_data:
                    rows.append(row_data)

        # 표를 텍스트로 재구성
        table_text = f"[Table] {caption}\n"
        if thed_tag:
            table_text += " | ".join(headers) + "\n"
        if tbody_tag:
            for row in rows:
                table_text += " | ".join(row) + "\n"

        return table_text.strip()

    def parse_img_tag(soup):
        imgs = soup.find_all("img")
        if imgs is None:
            return ""
        img_texts = []
        for tag in imgs:
            alt = tag.get('alt', '')
            src = tag.get('src', '')
            img_texts.append(f'[Image] {alt} ({src})')
        return "\n".join(img_texts)

    def parse_iframe_tag(soup):
        videos = soup.find_all("iframe")
        if videos is None:
            return ""
        video_texts = []
        for tag in videos:
            title = tag.get('title', 'Embedded Video')
            src = tag.get('src', '')
            video_texts.append(f'[Video] {title} - {src}')
        return "\n".join(video_texts)

    def clean_xml(html):
        # remove tags starts with <?xml
        html = re.sub(r"<\?xml.*?>", "", html)
        # remove tags starts with <!DOCTYPE
        html = re.sub(r"<!DOCTYPE.*?>", "", html)
        # remove tags starts with <!DOCTYPE
        html = re.sub(r"<!doctype.*?>", "", html)
        return html

    try:
        unimport_tags = ["script", "style", "meta", "nav", "footer", "header", "aside", "form", "input", "noscript",
                         "svg", "canvas", "img", "table", "iframe", "popup"]

        table_str = parse_table_tag(soup)
        img_str = parse_img_tag(soup)
        iframe_str = parse_iframe_tag(soup)
        popup_str = parse_popup_tag(soup)

        # remove unimportant tags
        for tag in unimport_tags:
            for node in soup.find_all(tag):
                node.decompose()

        # remove all attributes
        if not keep_attr:
            for tag in soup.find_all(True):
                tag.attrs = {}

        # remove comments
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        for comment in comments:
            comment.extract()

        # filter short text tags
        for node in soup.find_all():
            text = node.get_text(strip=True)
            if len(text) < 3:
                node.decompose()

    except Exception as e:
        print(e)

    res = str(soup)
    lines = [line for line in res.split("\n") if line.strip()]
    res = "\n".join(lines)
    res = clean_xml(res)
    return res, table_str, img_str, iframe_str, popup_str



def rank_tags_by_location(soup):
    def compute_importance_score(tag: Tag) -> float:
        score = TAG_SCORES.get(tag.name, 0)
        for parent in tag.parents:
            score += CONTAINER_SCORES.get(parent.name, 0)
        depth = len(list(tag.parents))
        if depth > 5:
            score -= (depth - 5) * 0.3
        return round(score, 2)

    def drop_supersets(texts: list[str]) -> list[str]:
        """
        containment(포함) 관계를 이용해
        ─ ① 자기보다 짧은 텍스트가 적어도 하나 있고
        ─ ② 자기보다 긴 텍스트가 적어도 하나 있는
        문자열만 남긴다.

        즉 ‘사슬’에서 **가장 짧은 것과 가장 긴 것**은 삭제.
        중간 길이(둘 다 만족)만 keep.
        """
        keep: list[str] = []

        for cur in texts:
            shorter_exists = any(t != cur and t in cur for t in texts)  # cur이 superset
            longer_exists = any(t != cur and cur in t for t in texts)  # cur이 subset

            if shorter_exists and longer_exists:  # 둘 다 TRUE → 중간 위치
                keep.append(cur)

        return keep

    soup = BeautifulSoup(soup, 'html.parser')
    best = {}
    all_text = []

    for tag in soup.find_all():
        if not isinstance(tag, Tag):
            continue
        text = tag.get('alt', '') if tag.name == 'img' else tag.get_text(strip=True)
        if not text or len(text) < 2:
            continue
        score = compute_importance_score(tag)
        if score <= 0:
            continue
        # 중복 텍스트는 최고 점수 항목만 남김
        prev = best.get(text)
        if prev is None or score > prev[0]:
            now_text = tag.get_text(strip=True)
            parent_text = tag.parent.get_text(strip=True)
            if now_text in parent_text:
                if now_text == parent_text:
                    continue
            diff_list = get_close_matches(now_text, all_text, n=5, cutoff=0.4)
            if diff_list:
                sort_list = sorted(diff_list, key=len, reverse=True)
                if len(now_text) > len(sort_list[0]):
                    all_text.remove(sort_list[0])
                    # all_text.append(now_text)
                else:
                    continue

            all_text.append(now_text)
            best[text] = (score, tag.name)

    # cand = {t: v for t, v in best.items()}
    # pruned_texts = drop_supersets(list(cand.keys()))

    # 4-D. 정렬 및 반환
    # results = [(cand[t][0], cand[t][1], t) for t in pruned_texts]
    # results.sort(key=lambda x: x[0], reverse=True)
    # 결과 정렬
    results = [(s, t, txt) for txt, (s, t) in best.items()]
    results.sort(key=lambda x: x[0], reverse=True)

    new_result = ""
    spare = 0
    for score, _, txt in results:
        if score > spare:
            new_result += txt
        elif score < spare:
            new_result += f"\n {txt}"
        else:
            new_result += f" | {txt}"
        spare = score
    return new_result


def dhkim_algorithm(html):
    soup = BeautifulSoup(html, 'html.parser')
    unimport_soup, table_str, img_str, iframe_str, popup_str = remove_unimportant_tags(soup)

    rank_soup = rank_tags_by_location(unimport_soup)

    result = f"{table_str}\n{img_str}\n{iframe_str}\n{popup_str}\n{rank_soup}"
    return result


def build_output(url: str):
    """
    Builds processed output documents from a given URL.

    This function takes a URL, ensures it is in a valid format, processes it to
    build its HTML content, applies a specific algorithm to analyze the content,
    and collects the results into a list of processed documents.

    Args:
        url: str
            The input URL to process.

    Returns:
        list:
            A list containing the analyzed documents generated from the given URL.
    """
    urls = [check_ensure_url(url)]
    all_docs = []
    for processed_url in urls:
        html = build_html_content(processed_url)
        result_v2 = dhkim_algorithm(html)
        all_docs.append(result_v2)

    return all_docs[0]