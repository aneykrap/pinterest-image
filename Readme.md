
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

### 검색 URL 설정

`collect_urls.py` 내부 `urls` 리스트 수정

```python
urls = [
    "https://www.pinterest.com/search/pins/?q=minimalist%20spring%20outfits&rs=typed",
]
```


