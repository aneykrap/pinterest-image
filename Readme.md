
### 패키지 설치

```bash
pip install -r requirements.txt
````

---

### `.env` 파일 생성

프로젝트 루트에 `.env` 파일 생성

```env
PINTEREST_EMAIL=your_email
PINTEREST_PASSWORD=your_password
```

---


## urls.txt 작성

- Pinterest 검색 URL을 **한 줄씩** 작성
- `#` 으로 시작하면 주석 처리

예시:

```txt
# spring outfit
https://www.pinterest.com/search/pins/?q=minimalist%20spring%20outfits&rs=typed
````

---

## collect_urls.py 설정
### 최대 스크롤 횟수 설정
```python
MAX_SCROLL = 10
```

* 최대 스크롤 횟수



### URL 간 대기 시간 수정

```python
time.sleep(60)
```

* 다음 URL 실행 전 대기 시간
* 숫자를 변경하여 조절 가능





