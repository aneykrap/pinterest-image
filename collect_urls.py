import os
import time
import random
import pandas as pd

from datetime import datetime
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from webdriver_manager.chrome import ChromeDriverManager


load_dotenv()

PINTEREST_EMAIL = os.getenv("PINTEREST_EMAIL")
PINTEREST_PASSWORD = os.getenv("PINTEREST_PASSWORD")

URL_FILE = "urls.txt"
OUTPUT_CSV = "pinterest_image_urls.csv"
CACHE_CSV = "crawl_cache.csv"

MAX_SCROLL = 10
STOP_IF_NO_NEW = 3


def load_urls(filename=URL_FILE):
    if not os.path.exists(filename):
        raise FileNotFoundError(f"{filename} 파일이 없습니다.")

    with open(filename, "r", encoding="utf-8") as f:
        urls = [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]

    if not urls:
        raise ValueError(f"{filename}에 수집할 URL이 없습니다.")

    return urls


def setup_driver():
    print("드라이버 설정 시작")

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--remote-allow-origins=*")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    print("드라이버 생성 완료")
    return driver


def login(driver):
    if not PINTEREST_EMAIL or not PINTEREST_PASSWORD:
        raise ValueError(".env에 PINTEREST_EMAIL 또는 PINTEREST_PASSWORD가 없습니다.")

    print("Pinterest 로그인 페이지 이동")
    driver.get("https://www.pinterest.com/login/")

    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.NAME, "id"))
    )

    print("로그인 정보 입력")
    driver.find_element(By.NAME, "id").send_keys(PINTEREST_EMAIL)
    driver.find_element(By.NAME, "password").send_keys(PINTEREST_PASSWORD)

    driver.find_element(By.XPATH, "//button[@type='submit']").click()
    time.sleep(8)

    print("로그인 후 URL:", driver.current_url)


def load_existing_urls(filename=OUTPUT_CSV):
    if not os.path.exists(filename):
        return set()

    df = pd.read_csv(filename)

    if "image_url" not in df.columns:
        return set()

    return set(df["image_url"].dropna().tolist())


def save_urls(data, filename=OUTPUT_CSV):
    if not data:
        print("새로 저장할 URL 데이터가 없습니다.")
        return

    new_df = pd.DataFrame(data)

    if os.path.exists(filename):
        old_df = pd.read_csv(filename)
        merged_df = pd.concat([old_df, new_df], ignore_index=True)
    else:
        merged_df = new_df

    merged_df = merged_df.drop_duplicates(subset=["image_url"]).reset_index(drop=True)
    merged_df.to_csv(filename, index=False, encoding="utf-8-sig")

    print(f"CSV 저장 완료: {filename}")
    print(f"전체 저장 URL 수: {len(merged_df)}")
    print(f"이번 실행 신규 URL 수: {len(new_df)}")


def load_cache(search_url):
    if not os.path.exists(CACHE_CSV):
        return 0, 0

    df = pd.read_csv(CACHE_CSV)
    matched = df[df["search_url"] == search_url]

    if matched.empty:
        return 0, 0

    row = matched.iloc[-1]
    return int(row["scroll_count"]), int(row["scroll_y"])


def save_cache(search_url, scroll_count, scroll_y):
    cache_row = pd.DataFrame([{
        "search_url": search_url,
        "scroll_count": scroll_count,
        "scroll_y": scroll_y,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }])

    if os.path.exists(CACHE_CSV):
        old_df = pd.read_csv(CACHE_CSV)
        old_df = old_df[old_df["search_url"] != search_url]
        cache_df = pd.concat([old_df, cache_row], ignore_index=True)
    else:
        cache_df = cache_row

    cache_df.to_csv(CACHE_CSV, index=False, encoding="utf-8-sig")


def restore_scroll_position(driver, scroll_y):
    if scroll_y <= 0:
        print("복원할 이전 스크롤 위치가 없습니다.")
        return

    print(f"이전 스크롤 위치 복원 시도: y={scroll_y}")

    step = 1500
    current = 0

    while current < scroll_y:
        current += step
        driver.execute_script(f"window.scrollTo(0, {current});")
        time.sleep(random.uniform(0.8, 1.5))

    print("스크롤 위치 복원 완료")


def collect_image_urls(driver, url, max_scroll=MAX_SCROLL, stop_if_no_new=STOP_IF_NO_NEW):
    image_data = []

    existing_urls = load_existing_urls()
    print(f"기존 CSV URL 수: {len(existing_urls)}")

    cached_scroll_count, cached_scroll_y = load_cache(url)
    print(f"캐시된 스크롤 횟수: {cached_scroll_count}")
    print(f"캐시된 스크롤 위치: {cached_scroll_y}")

    print(f"검색 URL 이동: {url}")
    driver.get(url)
    time.sleep(5)

    restore_scroll_position(driver, cached_scroll_y)

    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    search_term = query_params.get("q", [""])[0]

    print(f"추출된 검색어: {search_term}")
    print("현재 URL:", driver.current_url)
    print("페이지 제목:", driver.title)

    seen_urls = set()
    no_new_count = 0

    print("스크롤 시작")

    for i in range(max_scroll):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        sleep_time = random.uniform(2, 5)
        time.sleep(sleep_time)

        images = driver.find_elements(By.CSS_SELECTOR, "img[src]")

        before_count = len(seen_urls)
        duplicated_count = 0

        for img in images:
            try:
                src = img.get_attribute("src")

                if not src:
                    continue

                if src.endswith(".gif"):
                    continue

                if src in existing_urls:
                    duplicated_count += 1
                    continue

                if src in seen_urls:
                    continue

                seen_urls.add(src)

            except Exception as e:
                print(f"이미지 URL 처리 오류: {e}")

        after_count = len(seen_urls)
        new_count = after_count - before_count

        current_scroll_y = driver.execute_script("return window.scrollY;")
        total_scroll_count = cached_scroll_count + i + 1

        save_cache(url, total_scroll_count, current_scroll_y)

        print(
            f"{i + 1}/{max_scroll} 스크롤 완료 | "
            f"대기 {round(sleep_time, 2)}초 | "
            f"신규 URL {new_count}개 | "
            f"기존 URL {duplicated_count}개 | "
            f"이번 실행 누적 신규 URL {after_count}개 | "
            f"현재 scrollY {current_scroll_y}"
        )

        if new_count == 0:
            no_new_count += 1
            print(f"신규 URL 없음: {no_new_count}/{stop_if_no_new}")
        else:
            no_new_count = 0

        if no_new_count >= stop_if_no_new:
            print("신규 이미지가 더 이상 로딩되지 않아 수집 종료")
            break

    for src in seen_urls:
        image_data.append({
            "image_url": src,
            "search_term": search_term,
            "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    print(f"이번 실행 최종 신규 URL 수: {len(image_data)}")
    return image_data


def main():
    urls = load_urls()

    all_data = []

    print("URL 수집 시작")
    print(f"수집 대상 URL 수: {len(urls)}")

    driver = setup_driver()

    try:
        login(driver)

        for url in urls:
            data = collect_image_urls(
                driver,
                url,
                max_scroll=MAX_SCROLL,
                stop_if_no_new=STOP_IF_NO_NEW
            )

            all_data.extend(data)

            print("다음 URL 전 60초 대기")
            time.sleep(60)

    finally:
        print("브라우저 종료")
        driver.quit()

    save_urls(all_data)

    print("전체 URL 수집 완료")


if __name__ == "__main__":
    main()