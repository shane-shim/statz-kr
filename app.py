"""
미라클 동산 전용 세이버메트릭스
Streamlit 웹 애플리케이션
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from sabermetrics import (
    BattingStats, PitchingStats, SabermetricsCalculator,
    format_avg, format_era, format_percentage
)
from sheets_db import MockSheetsDB, SheetsDB
import time

# 페이지 설정
st.set_page_config(
    page_title="미라클 동산",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 스타일
st.markdown("""
<style>
    .stat-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .stat-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .stat-label {
        font-size: 0.9rem;
        color: #666;
    }
    .big-stat {
        font-size: 3rem;
        font-weight: bold;
    }
    .grade-excellent { color: #1e88e5; font-weight: bold; }
    .grade-good { color: #43a047; font-weight: bold; }
    .grade-average { color: #ff9800; font-weight: bold; }
    .grade-below { color: #e53935; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


# === 등급 기준 (사회인야구 기준) ===
GRADE_CRITERIA = {
    'AVG': [(0.350, '훌륭함', '#1e88e5'), (0.300, '좋음', '#43a047'), (0.250, '보통', '#ff9800'), (0.200, '개선필요', '#e53935'), (0, '부진', '#b71c1c')],
    'OBP': [(0.420, '훌륭함', '#1e88e5'), (0.360, '좋음', '#43a047'), (0.300, '보통', '#ff9800'), (0.250, '개선필요', '#e53935'), (0, '부진', '#b71c1c')],
    'SLG': [(0.550, '훌륭함', '#1e88e5'), (0.450, '좋음', '#43a047'), (0.350, '보통', '#ff9800'), (0.250, '개선필요', '#e53935'), (0, '부진', '#b71c1c')],
    'OPS': [(0.950, '훌륭함', '#1e88e5'), (0.800, '좋음', '#43a047'), (0.650, '보통', '#ff9800'), (0.550, '개선필요', '#e53935'), (0, '부진', '#b71c1c')],
    'wOBA': [(0.400, '훌륭함', '#1e88e5'), (0.340, '좋음', '#43a047'), (0.300, '보통', '#ff9800'), (0.250, '개선필요', '#e53935'), (0, '부진', '#b71c1c')],
    'ERA': [(2.50, '훌륭함', '#1e88e5'), (3.50, '좋음', '#43a047'), (4.50, '보통', '#ff9800'), (5.50, '개선필요', '#e53935'), (99, '부진', '#b71c1c')],
    'WHIP': [(1.00, '훌륭함', '#1e88e5'), (1.25, '좋음', '#43a047'), (1.50, '보통', '#ff9800'), (1.75, '개선필요', '#e53935'), (99, '부진', '#b71c1c')],
}


def get_grade(stat_name: str, value: float) -> tuple:
    """지표값에 대한 등급과 색상 반환"""
    if value is None:
        return ('-', '#666666')

    criteria = GRADE_CRITERIA.get(stat_name, [])

    # ERA, WHIP는 낮을수록 좋음
    if stat_name in ['ERA', 'WHIP']:
        for threshold, grade, color in criteria:
            if value <= threshold:
                return (grade, color)
    else:
        for threshold, grade, color in criteria:
            if value >= threshold:
                return (grade, color)

    return ('부진', '#b71c1c')


def display_stat_with_grade(label: str, value, stat_name: str = None, format_str: str = ".3f"):
    """등급과 함께 지표 표시"""
    if value is None:
        st.markdown(f"""
        <div style="text-align: center; padding: 10px; background: #f5f5f5; border-radius: 8px; margin: 5px 0;">
            <div style="font-size: 0.85rem; color: #666;">{label}</div>
            <div style="font-size: 1.8rem; font-weight: bold;">-</div>
        </div>
        """, unsafe_allow_html=True)
        return

    if stat_name:
        grade, color = get_grade(stat_name, value)
        grade_html = f'<span style="color: {color}; font-size: 0.75rem;">({grade})</span>'
    else:
        grade_html = ''

    formatted_value = f"{value:{format_str}}" if isinstance(value, float) else str(value)

    st.markdown(f"""
    <div style="text-align: center; padding: 10px; background: #f5f5f5; border-radius: 8px; margin: 5px 0;">
        <div style="font-size: 0.85rem; color: #666;">{label}</div>
        <div style="font-size: 1.8rem; font-weight: bold;">{formatted_value}</div>
        {grade_html}
    </div>
    """, unsafe_allow_html=True)


def show_grade_legend():
    """등급 범례 표시"""
    st.markdown("""
    <div style="display: flex; gap: 15px; justify-content: center; padding: 10px; background: #fafafa; border-radius: 8px; margin: 10px 0;">
        <span><span style="color: #1e88e5;">●</span> 훌륭함</span>
        <span><span style="color: #43a047;">●</span> 좋음</span>
        <span><span style="color: #ff9800;">●</span> 보통</span>
        <span><span style="color: #e53935;">●</span> 개선필요</span>
    </div>
    """, unsafe_allow_html=True)


def get_db():
    """데이터베이스 인스턴스 가져오기"""
    if 'db' not in st.session_state:
        # Streamlit Cloud secrets 또는 로컬 credentials 사용
        try:
            # Streamlit Cloud 환경
            from sheets_db import SheetsDBFromSecrets
            st.session_state.db = SheetsDBFromSecrets(
                credentials_dict=dict(st.secrets["gcp_service_account"]),
                spreadsheet_url=st.secrets["spreadsheet_url"]
            )
        except (FileNotFoundError, KeyError):
            # 로컬 환경
            st.session_state.db = SheetsDB(
                credentials_path="credentials.json",
                spreadsheet_url="https://docs.google.com/spreadsheets/d/1rcWR_qwVAo_PU0ecO4_gVpWjolOq07Uifs0NlqTn5FY/edit"
            )
        st.session_state.db.connect()
    return st.session_state.db


@st.cache_data(ttl=60)  # 60초 캐싱
def load_games(_db):
    """경기 데이터 캐싱 로드"""
    return _db.get_games()


@st.cache_data(ttl=60)
def load_players(_db):
    """선수 데이터 캐싱 로드"""
    return _db.get_players()


@st.cache_data(ttl=60)
def load_at_bats(_db, game_id=None, player_id=None):
    """타석 데이터 캐싱 로드"""
    return _db.get_at_bats(game_id=game_id, player_id=player_id)


@st.cache_data(ttl=60)
def load_pitching(_db, game_id=None, player_id=None):
    """투구 데이터 캐싱 로드"""
    return _db.get_pitching(game_id=game_id, player_id=player_id)


def calculate_player_batting_stats(df: pd.DataFrame) -> BattingStats:
    """타석 기록 DataFrame에서 BattingStats 계산"""
    stats = BattingStats()

    if len(df) == 0:
        return stats

    # 타석 수
    stats.plate_appearances = len(df)

    # 결과별 집계
    for _, row in df.iterrows():
        result = row.get('결과', '')
        hit_type = row.get('안타종류', '')

        # 안타 종류 분류
        if result == '안타':
            stats.hits += 1
            if hit_type == '1루타':
                pass  # singles는 property로 계산
            elif hit_type == '2루타':
                stats.doubles += 1
            elif hit_type == '3루타':
                stats.triples += 1
            elif hit_type == '홈런':
                stats.home_runs += 1

        # 볼넷, 삼진 등
        stats.walks += int(row.get('볼넷', 0))
        stats.strikeouts += int(row.get('삼진', 0))
        stats.hit_by_pitch += int(row.get('사구', 0))
        stats.sacrifice_flies += int(row.get('희생플라이', 0))
        stats.sacrifice_bunts += int(row.get('희생번트', 0))
        stats.rbis += int(row.get('타점', 0))
        stats.runs += int(row.get('득점', 0))
        stats.stolen_bases += int(row.get('도루', 0))
        stats.caught_stealing += int(row.get('도실', 0))

    # 타수 = 타석 - 볼넷 - 사구 - 희생플라이 - 희생번트
    stats.at_bats = stats.plate_appearances - stats.walks - stats.hit_by_pitch - stats.sacrifice_flies - stats.sacrifice_bunts

    return stats


def calculate_player_pitching_stats(df: pd.DataFrame) -> PitchingStats:
    """투구 기록 DataFrame에서 PitchingStats 계산"""
    stats = PitchingStats()

    if len(df) == 0:
        return stats

    for _, row in df.iterrows():
        stats.innings_pitched += float(row.get('이닝', 0))
        stats.hits_allowed += int(row.get('피안타', 0))
        stats.runs_allowed += int(row.get('실점', 0))
        stats.earned_runs += int(row.get('자책', 0))
        stats.walks += int(row.get('볼넷', 0))
        stats.strikeouts += int(row.get('삼진', 0))
        stats.home_runs_allowed += int(row.get('피홈런', 0))
        stats.wins += int(row.get('승', 0))
        stats.losses += int(row.get('패', 0))
        stats.saves += int(row.get('세이브', 0))

    return stats


# ===== 메인 앱 =====

def main():
    db = get_db()

    # 사이드바 - 네비게이션
    st.sidebar.title("⚾ 미라클 동산")
    st.sidebar.markdown("전용 세이버메트릭스")
    st.sidebar.divider()

    menu = st.sidebar.radio(
        "메뉴",
        ["대시보드", "성장 리포트", "팀 인사이트", "경기 기록", "선수 통계", "선수 관리", "경기 관리"],
        label_visibility="collapsed"
    )

    if menu == "대시보드":
        show_dashboard(db)
    elif menu == "성장 리포트":
        show_growth_report(db)
    elif menu == "팀 인사이트":
        show_team_insight(db)
    elif menu == "경기 기록":
        show_game_recording(db)
    elif menu == "선수 통계":
        show_player_stats(db)
    elif menu == "선수 관리":
        show_player_management(db)
    elif menu == "경기 관리":
        show_game_management(db)


def show_dashboard(db):
    """대시보드 화면"""
    st.title("대시보드")

    try:
        games = load_games(db)
        players = load_players(db)
    except Exception as e:
        st.error("데이터를 불러오는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
        st.caption(f"오류: {type(e).__name__}")
        if st.button("새로고침"):
            st.cache_data.clear()
            st.rerun()
        return

    # 팀 성적 요약
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("총 경기", len(games))
    with col2:
        wins = len(games[games['결과'] == '승']) if len(games) > 0 else 0
        st.metric("승리", wins)
    with col3:
        losses = len(games[games['결과'] == '패']) if len(games) > 0 else 0
        st.metric("패배", losses)
    with col4:
        if len(games) > 0:
            win_rate = wins / len(games) * 100
            st.metric("승률", f"{win_rate:.1f}%")
        else:
            st.metric("승률", "-")

    st.divider()

    # 상위 타자 순위
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("타율 TOP 5")
        at_bats = load_at_bats(db)
        if len(at_bats) > 0:
            player_avgs = []
            for player_id in at_bats['선수ID'].unique():
                player_abs = at_bats[at_bats['선수ID'] == player_id]
                player_name = player_abs['선수명'].iloc[0]
                stats = calculate_player_batting_stats(player_abs)
                if stats.at_bats >= 5:  # 최소 5타수
                    avg = SabermetricsCalculator.avg(stats)
                    if avg:
                        player_avgs.append({
                            '선수': player_name,
                            '타율': avg,
                            '타수': stats.at_bats,
                            '안타': stats.hits
                        })

            if player_avgs:
                avg_df = pd.DataFrame(player_avgs)
                avg_df = avg_df.sort_values('타율', ascending=False).head(5)
                avg_df['타율'] = avg_df['타율'].apply(lambda x: f"{x:.3f}")
                st.dataframe(avg_df, hide_index=True, use_container_width=True)
            else:
                st.info("충분한 타석 기록이 없습니다.")
        else:
            st.info("기록된 타석이 없습니다.")

    with col2:
        st.subheader("OPS TOP 5")
        if len(at_bats) > 0:
            player_ops = []
            for player_id in at_bats['선수ID'].unique():
                player_abs = at_bats[at_bats['선수ID'] == player_id]
                player_name = player_abs['선수명'].iloc[0]
                stats = calculate_player_batting_stats(player_abs)
                if stats.at_bats >= 5:
                    ops = SabermetricsCalculator.ops(stats)
                    if ops:
                        player_ops.append({
                            '선수': player_name,
                            'OPS': ops,
                            'OBP': SabermetricsCalculator.obp(stats),
                            'SLG': SabermetricsCalculator.slg(stats)
                        })

            if player_ops:
                ops_df = pd.DataFrame(player_ops)
                ops_df = ops_df.sort_values('OPS', ascending=False).head(5)
                ops_df['OPS'] = ops_df['OPS'].apply(lambda x: f"{x:.3f}")
                ops_df['OBP'] = ops_df['OBP'].apply(lambda x: f"{x:.3f}" if x else "-")
                ops_df['SLG'] = ops_df['SLG'].apply(lambda x: f"{x:.3f}" if x else "-")
                st.dataframe(ops_df, hide_index=True, use_container_width=True)
            else:
                st.info("충분한 타석 기록이 없습니다.")
        else:
            st.info("기록된 타석이 없습니다.")

    # 최근 경기
    st.divider()
    st.subheader("최근 경기")
    if len(games) > 0:
        recent_games = games.tail(5).iloc[::-1]
        st.dataframe(
            recent_games[['날짜', '상대팀', '홈/원정', '우리점수', '상대점수', '결과']],
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("등록된 경기가 없습니다.")


def show_game_recording(db):
    """경기 기록 화면"""
    st.title("경기 기록 입력")

    games = load_games(db)
    players = load_players(db)

    if len(games) == 0:
        st.warning("먼저 경기를 등록해주세요.")
        return

    if len(players) == 0:
        st.warning("먼저 선수를 등록해주세요.")
        return

    # 경기 선택
    game_options = {f"{row['날짜']} vs {row['상대팀']}": row['경기ID']
                    for _, row in games.iterrows()}
    selected_game = st.selectbox("경기 선택", list(game_options.keys()))
    game_id = game_options[selected_game]

    st.divider()

    # 탭: 타격/투구
    tab1, tab2 = st.tabs(["타격 기록", "투구 기록"])

    with tab1:
        st.subheader("타격 기록 입력")

        col1, col2 = st.columns(2)

        with col1:
            player_options = {row['이름']: (row['선수ID'], row['이름'])
                              for _, row in players.iterrows()}
            selected_player = st.selectbox("선수", list(player_options.keys()), key="batting_player")
            player_id, player_name = player_options[selected_player]

            inning = st.number_input("이닝", min_value=1, max_value=12, value=1)
            batting_order = st.number_input("타순", min_value=1, max_value=9, value=1)

        with col2:
            result = st.selectbox("결과", ["안타", "아웃", "볼넷", "삼진", "사구", "희생플라이", "희생번트", "에러출루"])

            if result == "안타":
                hit_type = st.selectbox("안타 종류", ["1루타", "2루타", "3루타", "홈런"])
            else:
                hit_type = ""

            rbis = st.number_input("타점", min_value=0, max_value=4, value=0)
            runs = st.selectbox("득점", [0, 1], format_func=lambda x: "득점" if x == 1 else "-")

        col3, col4 = st.columns(2)
        with col3:
            stolen = st.number_input("도루", min_value=0, max_value=3, value=0)
        with col4:
            caught = st.number_input("도루실패", min_value=0, max_value=3, value=0)

        if st.button("타석 기록 저장", type="primary"):
            # 결과에 따른 플래그 설정
            walks = 1 if result == "볼넷" else 0
            strikeouts = 1 if result == "삼진" else 0
            hit_by_pitch = 1 if result == "사구" else 0
            sacrifice_flies = 1 if result == "희생플라이" else 0
            sacrifice_bunts = 1 if result == "희생번트" else 0

            db.add_at_bat(
                game_id=game_id,
                player_id=player_id,
                player_name=player_name,
                inning=inning,
                batting_order=batting_order,
                result=result,
                hit_type=hit_type,
                rbis=rbis,
                runs=runs,
                stolen_bases=stolen,
                caught_stealing=caught,
                walks=walks,
                strikeouts=strikeouts,
                hit_by_pitch=hit_by_pitch,
                sacrifice_flies=sacrifice_flies,
                sacrifice_bunts=sacrifice_bunts
            )
            st.success(f"기록 저장 완료! {player_name} - {inning}회 {result}")
            st.rerun()

        # 이 경기 타석 기록 표시
        st.divider()
        st.subheader("이 경기 타석 기록")
        game_at_bats = load_at_bats(db, game_id=game_id)
        if len(game_at_bats) > 0:
            display_cols = ['선수명', '이닝', '타순', '결과', '안타종류', '타점', '득점']
            st.dataframe(game_at_bats[display_cols], hide_index=True, use_container_width=True)
        else:
            st.info("아직 기록이 없습니다.")

    with tab2:
        st.subheader("투구 기록 입력")

        col1, col2 = st.columns(2)

        with col1:
            pitcher_options = {row['이름']: (row['선수ID'], row['이름'])
                               for _, row in players.iterrows()}
            selected_pitcher = st.selectbox("투수", list(pitcher_options.keys()), key="pitching_player")
            pitcher_id, pitcher_name = pitcher_options[selected_pitcher]

            innings = st.number_input("이닝", min_value=0.0, max_value=9.0, value=0.0, step=0.1,
                                       help="5.1 = 5이닝 1아웃")

        with col2:
            hits = st.number_input("피안타", min_value=0, value=0)
            earned_runs = st.number_input("자책점", min_value=0, value=0)
            runs = st.number_input("실점", min_value=0, value=0)

        col3, col4 = st.columns(2)
        with col3:
            p_walks = st.number_input("볼넷 (투수)", min_value=0, value=0, key="p_walks")
            p_strikeouts = st.number_input("탈삼진", min_value=0, value=0)
        with col4:
            p_homers = st.number_input("피홈런", min_value=0, value=0)
            decision = st.selectbox("결과", ["-", "승", "패", "세이브"])

        if st.button("투구 기록 저장", type="primary"):
            db.add_pitching(
                game_id=game_id,
                player_id=pitcher_id,
                player_name=pitcher_name,
                innings=innings,
                hits=hits,
                runs=runs,
                earned_runs=earned_runs,
                walks=p_walks,
                strikeouts=p_strikeouts,
                home_runs=p_homers,
                win=(decision == "승"),
                loss=(decision == "패"),
                save=(decision == "세이브")
            )
            st.success(f"투구 기록 저장 완료! {pitcher_name} - {innings}이닝")
            st.rerun()

        # 이 경기 투구 기록 표시
        st.divider()
        st.subheader("이 경기 투구 기록")
        game_pitching = load_pitching(db, game_id=game_id)
        if len(game_pitching) > 0:
            display_cols = ['선수명', '이닝', '피안타', '자책', '볼넷', '삼진']
            st.dataframe(game_pitching[display_cols], hide_index=True, use_container_width=True)
        else:
            st.info("아직 기록이 없습니다.")


def show_player_stats(db):
    """선수 통계 화면"""
    st.title("선수 통계")

    players = load_players(db)

    if len(players) == 0:
        st.warning("등록된 선수가 없습니다.")
        return

    # 선수 선택
    player_options = {row['이름']: row['선수ID'] for _, row in players.iterrows()}
    selected_player = st.selectbox("선수 선택", list(player_options.keys()))
    player_id = player_options[selected_player]

    player_info = players[players['선수ID'] == player_id].iloc[0]

    # 선수 정보
    st.markdown(f"### {player_info['이름']} #{player_info['등번호']}")
    st.caption(f"{player_info['포지션']} | {player_info['투타']}")

    st.divider()

    # 타격/투구 탭
    tab1, tab2 = st.tabs(["타격 기록", "투구 기록"])

    with tab1:
        at_bats = load_at_bats(db, player_id=player_id)

        if len(at_bats) == 0:
            st.info("타격 기록이 없습니다.")
        else:
            stats = calculate_player_batting_stats(at_bats)
            calc = SabermetricsCalculator

            # 주요 지표
            st.subheader("시즌 기록")
            show_grade_legend()

            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                display_stat_with_grade("타율", calc.avg(stats), "AVG")
            with col2:
                display_stat_with_grade("출루율", calc.obp(stats), "OBP")
            with col3:
                display_stat_with_grade("장타율", calc.slg(stats), "SLG")
            with col4:
                display_stat_with_grade("OPS", calc.ops(stats), "OPS")
            with col5:
                display_stat_with_grade("wOBA", calc.woba(stats), "wOBA")

            st.divider()

            # 기본 기록
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("경기", len(at_bats['경기ID'].unique()))
                st.metric("타석", stats.plate_appearances)
                st.metric("타수", stats.at_bats)
            with col2:
                st.metric("안타", stats.hits)
                st.metric("2루타", stats.doubles)
                st.metric("3루타", stats.triples)
            with col3:
                st.metric("홈런", stats.home_runs)
                st.metric("타점", stats.rbis)
                st.metric("득점", stats.runs)
            with col4:
                st.metric("볼넷", stats.walks)
                st.metric("삼진", stats.strikeouts)
                st.metric("도루", stats.stolen_bases)

            st.divider()

            # 세부 지표
            st.subheader("세이버메트릭스 지표")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("ISO (순장타율)", format_avg(calc.iso(stats)))
                st.metric("BABIP", format_avg(calc.babip(stats)))
            with col2:
                st.metric("BB%", format_percentage(calc.bb_rate(stats)))
                st.metric("K%", format_percentage(calc.k_rate(stats)))
            with col3:
                st.metric("루타", stats.total_bases)

            # 경기별 기록
            st.divider()
            st.subheader("경기별 기록")
            st.dataframe(
                at_bats[['경기ID', '이닝', '결과', '안타종류', '타점', '득점']],
                hide_index=True,
                use_container_width=True
            )

    with tab2:
        pitching = load_pitching(db, player_id=player_id)

        if len(pitching) == 0:
            st.info("투구 기록이 없습니다.")
        else:
            stats = calculate_player_pitching_stats(pitching)
            calc = SabermetricsCalculator

            # 주요 지표
            st.subheader("시즌 기록")
            show_grade_legend()

            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                display_stat_with_grade("ERA", calc.era(stats), "ERA", ".2f")
            with col2:
                display_stat_with_grade("WHIP", calc.whip(stats), "WHIP", ".2f")
            with col3:
                display_stat_with_grade("K/9", calc.k_per_9(stats), None, ".1f")
            with col4:
                display_stat_with_grade("BB/9", calc.bb_per_9(stats), None, ".1f")
            with col5:
                display_stat_with_grade("FIP", calc.fip(stats), "ERA", ".2f")

            st.divider()

            # 기본 기록
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("경기", len(pitching))
                st.metric("이닝", f"{stats.innings_pitched:.1f}")
            with col2:
                st.metric("승", stats.wins)
                st.metric("패", stats.losses)
            with col3:
                st.metric("세이브", stats.saves)
                st.metric("자책", stats.earned_runs)
            with col4:
                st.metric("삼진", stats.strikeouts)
                st.metric("볼넷", stats.walks)

            # 경기별 기록
            st.divider()
            st.subheader("경기별 기록")
            st.dataframe(
                pitching[['경기ID', '이닝', '피안타', '자책', '삼진', '볼넷']],
                hide_index=True,
                use_container_width=True
            )


def show_player_management(db):
    """선수 관리 화면"""
    st.title("선수 관리")

    tab1, tab2 = st.tabs(["선수 등록", "선수 목록"])

    with tab1:
        st.subheader("새 선수 등록")

        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("이름")
            number = st.number_input("등번호", min_value=0, max_value=99, value=1)

        with col2:
            position = st.selectbox("포지션",
                ["투수", "포수", "1루수", "2루수", "3루수", "유격수", "좌익수", "중견수", "우익수", "지명타자"])
            bat_throw = st.selectbox("투타",
                ["우투우타", "우투좌타", "좌투좌타", "좌투우타", "우투양타", "좌투양타"])

        if st.button("선수 등록", type="primary"):
            if name:
                player_id = db.add_player(name, number, position, bat_throw)
                st.success(f"선수 등록 완료! {name} (ID: {player_id})")
                st.rerun()
            else:
                st.error("이름을 입력해주세요.")

    with tab2:
        st.subheader("등록된 선수")
        players = load_players(db)

        if len(players) > 0:
            st.dataframe(
                players[['이름', '등번호', '포지션', '투타']],
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("등록된 선수가 없습니다.")


def show_growth_report(db):
    """개인 성장 리포트 + AI 코칭"""
    st.title("📈 성장 리포트")
    st.caption("최근 경기 트렌드 분석 & AI 코칭 조언")

    players = load_players(db)
    if len(players) == 0:
        st.warning("등록된 선수가 없습니다.")
        return

    # 선수 선택
    player_options = {row['이름']: row['선수ID'] for _, row in players.iterrows()}
    selected_player = st.selectbox("선수 선택", list(player_options.keys()))
    player_id = player_options[selected_player]
    player_info = players[players['선수ID'] == player_id].iloc[0]

    st.markdown(f"### {player_info['이름']} #{player_info['등번호']}")
    st.divider()

    # 타석 데이터 가져오기
    at_bats = load_at_bats(db, player_id=player_id)

    if len(at_bats) == 0:
        st.info("아직 기록이 없습니다. 경기 기록을 추가해주세요!")
        return

    # 경기별로 그룹화
    games = at_bats['경기ID'].unique()

    if len(games) < 2:
        st.info("트렌드 분석을 위해 최소 2경기 이상의 기록이 필요합니다.")
        # 현재 성적만 표시
        stats = calculate_player_batting_stats(at_bats)
        calc = SabermetricsCalculator
        col1, col2, col3 = st.columns(3)
        with col1:
            display_stat_with_grade("타율", calc.avg(stats), "AVG")
        with col2:
            display_stat_with_grade("OPS", calc.ops(stats), "OPS")
        with col3:
            display_stat_with_grade("출루율", calc.obp(stats), "OBP")
        return

    # 경기별 성적 계산
    game_stats = []
    for game_id in games:
        game_abs = at_bats[at_bats['경기ID'] == game_id]
        stats = calculate_player_batting_stats(game_abs)
        calc = SabermetricsCalculator

        game_stats.append({
            '경기': game_id[-4:],  # 마지막 4자리만
            '타수': stats.at_bats,
            '안타': stats.hits,
            '타율': calc.avg(stats) or 0,
            'OPS': calc.ops(stats) or 0,
            '삼진': stats.strikeouts,
            '볼넷': stats.walks,
            '삼진률': (stats.strikeouts / stats.plate_appearances * 100) if stats.plate_appearances > 0 else 0,
            '볼넷률': (stats.walks / stats.plate_appearances * 100) if stats.plate_appearances > 0 else 0,
        })

    game_df = pd.DataFrame(game_stats)

    # === 트렌드 분석 ===
    st.subheader("📊 최근 경기 트렌드")

    # 최근 5경기 vs 이전 경기 비교
    recent_n = min(5, len(games))
    recent_games = list(games)[-recent_n:]
    older_games = list(games)[:-recent_n] if len(games) > recent_n else []

    recent_abs = at_bats[at_bats['경기ID'].isin(recent_games)]
    recent_stats = calculate_player_batting_stats(recent_abs)
    recent_avg = SabermetricsCalculator.avg(recent_stats) or 0
    recent_ops = SabermetricsCalculator.ops(recent_stats) or 0
    recent_k_rate = (recent_stats.strikeouts / recent_stats.plate_appearances * 100) if recent_stats.plate_appearances > 0 else 0

    if older_games:
        older_abs = at_bats[at_bats['경기ID'].isin(older_games)]
        older_stats = calculate_player_batting_stats(older_abs)
        older_avg = SabermetricsCalculator.avg(older_stats) or 0
        older_ops = SabermetricsCalculator.ops(older_stats) or 0
        older_k_rate = (older_stats.strikeouts / older_stats.plate_appearances * 100) if older_stats.plate_appearances > 0 else 0

        avg_diff = recent_avg - older_avg
        ops_diff = recent_ops - older_ops
        k_diff = recent_k_rate - older_k_rate

        col1, col2, col3 = st.columns(3)
        with col1:
            delta_color = "normal" if avg_diff >= 0 else "inverse"
            st.metric(f"타율 (최근 {recent_n}경기)", f"{recent_avg:.3f}",
                     f"{avg_diff:+.3f}", delta_color=delta_color)
        with col2:
            delta_color = "normal" if ops_diff >= 0 else "inverse"
            st.metric(f"OPS (최근 {recent_n}경기)", f"{recent_ops:.3f}",
                     f"{ops_diff:+.3f}", delta_color=delta_color)
        with col3:
            delta_color = "inverse" if k_diff >= 0 else "normal"  # 삼진률은 낮을수록 좋음
            st.metric(f"삼진률 (최근 {recent_n}경기)", f"{recent_k_rate:.1f}%",
                     f"{k_diff:+.1f}%", delta_color=delta_color)
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(f"타율 (최근 {recent_n}경기)", f"{recent_avg:.3f}")
        with col2:
            st.metric(f"OPS (최근 {recent_n}경기)", f"{recent_ops:.3f}")
        with col3:
            st.metric(f"삼진률 (최근 {recent_n}경기)", f"{recent_k_rate:.1f}%")

    # 그래프
    if len(game_df) >= 2:
        import plotly.graph_objects as go

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=list(range(1, len(game_df)+1)), y=game_df['타율'],
                                  mode='lines+markers', name='타율', line=dict(color='#1e88e5', width=3)))
        fig.update_layout(
            title="경기별 타율 변화",
            xaxis_title="경기",
            yaxis_title="타율",
            yaxis=dict(range=[0, max(0.5, game_df['타율'].max() + 0.1)]),
            height=300
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # === AI 코칭 조언 ===
    st.subheader("🤖 AI 코칭 조언")

    advice_list = []

    # 전체 통계
    total_stats = calculate_player_batting_stats(at_bats)
    calc = SabermetricsCalculator

    total_avg = calc.avg(total_stats) or 0
    total_ops = calc.ops(total_stats) or 0
    total_k_rate = (total_stats.strikeouts / total_stats.plate_appearances * 100) if total_stats.plate_appearances > 0 else 0
    total_bb_rate = (total_stats.walks / total_stats.plate_appearances * 100) if total_stats.plate_appearances > 0 else 0
    total_iso = calc.iso(total_stats) or 0

    # 조언 생성
    # 1. 타율 기반 조언
    if total_avg >= 0.350:
        advice_list.append(("🔥", "훌륭한 타율!", f"타율 {total_avg:.3f}로 리그 최상위권입니다. 현재 컨디션을 유지하세요!"))
    elif total_avg >= 0.300:
        advice_list.append(("👍", "좋은 타율", f"타율 {total_avg:.3f}로 준수합니다. 꾸준함을 유지하세요."))
    elif total_avg >= 0.250:
        advice_list.append(("📊", "평균 타율", f"타율 {total_avg:.3f}입니다. 스윙 타이밍 점검을 권장합니다."))
    else:
        advice_list.append(("⚠️", "타율 개선 필요", f"타율 {total_avg:.3f}입니다. 배팅 폼 점검과 티배팅 연습을 추천합니다."))

    # 2. 삼진률 기반 조언
    if total_k_rate > 25:
        advice_list.append(("👁️", "선구안 개선 필요", f"삼진률 {total_k_rate:.1f}%가 높습니다. 초구 스트라이크 적극 공략과 2스트라이크 후 컨택 위주 스윙을 연습하세요."))
    elif total_k_rate < 10:
        advice_list.append(("✨", "뛰어난 컨택 능력", f"삼진률 {total_k_rate:.1f}%로 매우 낮습니다. 컨택 능력이 우수합니다!"))

    # 3. 볼넷률 기반 조언
    if total_bb_rate < 5:
        advice_list.append(("🎯", "출루 기회 활용", f"볼넷률 {total_bb_rate:.1f}%가 낮습니다. 볼 선구를 늘려 출루 기회를 높이세요."))
    elif total_bb_rate > 12:
        advice_list.append(("👀", "훌륭한 선구안", f"볼넷률 {total_bb_rate:.1f}%로 높습니다. 뛰어난 선구안을 보유하고 있습니다!"))

    # 4. 장타력 기반 조언
    if total_iso < 0.100 and total_stats.at_bats >= 10:
        advice_list.append(("💪", "장타력 강화 필요", f"ISO(순장타율) {total_iso:.3f}입니다. 장타를 늘리려면 하체 힘과 팔로우스루를 점검하세요."))
    elif total_iso > 0.200:
        advice_list.append(("🚀", "강력한 장타력", f"ISO {total_iso:.3f}로 뛰어난 장타력을 보유하고 있습니다!"))

    # 5. 최근 트렌드 기반 조언
    if older_games and avg_diff < -0.050:
        advice_list.append(("📉", "최근 슬럼프 징후", f"최근 {recent_n}경기 타율이 {abs(avg_diff):.3f} 하락했습니다. 컨디션 관리와 기본기 점검이 필요합니다."))
    elif older_games and avg_diff > 0.050:
        advice_list.append(("📈", "상승세!", f"최근 {recent_n}경기 타율이 {avg_diff:.3f} 상승했습니다. 좋은 컨디션을 유지하세요!"))

    # 조언 표시
    for icon, title, content in advice_list:
        st.markdown(f"""
        <div style="background: #f8f9fa; border-left: 4px solid #1e88e5; padding: 15px; margin: 10px 0; border-radius: 5px;">
            <strong>{icon} {title}</strong><br/>
            <span style="color: #555;">{content}</span>
        </div>
        """, unsafe_allow_html=True)

    if not advice_list:
        st.info("충분한 데이터가 쌓이면 맞춤형 조언을 제공합니다!")


def show_team_insight(db):
    """팀 인사이트"""
    st.title("👥 팀 인사이트")
    st.caption("팀 분석, 최적 타순 추천, 팀원 비교")

    players = load_players(db)
    at_bats = load_at_bats(db)
    games = load_games(db)

    if len(players) == 0:
        st.warning("등록된 선수가 없습니다.")
        return

    if len(at_bats) == 0:
        st.warning("기록된 경기가 없습니다.")
        return

    tab1, tab2, tab3 = st.tabs(["팀원 비교", "최적 타순", "팀 리더보드"])

    with tab1:
        st.subheader("팀원 성적 비교")
        show_grade_legend()

        # 모든 선수 성적 계산
        player_stats_list = []
        for _, player in players.iterrows():
            player_abs = at_bats[at_bats['선수ID'] == player['선수ID']]
            if len(player_abs) > 0:
                stats = calculate_player_batting_stats(player_abs)
                calc = SabermetricsCalculator
                if stats.at_bats >= 3:  # 최소 3타수
                    avg = calc.avg(stats) or 0
                    ops = calc.ops(stats) or 0
                    obp = calc.obp(stats) or 0
                    slg = calc.slg(stats) or 0

                    player_stats_list.append({
                        '선수': player['이름'],
                        '타수': stats.at_bats,
                        '안타': stats.hits,
                        '타율': avg,
                        '출루율': obp,
                        '장타율': slg,
                        'OPS': ops,
                        '홈런': stats.home_runs,
                        '타점': stats.rbis,
                        '삼진': stats.strikeouts,
                        '볼넷': stats.walks,
                    })

        if player_stats_list:
            stats_df = pd.DataFrame(player_stats_list)
            stats_df = stats_df.sort_values('OPS', ascending=False)

            # 등급 색상 적용
            def color_grade(val, stat_name):
                if pd.isna(val):
                    return ''
                grade, color = get_grade(stat_name, val)
                return f'color: {color}; font-weight: bold'

            styled_df = stats_df.copy()
            styled_df['타율'] = styled_df['타율'].apply(lambda x: f"{x:.3f}")
            styled_df['출루율'] = styled_df['출루율'].apply(lambda x: f"{x:.3f}")
            styled_df['장타율'] = styled_df['장타율'].apply(lambda x: f"{x:.3f}")
            styled_df['OPS'] = styled_df['OPS'].apply(lambda x: f"{x:.3f}")

            st.dataframe(styled_df, hide_index=True, use_container_width=True)

            # 레이더 차트로 비교
            if len(player_stats_list) >= 2:
                st.subheader("선수 비교 차트")
                compare_players = st.multiselect(
                    "비교할 선수 선택 (2-4명)",
                    [p['선수'] for p in player_stats_list],
                    default=[player_stats_list[0]['선수'], player_stats_list[1]['선수']] if len(player_stats_list) >= 2 else []
                )

                if len(compare_players) >= 2:
                    fig = go.Figure()

                    categories = ['타율', '출루율', '장타율']

                    for player_name in compare_players:
                        player_data = next((p for p in player_stats_list if p['선수'] == player_name), None)
                        if player_data:
                            # 정규화 (0-1 스케일)
                            values = [
                                min(player_data['타율'] / 0.4, 1),
                                min(player_data['출루율'] / 0.5, 1),
                                min(player_data['장타율'] / 0.6, 1),
                            ]
                            values.append(values[0])  # 닫기

                            fig.add_trace(go.Scatterpolar(
                                r=values,
                                theta=categories + [categories[0]],
                                name=player_name,
                                fill='toself',
                                opacity=0.6
                            ))

                    fig.update_layout(
                        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                        showlegend=True,
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("충분한 타석 기록이 있는 선수가 없습니다.")

    with tab2:
        st.subheader("🎯 최적 타순 추천")
        st.caption("OPS 기반 타순 최적화")

        if player_stats_list:
            # 타순 추천 로직
            sorted_players = sorted(player_stats_list, key=lambda x: x['OPS'], reverse=True)

            st.markdown("""
            **타순 구성 원칙:**
            - 1번: 출루율 높은 선수
            - 2번: 컨택 좋고 출루율 높은 선수
            - 3번: 가장 좋은 타자 (OPS 최고)
            - 4번: 장타력 + 타점 능력
            - 5번 이하: OPS 순
            """)

            st.divider()

            # 출루율 기준 정렬 (1,2번용)
            by_obp = sorted(player_stats_list, key=lambda x: x['출루율'], reverse=True)
            # 장타율 기준 정렬 (4번용)
            by_slg = sorted(player_stats_list, key=lambda x: x['장타율'], reverse=True)

            recommended_order = []
            used = set()

            # 1번: 출루율 최고
            if by_obp:
                p = by_obp[0]
                recommended_order.append((1, p['선수'], f"출루율 {p['출루율']:.3f}"))
                used.add(p['선수'])

            # 2번: 출루율 2위
            for p in by_obp:
                if p['선수'] not in used:
                    recommended_order.append((2, p['선수'], f"출루율 {p['출루율']:.3f}"))
                    used.add(p['선수'])
                    break

            # 3번: OPS 최고 (남은 선수 중)
            for p in sorted_players:
                if p['선수'] not in used:
                    recommended_order.append((3, p['선수'], f"OPS {p['OPS']:.3f} (팀 내 최고)"))
                    used.add(p['선수'])
                    break

            # 4번: 장타율 최고 (남은 선수 중)
            for p in by_slg:
                if p['선수'] not in used:
                    recommended_order.append((4, p['선수'], f"장타율 {p['장타율']:.3f}"))
                    used.add(p['선수'])
                    break

            # 5번 이하: OPS 순
            order_num = 5
            for p in sorted_players:
                if p['선수'] not in used and order_num <= 9:
                    recommended_order.append((order_num, p['선수'], f"OPS {p['OPS']:.3f}"))
                    used.add(p['선수'])
                    order_num += 1

            # 표시
            for order, name, reason in recommended_order:
                st.markdown(f"""
                <div style="display: flex; align-items: center; padding: 10px; background: {'#e3f2fd' if order <= 4 else '#f5f5f5'}; margin: 5px 0; border-radius: 8px;">
                    <div style="font-size: 1.5rem; font-weight: bold; width: 40px; color: #1e88e5;">{order}</div>
                    <div style="flex: 1;">
                        <strong>{name}</strong><br/>
                        <span style="color: #666; font-size: 0.85rem;">{reason}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("충분한 기록이 있는 선수가 필요합니다.")

    with tab3:
        st.subheader("🏆 팀 리더보드")

        if player_stats_list:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**타율 TOP 3**")
                top_avg = sorted(player_stats_list, key=lambda x: x['타율'], reverse=True)[:3]
                for i, p in enumerate(top_avg, 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                    st.markdown(f"{medal} **{p['선수']}** - {p['타율']:.3f}")

                st.markdown("**홈런 TOP 3**")
                top_hr = sorted(player_stats_list, key=lambda x: x['홈런'], reverse=True)[:3]
                for i, p in enumerate(top_hr, 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                    st.markdown(f"{medal} **{p['선수']}** - {p['홈런']}개")

            with col2:
                st.markdown("**OPS TOP 3**")
                top_ops = sorted(player_stats_list, key=lambda x: x['OPS'], reverse=True)[:3]
                for i, p in enumerate(top_ops, 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                    st.markdown(f"{medal} **{p['선수']}** - {p['OPS']:.3f}")

                st.markdown("**타점 TOP 3**")
                top_rbi = sorted(player_stats_list, key=lambda x: x['타점'], reverse=True)[:3]
                for i, p in enumerate(top_rbi, 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                    st.markdown(f"{medal} **{p['선수']}** - {p['타점']}타점")

            # 팀 평균
            st.divider()
            st.subheader("📊 팀 평균")

            team_avg = sum(p['타율'] for p in player_stats_list) / len(player_stats_list)
            team_ops = sum(p['OPS'] for p in player_stats_list) / len(player_stats_list)
            team_hr = sum(p['홈런'] for p in player_stats_list)
            team_rbi = sum(p['타점'] for p in player_stats_list)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                display_stat_with_grade("팀 평균 타율", team_avg, "AVG")
            with col2:
                display_stat_with_grade("팀 평균 OPS", team_ops, "OPS")
            with col3:
                st.metric("팀 총 홈런", f"{team_hr}개")
            with col4:
                st.metric("팀 총 타점", f"{team_rbi}점")
        else:
            st.info("충분한 기록이 있는 선수가 필요합니다.")


def show_game_management(db):
    """경기 관리 화면"""
    st.title("경기 관리")

    tab1, tab2 = st.tabs(["경기 등록", "경기 목록"])

    with tab1:
        st.subheader("새 경기 등록")

        col1, col2 = st.columns(2)

        with col1:
            date = st.date_input("날짜")
            opponent = st.text_input("상대팀")
            home_away = st.selectbox("홈/원정", ["홈", "원정"])

        with col2:
            our_score = st.number_input("우리 점수", min_value=0, value=0)
            their_score = st.number_input("상대 점수", min_value=0, value=0)
            stadium = st.text_input("구장")

        memo = st.text_area("메모", height=100)

        if st.button("경기 등록", type="primary"):
            if opponent:
                game_id = db.add_game(
                    date=str(date),
                    opponent=opponent,
                    home_away=home_away,
                    our_score=our_score,
                    their_score=their_score,
                    stadium=stadium,
                    memo=memo
                )
                st.success(f"경기 등록 완료! (ID: {game_id})")
                st.rerun()
            else:
                st.error("상대팀을 입력해주세요.")

    with tab2:
        st.subheader("경기 목록")
        games = load_games(db)

        if len(games) > 0:
            # 결과별 색상
            def highlight_result(val):
                if val == '승':
                    return 'background-color: #d4edda'
                elif val == '패':
                    return 'background-color: #f8d7da'
                return ''

            styled_df = games[['날짜', '상대팀', '홈/원정', '우리점수', '상대점수', '결과', '구장']].style.applymap(
                highlight_result, subset=['결과']
            )
            st.dataframe(styled_df, hide_index=True, use_container_width=True)

            # 통계
            st.divider()
            col1, col2, col3 = st.columns(3)
            with col1:
                wins = len(games[games['결과'] == '승'])
                st.metric("승", wins)
            with col2:
                losses = len(games[games['결과'] == '패'])
                st.metric("패", losses)
            with col3:
                draws = len(games[games['결과'] == '무'])
                st.metric("무", draws)
        else:
            st.info("등록된 경기가 없습니다.")


if __name__ == "__main__":
    main()
