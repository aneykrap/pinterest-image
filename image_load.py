import os
import time
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

INPUT_CSV = "pinterest_image_urls.csv"
SAVE_DIR = "pinterest_images"

MAX_WORKERS = 10      # 동시에 10개 다운로드
TIMEOUT = 15

os.makedirs(SAVE_DIR, exist_ok=True)


def make_filename(idx, url, search_term):
    parsed = urlparse(url)
    ext = os.path.splitext(parsed.path)[1]

    if ext.lower() not in [".jpg", ".jpeg", ".png", ".webp"]:
        ext = ".jpg"

    safe_term = str(search_term).replace(" ", "_").replace("/", "_")
    return f"{idx}_{safe_term}{ext}"


def download_one(idx, row):
    url = row["image_url"]
    search_term = row.get("search_term", "unknown")

    filename = make_filename(idx, url, search_term)
    path = os.path.join(SAVE_DIR, filename)

    if os.path.exists(path):
        return {
            "idx": idx,
            "success": True,
            "status": "skip",
            "filename": filename,
            "elapsed": 0
        }

    try:
        start = time.time()

        response = requests.get(
            url,
            timeout=TIMEOUT,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        elapsed = time.time() - start

        if response.status_code == 200:
            with open(path, "wb") as f:
                f.write(response.content)

            return {
                "idx": idx,
                "success": True,
                "status": "downloaded",
                "filename": filename,
                "elapsed": round(elapsed, 2)
            }

        return {
            "idx": idx,
            "success": False,
            "status": f"http_{response.status_code}",
            "filename": filename,
            "elapsed": round(elapsed, 2)
        }

    except Exception as e:
        return {
            "idx": idx,
            "success": False,
            "status": str(e),
            "filename": filename,
            "elapsed": 0
        }


def main():
    df = pd.read_csv(INPUT_CSV)
    df = df.drop_duplicates(subset=["image_url"]).reset_index(drop=True)

    print(f"다운로드 대상 URL 수: {len(df)}")
    print(f"동시 다운로드 수: {MAX_WORKERS}")

    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(download_one, idx, row)
            for idx, row in df.iterrows()
        ]

        for count, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            results.append(result)

            print(
                f"[{count}/{len(df)}] "
                f"{result['status']} | "
                f"{result['filename']} | "
                f"{result['elapsed']}초"
            )

    pd.DataFrame(results).to_csv(
        "download_log.csv",
        index=False,
        encoding="utf-8-sig"
    )

    success_count = sum(1 for r in results if r["success"])
    fail_count = len(results) - success_count

    print("다운로드 완료")
    print(f"성공: {success_count}")
    print(f"실패: {fail_count}")


if __name__ == "__main__":
    main()