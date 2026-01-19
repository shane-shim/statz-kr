"""
Google Sheets 데이터베이스 모듈
선수, 경기, 타석 기록을 Google Sheets에 저장/조회
"""

import json
import os
from datetime import datetime
from typing import Optional

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# Google Sheets API 스코프
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# 시트 이름
SHEET_PLAYERS = "선수"
SHEET_GAMES = "경기"
SHEET_AT_BATS = "타석기록"
SHEET_PITCHING = "투구기록"
SHEET_ATTENDANCE = "참석기록"


class SheetsDB:
    """Google Sheets 기반 데이터베이스"""

    def __init__(self, credentials_path: Optional[str] = None, spreadsheet_url: Optional[str] = None):
        self.credentials_path = credentials_path or os.environ.get('GOOGLE_CREDENTIALS_PATH')
        self.spreadsheet_url = spreadsheet_url or os.environ.get('STATZ_SPREADSHEET_URL')
        self._client = None
        self._spreadsheet = None
        self._sheet_cache = {}  # 워크시트 캐싱

    def connect(self):
        """Google Sheets에 연결"""
        if self.credentials_path and os.path.exists(self.credentials_path):
            creds = Credentials.from_service_account_file(self.credentials_path, scopes=SCOPES)
            self._client = gspread.authorize(creds)
        else:
            creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
            if creds_json:
                creds_dict = json.loads(creds_json)
                creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
                self._client = gspread.authorize(creds)
            else:
                raise ValueError("Google credentials not found.")

        if self.spreadsheet_url:
            self._spreadsheet = self._client.open_by_url(self.spreadsheet_url)
        else:
            raise ValueError("Spreadsheet URL not set.")

    def _get_or_create_sheet(self, title: str, headers: list) -> gspread.Worksheet:
        """시트 가져오기 또는 생성 (캐싱)"""
        if title in self._sheet_cache:
            return self._sheet_cache[title]

        try:
            worksheet = self._spreadsheet.worksheet(title)
        except gspread.WorksheetNotFound:
            worksheet = self._spreadsheet.add_worksheet(title=title, rows=1000, cols=len(headers))
            worksheet.append_row(headers)

        self._sheet_cache[title] = worksheet
        return worksheet

    # === 선수 관리 ===

    def get_players_sheet(self) -> gspread.Worksheet:
        headers = ["선수ID", "이름", "등번호", "포지션", "투타", "생성일"]
        return self._get_or_create_sheet(SHEET_PLAYERS, headers)

    def add_player(self, name: str, number: int, position: str, bat_throw: str) -> str:
        sheet = self.get_players_sheet()
        player_id = f"P{datetime.now().strftime('%Y%m%d%H%M%S')}"
        sheet.append_row([player_id, name, number, position, bat_throw, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        return player_id

    def get_players(self) -> pd.DataFrame:
        sheet = self.get_players_sheet()
        data = sheet.get_all_records()
        return pd.DataFrame(data)

    def get_player_by_name(self, name: str) -> Optional[dict]:
        df = self.get_players()
        matches = df[df['이름'] == name]
        if len(matches) > 0:
            return matches.iloc[0].to_dict()
        return None

    # === 경기 관리 ===

    def get_games_sheet(self) -> gspread.Worksheet:
        headers = ["경기ID", "날짜", "상대팀", "홈/원정", "우리점수", "상대점수", "결과", "구장", "메모"]
        return self._get_or_create_sheet(SHEET_GAMES, headers)

    def add_game(self, date: str, opponent: str, home_away: str,
                 our_score: int, their_score: int, stadium: str = "", memo: str = "") -> str:
        sheet = self.get_games_sheet()
        game_id = f"G{datetime.now().strftime('%Y%m%d%H%M%S')}"
        if our_score > their_score:
            result = "승"
        elif our_score < their_score:
            result = "패"
        else:
            result = "무"
        sheet.append_row([game_id, date, opponent, home_away, our_score, their_score, result, stadium, memo])
        return game_id

    def get_games(self) -> pd.DataFrame:
        sheet = self.get_games_sheet()
        data = sheet.get_all_records()
        return pd.DataFrame(data)

    # === 타석 기록 ===

    def get_at_bats_sheet(self) -> gspread.Worksheet:
        headers = ["기록ID", "경기ID", "선수ID", "선수명", "이닝", "타순",
                   "결과", "안타종류", "타점", "득점", "도루", "도실",
                   "볼넷", "삼진", "사구", "희생플라이", "희생번트", "기록일시"]
        return self._get_or_create_sheet(SHEET_AT_BATS, headers)

    def add_at_bat(self, game_id: str, player_id: str, player_name: str,
                   inning: int, batting_order: int, result: str,
                   hit_type: str = "", rbis: int = 0, runs: int = 0,
                   stolen_bases: int = 0, caught_stealing: int = 0,
                   walks: int = 0, strikeouts: int = 0, hit_by_pitch: int = 0,
                   sacrifice_flies: int = 0, sacrifice_bunts: int = 0) -> str:
        sheet = self.get_at_bats_sheet()
        record_id = f"AB{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        sheet.append_row([record_id, game_id, player_id, player_name, inning, batting_order,
                          result, hit_type, rbis, runs, stolen_bases, caught_stealing,
                          walks, strikeouts, hit_by_pitch, sacrifice_flies, sacrifice_bunts,
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        return record_id

    def add_at_bats_batch(self, records: list) -> int:
        """타석 기록 배치 추가 (API 호출 최소화)"""
        if not records:
            return 0
        sheet = self.get_at_bats_sheet()
        rows = []
        for r in records:
            record_id = f"AB{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            rows.append([
                record_id, r['game_id'], r['player_id'], r['player_name'],
                r['inning'], r['batting_order'], r['result'], r['hit_type'],
                r['rbis'], r['runs'], r['stolen_bases'], r['caught_stealing'],
                r['walks'], r['strikeouts'], r['hit_by_pitch'],
                r['sacrifice_flies'], r['sacrifice_bunts'],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ])
        sheet.append_rows(rows)
        return len(rows)

    def get_at_bats(self, game_id: Optional[str] = None, player_id: Optional[str] = None) -> pd.DataFrame:
        sheet = self.get_at_bats_sheet()
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if game_id and len(df) > 0:
            df = df[df['경기ID'] == game_id]
        if player_id and len(df) > 0:
            df = df[df['선수ID'] == player_id]
        return df

    # === 투구 기록 ===

    def get_pitching_sheet(self) -> gspread.Worksheet:
        headers = ["기록ID", "경기ID", "선수ID", "선수명",
                   "이닝", "피안타", "실점", "자책", "볼넷", "삼진", "피홈런",
                   "승", "패", "세이브", "기록일시"]
        return self._get_or_create_sheet(SHEET_PITCHING, headers)

    def add_pitching(self, game_id: str, player_id: str, player_name: str,
                     innings: float, hits: int, runs: int, earned_runs: int,
                     walks: int, strikeouts: int, home_runs: int = 0,
                     win: bool = False, loss: bool = False, save: bool = False) -> str:
        sheet = self.get_pitching_sheet()
        record_id = f"P{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        sheet.append_row([record_id, game_id, player_id, player_name,
                          innings, hits, runs, earned_runs, walks, strikeouts, home_runs,
                          1 if win else 0, 1 if loss else 0, 1 if save else 0,
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        return record_id

    def get_pitching(self, game_id: Optional[str] = None, player_id: Optional[str] = None) -> pd.DataFrame:
        sheet = self.get_pitching_sheet()
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if game_id and len(df) > 0:
            df = df[df['경기ID'] == game_id]
        if player_id and len(df) > 0:
            df = df[df['선수ID'] == player_id]
        return df

    # === 참석 기록 ===

    def get_attendance_sheet(self) -> gspread.Worksheet:
        headers = ["기록ID", "경기ID", "경기일", "선수ID", "선수명", "참석여부", "사유", "기록일시"]
        return self._get_or_create_sheet(SHEET_ATTENDANCE, headers)

    def add_attendance(self, game_id: str, game_date: str, player_id: str, player_name: str,
                       attended: bool, reason: str = "") -> str:
        """참석 기록 추가"""
        sheet = self.get_attendance_sheet()
        record_id = f"ATT{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        sheet.append_row([
            record_id, game_id, game_date, player_id, player_name,
            "참석" if attended else "불참", reason,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ])
        return record_id

    def add_attendance_batch(self, records: list) -> int:
        """참석 기록 배치 추가"""
        if not records:
            return 0
        sheet = self.get_attendance_sheet()
        rows = []
        for r in records:
            record_id = f"ATT{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            rows.append([
                record_id, r['game_id'], r['game_date'], r['player_id'], r['player_name'],
                "참석" if r['attended'] else "불참", r.get('reason', ''),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ])
        sheet.append_rows(rows)
        return len(rows)

    def get_attendance(self, game_id: Optional[str] = None, player_id: Optional[str] = None) -> pd.DataFrame:
        """참석 기록 조회"""
        sheet = self.get_attendance_sheet()
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if game_id and len(df) > 0:
            df = df[df['경기ID'] == game_id]
        if player_id and len(df) > 0:
            df = df[df['선수ID'] == player_id]
        return df

    def get_attendance_stats(self) -> pd.DataFrame:
        """선수별 참석률 통계"""
        df = self.get_attendance()
        if len(df) == 0:
            return pd.DataFrame(columns=['선수명', '총경기', '참석', '불참', '참석률'])

        stats = df.groupby(['선수ID', '선수명']).agg(
            총경기=('기록ID', 'count'),
            참석=('참석여부', lambda x: (x == '참석').sum())
        ).reset_index()
        stats['불참'] = stats['총경기'] - stats['참석']
        stats['참석률'] = (stats['참석'] / stats['총경기'] * 100).round(1)
        return stats[['선수명', '총경기', '참석', '불참', '참석률']].sort_values('참석률', ascending=False)


class SheetsDBFromSecrets(SheetsDB):
    """Streamlit Cloud secrets용 Google Sheets 데이터베이스"""

    def __init__(self, credentials_dict: dict, spreadsheet_url: str):
        super().__init__()
        self.credentials_dict = credentials_dict
        self.spreadsheet_url = spreadsheet_url

    def connect(self):
        """Google Sheets에 연결 (secrets 사용)"""
        creds = Credentials.from_service_account_info(self.credentials_dict, scopes=SCOPES)
        self._client = gspread.authorize(creds)
        self._spreadsheet = self._client.open_by_url(self.spreadsheet_url)


class MockSheetsDB:
    """테스트/데모용 Mock 데이터베이스"""

    def __init__(self):
        self.players = pd.DataFrame(columns=["선수ID", "이름", "등번호", "포지션", "투타", "생성일"])
        self.games = pd.DataFrame(columns=["경기ID", "날짜", "상대팀", "홈/원정", "우리점수", "상대점수", "결과", "구장", "메모"])
        self.at_bats = pd.DataFrame(columns=["기록ID", "경기ID", "선수ID", "선수명", "이닝", "타순",
                                              "결과", "안타종류", "타점", "득점", "도루", "도실",
                                              "볼넷", "삼진", "사구", "희생플라이", "희생번트", "기록일시"])
        self.pitching = pd.DataFrame(columns=["기록ID", "경기ID", "선수ID", "선수명",
                                               "이닝", "피안타", "실점", "자책", "볼넷", "삼진", "피홈런",
                                               "승", "패", "세이브", "기록일시"])

    def connect(self):
        pass

    def add_player(self, name: str, number: int, position: str, bat_throw: str) -> str:
        player_id = f"P{len(self.players) + 1:03d}"
        new_row = pd.DataFrame([{"선수ID": player_id, "이름": name, "등번호": number,
                                  "포지션": position, "투타": bat_throw,
                                  "생성일": datetime.now().strftime("%Y-%m-%d")}])
        self.players = pd.concat([self.players, new_row], ignore_index=True)
        return player_id

    def get_players(self) -> pd.DataFrame:
        return self.players.copy()

    def get_player_by_name(self, name: str) -> Optional[dict]:
        matches = self.players[self.players['이름'] == name]
        if len(matches) > 0:
            return matches.iloc[0].to_dict()
        return None

    def add_game(self, date: str, opponent: str, home_away: str,
                 our_score: int, their_score: int, stadium: str = "", memo: str = "") -> str:
        game_id = f"G{len(self.games) + 1:03d}"
        if our_score > their_score:
            result = "승"
        elif our_score < their_score:
            result = "패"
        else:
            result = "무"
        new_row = pd.DataFrame([{"경기ID": game_id, "날짜": date, "상대팀": opponent,
                                  "홈/원정": home_away, "우리점수": our_score,
                                  "상대점수": their_score, "결과": result,
                                  "구장": stadium, "메모": memo}])
        self.games = pd.concat([self.games, new_row], ignore_index=True)
        return game_id

    def get_games(self) -> pd.DataFrame:
        return self.games.copy()

    def add_at_bat(self, game_id: str, player_id: str, player_name: str,
                   inning: int, batting_order: int, result: str,
                   hit_type: str = "", rbis: int = 0, runs: int = 0,
                   stolen_bases: int = 0, caught_stealing: int = 0,
                   walks: int = 0, strikeouts: int = 0, hit_by_pitch: int = 0,
                   sacrifice_flies: int = 0, sacrifice_bunts: int = 0) -> str:
        record_id = f"AB{len(self.at_bats) + 1:03d}"
        new_row = pd.DataFrame([{"기록ID": record_id, "경기ID": game_id, "선수ID": player_id,
                                  "선수명": player_name, "이닝": inning, "타순": batting_order,
                                  "결과": result, "안타종류": hit_type, "타점": rbis, "득점": runs,
                                  "도루": stolen_bases, "도실": caught_stealing,
                                  "볼넷": walks, "삼진": strikeouts, "사구": hit_by_pitch,
                                  "희생플라이": sacrifice_flies, "희생번트": sacrifice_bunts,
                                  "기록일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
        self.at_bats = pd.concat([self.at_bats, new_row], ignore_index=True)
        return record_id

    def get_at_bats(self, game_id: Optional[str] = None, player_id: Optional[str] = None) -> pd.DataFrame:
        df = self.at_bats.copy()
        if game_id and len(df) > 0:
            df = df[df['경기ID'] == game_id]
        if player_id and len(df) > 0:
            df = df[df['선수ID'] == player_id]
        return df

    def add_pitching(self, game_id: str, player_id: str, player_name: str,
                     innings: float, hits: int, runs: int, earned_runs: int,
                     walks: int, strikeouts: int, home_runs: int = 0,
                     win: bool = False, loss: bool = False, save: bool = False) -> str:
        record_id = f"PT{len(self.pitching) + 1:03d}"
        new_row = pd.DataFrame([{"기록ID": record_id, "경기ID": game_id, "선수ID": player_id,
                                  "선수명": player_name, "이닝": innings, "피안타": hits,
                                  "실점": runs, "자책": earned_runs, "볼넷": walks,
                                  "삼진": strikeouts, "피홈런": home_runs,
                                  "승": 1 if win else 0, "패": 1 if loss else 0,
                                  "세이브": 1 if save else 0,
                                  "기록일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
        self.pitching = pd.concat([self.pitching, new_row], ignore_index=True)
        return record_id

    def get_pitching(self, game_id: Optional[str] = None, player_id: Optional[str] = None) -> pd.DataFrame:
        df = self.pitching.copy()
        if game_id and len(df) > 0:
            df = df[df['경기ID'] == game_id]
        if player_id and len(df) > 0:
            df = df[df['선수ID'] == player_id]
        return df
