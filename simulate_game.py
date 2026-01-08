"""
가상 야구 경기 시뮬레이션
9이닝 경기를 시뮬레이션하고 Google Sheets에 기록
"""

import random
from sheets_db import SheetsDB

# 데이터베이스 연결
db = SheetsDB(
    credentials_path="/Users/jaewansim/Desktop/statz-kr/credentials.json",
    spreadsheet_url="https://docs.google.com/spreadsheets/d/1rcWR_qwVAo_PU0ecO4_gVpWjolOq07Uifs0NlqTn5FY/edit"
)
db.connect()
print("Google Sheets 연결 완료!")

# 우리 팀 선수 등록
our_team = [
    ("김민수", 1, "투수", "우투우타"),
    ("이정훈", 7, "중견수", "우투좌타"),
    ("박성호", 25, "1루수", "우투우타"),
    ("최동욱", 22, "포수", "우투우타"),
    ("정재원", 3, "유격수", "우투좌타"),
    ("한승우", 14, "3루수", "우투우타"),
    ("오준혁", 8, "우익수", "좌투좌타"),
    ("신동현", 5, "2루수", "우투우타"),
    ("윤태호", 11, "좌익수", "우투좌타"),
]

print("\n=== 선수 등록 ===")
player_ids = {}
for name, number, position, bat_throw in our_team:
    player_id = db.add_player(name, number, position, bat_throw)
    player_ids[name] = player_id
    print(f"  {name} #{number} ({position}) 등록 완료")

# 경기 등록
print("\n=== 경기 등록 ===")
game_id = db.add_game(
    date="2025-01-09",
    opponent="청룡 베이스볼",
    home_away="홈",
    our_score=0,  # 나중에 업데이트
    their_score=0,
    stadium="잠실야구장",
    memo="시뮬레이션 경기"
)
print(f"  vs 청룡 베이스볼 (경기ID: {game_id})")

# 타격 결과 확률
def get_at_bat_result():
    """타석 결과 랜덤 생성"""
    rand = random.random()
    if rand < 0.25:  # 25% 안타
        hit_rand = random.random()
        if hit_rand < 0.65:
            return "안타", "1루타"
        elif hit_rand < 0.85:
            return "안타", "2루타"
        elif hit_rand < 0.95:
            return "안타", "3루타"
        else:
            return "안타", "홈런"
    elif rand < 0.35:  # 10% 볼넷
        return "볼넷", ""
    elif rand < 0.55:  # 20% 삼진
        return "삼진", ""
    elif rand < 0.58:  # 3% 사구
        return "사구", ""
    else:  # 42% 아웃
        return "아웃", ""

# 시뮬레이션 실행
print("\n" + "="*50)
print("       ⚾ 경기 시뮬레이션 시작 ⚾")
print("       우리팀 vs 청룡 베이스볼")
print("="*50)

batting_order = list(our_team)  # 타순 = 등록 순서
current_batter = 0
our_score = 0
their_score = 0
total_hits = 0
total_rbis = 0

for inning in range(1, 10):
    print(f"\n--- {inning}회 초 (우리 공격) ---")

    outs = 0
    runners = [False, False, False]  # 1루, 2루, 3루
    inning_runs = 0

    while outs < 3:
        batter_name = batting_order[current_batter][0]
        batter_id = player_ids[batter_name]

        result, hit_type = get_at_bat_result()

        # 결과 처리
        rbis = 0
        runs = 0
        walks = 1 if result == "볼넷" else 0
        strikeouts = 1 if result == "삼진" else 0
        hit_by_pitch = 1 if result == "사구" else 0
        stolen = random.randint(0, 1) if result == "안타" and hit_type == "1루타" else 0

        if result == "아웃" or result == "삼진":
            outs += 1
            print(f"  {batter_name}: {result} ({outs}아웃)")
        elif result == "안타":
            total_hits += 1
            if hit_type == "홈런":
                # 홈런: 모든 주자 + 타자 득점
                rbis = sum(runners) + 1
                runs = 1
                inning_runs += rbis
                runners = [False, False, False]
                print(f"  {batter_name}: 💥 홈런! {rbis}타점")
            elif hit_type == "3루타":
                rbis = sum(runners)
                inning_runs += rbis
                runners = [False, False, True]
                print(f"  {batter_name}: 3루타! {rbis}타점" if rbis else f"  {batter_name}: 3루타!")
            elif hit_type == "2루타":
                rbis = runners[1] + runners[2]  # 2,3루 주자 득점
                inning_runs += rbis
                if runners[0]:
                    runners = [False, True, True]
                else:
                    runners = [False, True, False]
                print(f"  {batter_name}: 2루타! {rbis}타점" if rbis else f"  {batter_name}: 2루타!")
            else:  # 1루타
                if runners[2]:
                    rbis += 1
                    inning_runs += 1
                runners = [True, runners[0], runners[1]]
                if runners[2]:
                    rbis += 1
                    inning_runs += 1
                    runners[2] = False
                print(f"  {batter_name}: 안타! {rbis}타점" if rbis else f"  {batter_name}: 안타!")
        elif result in ["볼넷", "사구"]:
            # 밀어내기 체크
            if all(runners):
                rbis = 1
                inning_runs += 1
                print(f"  {batter_name}: {result} (밀어내기 1점)")
            else:
                if runners[1] and runners[0]:
                    runners[2] = True
                if runners[0]:
                    runners[1] = True
                runners[0] = True
                print(f"  {batter_name}: {result}")

        total_rbis += rbis

        # Google Sheets에 기록
        db.add_at_bat(
            game_id=game_id,
            player_id=batter_id,
            player_name=batter_name,
            inning=inning,
            batting_order=current_batter + 1,
            result=result,
            hit_type=hit_type,
            rbis=rbis,
            runs=runs,
            stolen_bases=stolen,
            caught_stealing=0,
            walks=walks,
            strikeouts=strikeouts,
            hit_by_pitch=hit_by_pitch,
            sacrifice_flies=0,
            sacrifice_bunts=0
        )

        # 다음 타자
        current_batter = (current_batter + 1) % 9

    our_score += inning_runs
    print(f"  → {inning}회 {inning_runs}득점 (누적: {our_score}점)")

    # 상대팀 점수 (간단히 랜덤)
    their_inning = random.choices([0, 0, 0, 0, 1, 1, 2, 3], weights=[40, 20, 15, 10, 8, 4, 2, 1])[0]
    their_score += their_inning
    print(f"--- {inning}회 말 (상대 공격) ---")
    print(f"  → 청룡 {their_inning}득점 (누적: {their_score}점)")

# 투수 기록
print("\n=== 투수 기록 저장 ===")
pitcher_name = "김민수"
pitcher_id = player_ids[pitcher_name]

# 투수 성적 (9이닝 완투 가정)
db.add_pitching(
    game_id=game_id,
    player_id=pitcher_id,
    player_name=pitcher_name,
    innings=9.0,
    hits=random.randint(5, 9),
    runs=their_score,
    earned_runs=their_score - random.randint(0, min(2, their_score)),
    walks=random.randint(1, 4),
    strikeouts=random.randint(5, 12),
    home_runs=random.randint(0, 2),
    win=(our_score > their_score),
    loss=(our_score < their_score),
    save=False
)
print(f"  {pitcher_name}: 9이닝 완투")

# 최종 결과
print("\n" + "="*50)
print("              ⚾ 경기 종료 ⚾")
print("="*50)
print(f"\n  최종 스코어: 우리팀 {our_score} - {their_score} 청룡")
if our_score > their_score:
    result = "승리! 🎉"
elif our_score < their_score:
    result = "패배..."
else:
    result = "무승부"
print(f"  결과: {result}")
print(f"\n  팀 안타: {total_hits}개")
print(f"  팀 타점: {total_rbis}점")
print("\n  ✅ 모든 기록이 Google Sheets에 저장되었습니다!")
print("  📊 http://localhost:8501 에서 통계를 확인하세요!")
