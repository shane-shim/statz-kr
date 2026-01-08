"""
미라클 동산 10경기 시뮬레이션 (최적화 버전)
배치 쓰기로 API 호출 최소화
"""

import random
import time
from datetime import datetime, timedelta
from sheets_db import SheetsDB

# 데이터베이스 연결
db = SheetsDB(
    credentials_path="/Users/jaewansim/Desktop/statz-kr/credentials.json",
    spreadsheet_url="https://docs.google.com/spreadsheets/d/1rcWR_qwVAo_PU0ecO4_gVpWjolOq07Uifs0NlqTn5FY/edit"
)
db.connect()
print("Google Sheets 연결 완료!")

# 미라클 동산 선수 명단 (18명)
players_data = [
    ("심재완", 1, "투수", "우투우타"),
    ("성승훈", 2, "포수", "우투우타"),
    ("김성호", 3, "1루수", "우투좌타"),
    ("서용만", 4, "2루수", "우투우타"),
    ("최정열", 5, "유격수", "우투우타"),
    ("south..ten", 6, "3루수", "우투좌타"),
    ("r_재현", 7, "좌익수", "좌투좌타"),
    ("강원철", 8, "중견수", "우투우타"),
    ("규식", 9, "우익수", "우투우타"),
    ("김명환", 10, "내야수", "우투우타"),
    ("김민찬", 11, "외야수", "우투좌타"),
    ("김태훈", 12, "내야수", "우투우타"),
    ("백지영", 13, "외야수", "좌투좌타"),
    ("언제나하루를즐겁게", 14, "내야수", "우투우타"),
    ("윤도혁", 15, "투수", "우투우타"),
    ("최병준", 16, "투수", "좌투좌타"),
    ("hwang's", 17, "포수", "우투우타"),
    ("jy", 18, "외야수", "우투좌타"),
]

# 상대팀 목록
opponents = [
    "청룡 베이스볼", "화이트삭스", "레드불스", "블루윙스", "골든이글스",
    "실버스타즈", "그린몬스터즈", "블랙팬서스", "오렌지타이거즈", "퍼플드래곤즈"
]

# 구장 목록
stadiums = ["잠실야구장", "목동야구장", "고척돔", "문학야구장", "대전한밭야구장"]

print("\n=== 선수 확인/등록 ===")

# 기존 선수 목록 한 번에 가져오기
existing_players = db.get_players()
existing_dict = {}
if len(existing_players) > 0:
    for _, row in existing_players.iterrows():
        existing_dict[row['이름']] = row['선수ID']

player_ids = {}
new_players = []

for name, number, position, bat_throw in players_data:
    if name in existing_dict:
        player_ids[name] = existing_dict[name]
        print(f"  {name} - 기존 선수")
    else:
        new_players.append((name, number, position, bat_throw))

# 새 선수 등록 (딜레이 적용)
for name, number, position, bat_throw in new_players:
    player_id = db.add_player(name, number, position, bat_throw)
    player_ids[name] = player_id
    print(f"  {name} #{number} ({position}) 신규 등록")
    time.sleep(1)

print(f"\n총 {len(player_ids)}명 선수 준비 완료")

# 선수별 스킬 (타격 보정)
def get_player_skill(name):
    skill_bonus = {
        "심재완": 0.03, "성승훈": 0.02, "김성호": 0.04, "서용만": 0.01,
        "강원철": 0.03, "r_재현": 0.02, "규식": 0.01, "김민찬": 0.02
    }
    return skill_bonus.get(name, 0)

def get_at_bat_result(player_name):
    """타석 결과 랜덤 생성"""
    skill = get_player_skill(player_name)
    rand = random.random()
    hit_chance = 0.25 + skill

    if rand < hit_chance:
        hit_rand = random.random()
        if hit_rand < 0.65:
            return "안타", "1루타"
        elif hit_rand < 0.85:
            return "안타", "2루타"
        elif hit_rand < 0.95:
            return "안타", "3루타"
        else:
            return "안타", "홈런"
    elif rand < hit_chance + 0.10:
        return "볼넷", ""
    elif rand < hit_chance + 0.28:
        return "삼진", ""
    elif rand < hit_chance + 0.31:
        return "사구", ""
    else:
        return "아웃", ""

def simulate_game(game_num, player_ids, players_data):
    """한 경기 시뮬레이션 (메모리에 기록 저장)"""
    game_date = (datetime.now() - timedelta(days=10-game_num)).strftime("%Y-%m-%d")
    opponent = opponents[game_num - 1]
    stadium = random.choice(stadiums)
    home_away = random.choice(["홈", "원정"])
    game_id = f"SIM{game_num:03d}_{datetime.now().strftime('%H%M%S')}"

    batting_order = random.sample(players_data, 9)
    pitchers = [p for p in players_data if p[2] == "투수"]
    starting_pitcher = random.choice(pitchers)

    print(f"\n{'='*50}")
    print(f"  제{game_num}경기: vs {opponent}")
    print(f"  날짜: {game_date} | {home_away} | {stadium}")
    print(f"  선발: {starting_pitcher[0]}")
    print(f"{'='*50}")

    current_batter = 0
    our_score = 0
    their_score = 0
    at_bat_records = []

    for inning in range(1, 10):
        outs = 0
        runners = [False, False, False]
        inning_runs = 0

        while outs < 3:
            batter_name = batting_order[current_batter][0]
            batter_id = player_ids[batter_name]
            result, hit_type = get_at_bat_result(batter_name)

            rbis = 0
            runs = 0
            walks = 1 if result == "볼넷" else 0
            strikeouts = 1 if result == "삼진" else 0
            hit_by_pitch = 1 if result == "사구" else 0
            stolen = random.randint(0, 1) if result == "안타" and hit_type == "1루타" and random.random() < 0.15 else 0

            if result == "아웃" or result == "삼진":
                outs += 1
            elif result == "안타":
                if hit_type == "홈런":
                    rbis = sum(runners) + 1
                    runs = 1
                    inning_runs += rbis
                    runners = [False, False, False]
                elif hit_type == "3루타":
                    rbis = sum(runners)
                    inning_runs += rbis
                    runners = [False, False, True]
                elif hit_type == "2루타":
                    rbis = runners[1] + runners[2]
                    inning_runs += rbis
                    runners = [False, True, runners[0]]
                else:
                    if runners[2]:
                        rbis += 1
                        inning_runs += 1
                    runners = [True, runners[0], runners[1]]
                    if runners[2]:
                        rbis += 1
                        inning_runs += 1
                        runners[2] = False
            elif result in ["볼넷", "사구"]:
                if all(runners):
                    rbis = 1
                    inning_runs += 1
                else:
                    if runners[1] and runners[0]:
                        runners[2] = True
                    if runners[0]:
                        runners[1] = True
                    runners[0] = True

            # 기록 저장 (메모리)
            at_bat_records.append({
                'game_id': game_id,
                'player_id': batter_id,
                'player_name': batter_name,
                'inning': inning,
                'batting_order': current_batter + 1,
                'result': result,
                'hit_type': hit_type,
                'rbis': rbis,
                'runs': runs,
                'stolen_bases': stolen,
                'caught_stealing': 1 if stolen and random.random() < 0.3 else 0,
                'walks': walks,
                'strikeouts': strikeouts,
                'hit_by_pitch': hit_by_pitch,
                'sacrifice_flies': 0,
                'sacrifice_bunts': 0
            })

            current_batter = (current_batter + 1) % 9

        our_score += inning_runs
        their_inning = random.choices([0, 0, 0, 0, 1, 1, 2, 3], weights=[40, 20, 15, 10, 8, 4, 2, 1])[0]
        their_score += their_inning

    # 투수 기록
    pitcher_record = {
        'game_id': game_id,
        'player_id': player_ids[starting_pitcher[0]],
        'player_name': starting_pitcher[0],
        'innings': random.choice([5.0, 6.0, 7.0, 8.0, 9.0]),
        'hits': random.randint(4, 10),
        'runs': their_score,
        'earned_runs': max(0, their_score - random.randint(0, min(2, their_score))),
        'walks': random.randint(1, 5),
        'strikeouts': random.randint(3, 10),
        'home_runs': random.randint(0, 2),
        'win': our_score > their_score,
        'loss': our_score < their_score,
        'save': False
    }

    # 경기 기록
    game_record = {
        'date': game_date,
        'opponent': opponent,
        'home_away': home_away,
        'our_score': our_score,
        'their_score': their_score,
        'stadium': stadium,
        'memo': f'시뮬레이션 {game_num}차전'
    }

    result_str = "승리!" if our_score > their_score else "패배" if our_score < their_score else "무승부"
    print(f"  결과: 미라클동산 {our_score} - {their_score} {opponent} ({result_str})")

    return our_score, their_score, at_bat_records, pitcher_record, game_record

# 10경기 시뮬레이션
print("\n" + "="*50)
print("     미라클 동산 10경기 시뮬레이션")
print("="*50)

total_wins = 0
total_losses = 0
total_draws = 0
total_runs_for = 0
total_runs_against = 0

all_at_bats = []
all_pitching = []
all_games = []

for game_num in range(1, 11):
    our, their, at_bats, pitching, game = simulate_game(game_num, player_ids, players_data)
    total_runs_for += our
    total_runs_against += their
    if our > their:
        total_wins += 1
    elif our < their:
        total_losses += 1
    else:
        total_draws += 1

    all_at_bats.extend(at_bats)
    all_pitching.append(pitching)
    all_games.append(game)

# Google Sheets에 배치로 저장
print("\n\n=== Google Sheets 저장 중... ===")

print(f"  타석 기록 {len(all_at_bats)}개 저장 중...")
db.add_at_bats_batch(all_at_bats)
print(f"  타석 기록 저장 완료!")
time.sleep(2)

print(f"  투구 기록 {len(all_pitching)}개 저장 중...")
for p in all_pitching:
    db.add_pitching(
        game_id=p['game_id'], player_id=p['player_id'], player_name=p['player_name'],
        innings=p['innings'], hits=p['hits'], runs=p['runs'], earned_runs=p['earned_runs'],
        walks=p['walks'], strikeouts=p['strikeouts'], home_runs=p['home_runs'],
        win=p['win'], loss=p['loss'], save=p['save']
    )
    time.sleep(0.5)
print(f"  투구 기록 저장 완료!")

print(f"  경기 기록 {len(all_games)}개 저장 중...")
for g in all_games:
    db.add_game(
        date=g['date'], opponent=g['opponent'], home_away=g['home_away'],
        our_score=g['our_score'], their_score=g['their_score'],
        stadium=g['stadium'], memo=g['memo']
    )
    time.sleep(0.5)
print(f"  경기 기록 저장 완료!")

print("\n" + "="*50)
print("          시뮬레이션 완료!")
print("="*50)
print(f"\n  시즌 성적: {total_wins}승 {total_losses}패 {total_draws}무")
if total_wins + total_losses > 0:
    print(f"  승률: {total_wins/(total_wins+total_losses)*100:.1f}%")
print(f"  총 득점: {total_runs_for}점 | 총 실점: {total_runs_against}점")
print(f"  평균 득점: {total_runs_for/10:.1f}점 | 평균 실점: {total_runs_against/10:.1f}점")
print("\n  모든 기록이 Google Sheets에 저장되었습니다!")
print("  https://savermetrics.streamlit.app/ 에서 확인하세요!")
