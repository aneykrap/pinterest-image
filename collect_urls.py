import os
import time
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


def setup_driver():
    print("드라이버 설정 시작")

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--remote-allow-origins=*")
    options.add_argument("--disable-blink-features=AutomationControlled")

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

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


def save_urls(data, filename="pinterest_image_urls.csv"):
    if not data:
        print("저장할 URL 데이터가 없습니다.")
        return

    df = pd.DataFrame(data)

    if os.path.exists(filename):
        df.to_csv(filename, mode="a", header=False, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(filename, index=False, encoding="utf-8-sig")

    print(f"CSV 저장 완료: {filename}, {len(data)}개")


def collect_image_urls(url, max_scroll=5):
    driver = setup_driver()
    image_data = []

    try:
        login(driver)

        print(f"검색 URL 이동: {url}")
        driver.get(url)
        time.sleep(5)

        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        search_term = query_params.get("q", [""])[0]

        print(f"추출된 검색어: {search_term}")
        print("현재 URL:", driver.current_url)
        print("페이지 제목:", driver.title)

        print("스크롤 시작")
        for i in range(max_scroll):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            print(f"{i + 1}/{max_scroll} 스크롤 완료")
            time.sleep(3)

        print("이미지 태그 탐색 시작")
        images = driver.find_elements(By.CSS_SELECTOR, "img[src]")
        print(f"찾은 이미지 태그 수: {len(images)}")

        seen_urls = set()

        for img in images:
            try:
                src = img.get_attribute("src")

                if not src:
                    continue

                if src.endswith(".gif"):
                    continue

                if src in seen_urls:
                    continue

                seen_urls.add(src)

                image_data.append({
                    "image_url": src,
                    "search_term": search_term,
                    "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

            except Exception as e:
                print(f"이미지 URL 처리 오류: {e}")

        print(f"최종 수집 URL 수: {len(image_data)}")
        return image_data

    except Exception as e:
        print(f"URL 수집 중 오류 발생: {e}")
        return []

    finally:
        print("브라우저 종료")
        driver.quit()


def main():
    urls = [
        "https://www.pinterest.com/search/pins/?q=minimalist%20spring%20outfits&rs=typed",
        "https://www.pinterest.com/search/pins/?q=casual%20summer%20outfit%20women&rs=typed",
        "https://www.pinterest.com/search/pins/?q=streetwear%20outfit%20women&rs=typed",
    ]

    all_data = []

    print("URL 수집 시작")

    for url in urls:
        data = collect_image_urls(url, max_scroll=5)
        all_data.extend(data)

        print("다음 URL 전 60초 대기")
        time.sleep(60)

    save_urls(all_data)

    print("전체 URL 수집 완료")


if __name__ == "__main__":
    main()