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
</style>
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
        ["대시보드", "경기 기록", "선수 통계", "선수 관리", "경기 관리"],
        label_visibility="collapsed"
    )

    if menu == "대시보드":
        show_dashboard(db)
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

    games = db.get_games()
    players = db.get_players()

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
        at_bats = db.get_at_bats()
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

    games = db.get_games()
    players = db.get_players()

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
        game_at_bats = db.get_at_bats(game_id=game_id)
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
        game_pitching = db.get_pitching(game_id=game_id)
        if len(game_pitching) > 0:
            display_cols = ['선수명', '이닝', '피안타', '자책', '볼넷', '삼진']
            st.dataframe(game_pitching[display_cols], hide_index=True, use_container_width=True)
        else:
            st.info("아직 기록이 없습니다.")


def show_player_stats(db):
    """선수 통계 화면"""
    st.title("선수 통계")

    players = db.get_players()

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
        at_bats = db.get_at_bats(player_id=player_id)

        if len(at_bats) == 0:
            st.info("타격 기록이 없습니다.")
        else:
            stats = calculate_player_batting_stats(at_bats)
            calc = SabermetricsCalculator

            # 주요 지표
            st.subheader("시즌 기록")

            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("타율", format_avg(calc.avg(stats)))
            with col2:
                st.metric("출루율", format_avg(calc.obp(stats)))
            with col3:
                st.metric("장타율", format_avg(calc.slg(stats)))
            with col4:
                st.metric("OPS", format_avg(calc.ops(stats)))
            with col5:
                st.metric("wOBA", format_avg(calc.woba(stats)))

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
        pitching = db.get_pitching(player_id=player_id)

        if len(pitching) == 0:
            st.info("투구 기록이 없습니다.")
        else:
            stats = calculate_player_pitching_stats(pitching)
            calc = SabermetricsCalculator

            # 주요 지표
            st.subheader("시즌 기록")

            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("ERA", format_era(calc.era(stats)))
            with col2:
                st.metric("WHIP", f"{calc.whip(stats):.2f}" if calc.whip(stats) else "-")
            with col3:
                st.metric("K/9", f"{calc.k_per_9(stats):.1f}" if calc.k_per_9(stats) else "-")
            with col4:
                st.metric("BB/9", f"{calc.bb_per_9(stats):.1f}" if calc.bb_per_9(stats) else "-")
            with col5:
                st.metric("FIP", format_era(calc.fip(stats)))

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
        players = db.get_players()

        if len(players) > 0:
            st.dataframe(
                players[['이름', '등번호', '포지션', '투타']],
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("등록된 선수가 없습니다.")


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
        games = db.get_games()

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
