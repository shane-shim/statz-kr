# Statz-KR

사회인야구 세이버메트릭스 기록/분석 툴

## 주요 기능

- **경기 기록**: 타석별 결과 입력 (안타, 볼넷, 삼진 등)
- **투구 기록**: 이닝, 피안타, 자책점, 삼진 등
- **세이버메트릭스 자동 계산**
  - 타자: AVG, OBP, SLG, OPS, wOBA, ISO, BABIP, K%, BB%
  - 투수: ERA, WHIP, K/9, BB/9, FIP
- **대시보드**: 팀 성적, 타율/OPS 순위
- **Google Sheets 연동**: 클라우드 저장 및 팀원 공유

## 빠른 시작 (데모 모드)

```bash
# 프로젝트 폴더로 이동
cd /Users/jaewansim/Desktop/statz-kr

# 가상환경 생성 (선택사항)
python -m venv venv
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt

# 앱 실행
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속

> 데모 모드에서는 샘플 데이터로 바로 테스트할 수 있습니다.

## Google Sheets 연동 설정

### 1. Google Cloud 프로젝트 설정

1. [Google Cloud Console](https://console.cloud.google.com) 접속
2. 새 프로젝트 생성
3. Google Sheets API 활성화
4. 서비스 계정 생성 후 JSON 키 다운로드

### 2. Google Sheets 생성

1. 새 Google Sheets 문서 생성
2. 서비스 계정 이메일에 편집 권한 부여

### 3. 환경 변수 설정

```bash
export GOOGLE_CREDENTIALS_PATH="/path/to/credentials.json"
export STATZ_SPREADSHEET_URL="https://docs.google.com/spreadsheets/d/..."
```

### 4. 코드 수정

`app.py`에서 `MockSheetsDB`를 `SheetsDB`로 변경:

```python
def get_db():
    if 'db' not in st.session_state:
        st.session_state.db = SheetsDB()  # MockSheetsDB -> SheetsDB
        st.session_state.db.connect()
    return st.session_state.db
```

## 프로젝트 구조

```
statz-kr/
├── app.py              # Streamlit 웹 애플리케이션
├── sabermetrics.py     # 세이버메트릭스 계산 모듈
├── sheets_db.py        # Google Sheets 데이터베이스 모듈
├── requirements.txt    # Python 패키지 목록
└── README.md
```

## 세이버메트릭스 지표 설명

### 타격 지표

| 지표 | 설명 | 공식 |
|------|------|------|
| AVG | 타율 | 안타 / 타수 |
| OBP | 출루율 | (안타+볼넷+사구) / (타수+볼넷+사구+희생플라이) |
| SLG | 장타율 | 루타 / 타수 |
| OPS | 출루율+장타율 | OBP + SLG |
| wOBA | 가중출루율 | 가중치 적용된 출루 기여도 |
| ISO | 순장타율 | SLG - AVG |
| BABIP | 인플레이 타율 | (안타-홈런) / (타수-삼진-홈런+희생플라이) |

### 투구 지표

| 지표 | 설명 | 공식 |
|------|------|------|
| ERA | 평균자책점 | (자책점 × 9) / 이닝 |
| WHIP | 출루허용률 | (볼넷 + 피안타) / 이닝 |
| K/9 | 9이닝당 삼진 | (삼진 × 9) / 이닝 |
| BB/9 | 9이닝당 볼넷 | (볼넷 × 9) / 이닝 |
| FIP | 수비무관 평균자책점 | 투수 실력만 반영한 ERA |

## 라이선스

MIT License
