"""
세이버메트릭스 계산 모듈
사회인야구용 주요 지표 계산
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class BattingStats:
    """타격 기록"""
    plate_appearances: int = 0  # 타석
    at_bats: int = 0           # 타수
    hits: int = 0              # 안타
    doubles: int = 0           # 2루타
    triples: int = 0           # 3루타
    home_runs: int = 0         # 홈런
    walks: int = 0             # 볼넷
    strikeouts: int = 0        # 삼진
    hit_by_pitch: int = 0      # 사구
    sacrifice_flies: int = 0   # 희생플라이
    sacrifice_bunts: int = 0   # 희생번트
    rbis: int = 0              # 타점
    runs: int = 0              # 득점
    stolen_bases: int = 0      # 도루
    caught_stealing: int = 0   # 도루실패

    @property
    def singles(self) -> int:
        """단타"""
        return self.hits - self.doubles - self.triples - self.home_runs

    @property
    def total_bases(self) -> int:
        """루타"""
        return self.singles + (self.doubles * 2) + (self.triples * 3) + (self.home_runs * 4)


@dataclass
class PitchingStats:
    """투구 기록"""
    innings_pitched: float = 0.0  # 이닝 (5.1 = 5이닝 1아웃)
    hits_allowed: int = 0         # 피안타
    runs_allowed: int = 0         # 실점
    earned_runs: int = 0          # 자책점
    walks: int = 0                # 볼넷
    strikeouts: int = 0           # 삼진
    home_runs_allowed: int = 0    # 피홈런
    batters_faced: int = 0        # 상대타자
    wins: int = 0                 # 승
    losses: int = 0               # 패
    saves: int = 0                # 세이브

    @property
    def innings_decimal(self) -> float:
        """이닝을 소수점으로 변환 (5.1 -> 5.333...)"""
        full_innings = int(self.innings_pitched)
        partial = self.innings_pitched - full_innings
        outs = round(partial * 10)
        return full_innings + (outs / 3)


class SabermetricsCalculator:
    """세이버메트릭스 지표 계산기"""

    # wOBA 가중치 (MLB 기준, 사회인야구에 맞게 조정 가능)
    WOBA_WEIGHTS = {
        'bb': 0.69,
        'hbp': 0.72,
        'single': 0.87,
        'double': 1.27,
        'triple': 1.62,
        'hr': 2.10
    }

    # FIP 상수 (리그 평균에 따라 조정)
    FIP_CONSTANT = 3.10

    # === 타격 지표 ===

    @staticmethod
    def avg(stats: BattingStats) -> Optional[float]:
        """타율 (AVG) = 안타 / 타수"""
        if stats.at_bats == 0:
            return None
        return stats.hits / stats.at_bats

    @staticmethod
    def obp(stats: BattingStats) -> Optional[float]:
        """출루율 (OBP) = (안타 + 볼넷 + 사구) / (타수 + 볼넷 + 사구 + 희생플라이)"""
        denominator = stats.at_bats + stats.walks + stats.hit_by_pitch + stats.sacrifice_flies
        if denominator == 0:
            return None
        numerator = stats.hits + stats.walks + stats.hit_by_pitch
        return numerator / denominator

    @staticmethod
    def slg(stats: BattingStats) -> Optional[float]:
        """장타율 (SLG) = 루타 / 타수"""
        if stats.at_bats == 0:
            return None
        return stats.total_bases / stats.at_bats

    @staticmethod
    def ops(stats: BattingStats) -> Optional[float]:
        """OPS = 출루율 + 장타율"""
        obp = SabermetricsCalculator.obp(stats)
        slg = SabermetricsCalculator.slg(stats)
        if obp is None or slg is None:
            return None
        return obp + slg

    @staticmethod
    def iso(stats: BattingStats) -> Optional[float]:
        """순장타율 (ISO) = 장타율 - 타율"""
        slg = SabermetricsCalculator.slg(stats)
        avg = SabermetricsCalculator.avg(stats)
        if slg is None or avg is None:
            return None
        return slg - avg

    @staticmethod
    def woba(stats: BattingStats) -> Optional[float]:
        """가중출루율 (wOBA)"""
        denominator = stats.at_bats + stats.walks + stats.sacrifice_flies + stats.hit_by_pitch
        if denominator == 0:
            return None

        weights = SabermetricsCalculator.WOBA_WEIGHTS
        numerator = (
            weights['bb'] * stats.walks +
            weights['hbp'] * stats.hit_by_pitch +
            weights['single'] * stats.singles +
            weights['double'] * stats.doubles +
            weights['triple'] * stats.triples +
            weights['hr'] * stats.home_runs
        )
        return numerator / denominator

    @staticmethod
    def bb_rate(stats: BattingStats) -> Optional[float]:
        """볼넷비율 (BB%) = 볼넷 / 타석"""
        if stats.plate_appearances == 0:
            return None
        return stats.walks / stats.plate_appearances

    @staticmethod
    def k_rate(stats: BattingStats) -> Optional[float]:
        """삼진비율 (K%) = 삼진 / 타석"""
        if stats.plate_appearances == 0:
            return None
        return stats.strikeouts / stats.plate_appearances

    @staticmethod
    def babip(stats: BattingStats) -> Optional[float]:
        """인플레이 타율 (BABIP) = (안타 - 홈런) / (타수 - 삼진 - 홈런 + 희생플라이)"""
        denominator = stats.at_bats - stats.strikeouts - stats.home_runs + stats.sacrifice_flies
        if denominator == 0:
            return None
        numerator = stats.hits - stats.home_runs
        return numerator / denominator

    # === 투구 지표 ===

    @staticmethod
    def era(stats: PitchingStats) -> Optional[float]:
        """평균자책점 (ERA) = (자책점 * 9) / 이닝"""
        if stats.innings_decimal == 0:
            return None
        return (stats.earned_runs * 9) / stats.innings_decimal

    @staticmethod
    def whip(stats: PitchingStats) -> Optional[float]:
        """WHIP = (볼넷 + 피안타) / 이닝"""
        if stats.innings_decimal == 0:
            return None
        return (stats.walks + stats.hits_allowed) / stats.innings_decimal

    @staticmethod
    def k_per_9(stats: PitchingStats) -> Optional[float]:
        """9이닝당 삼진 (K/9) = (삼진 * 9) / 이닝"""
        if stats.innings_decimal == 0:
            return None
        return (stats.strikeouts * 9) / stats.innings_decimal

    @staticmethod
    def bb_per_9(stats: PitchingStats) -> Optional[float]:
        """9이닝당 볼넷 (BB/9) = (볼넷 * 9) / 이닝"""
        if stats.innings_decimal == 0:
            return None
        return (stats.walks * 9) / stats.innings_decimal

    @staticmethod
    def hr_per_9(stats: PitchingStats) -> Optional[float]:
        """9이닝당 피홈런 (HR/9) = (피홈런 * 9) / 이닝"""
        if stats.innings_decimal == 0:
            return None
        return (stats.home_runs_allowed * 9) / stats.innings_decimal

    @staticmethod
    def k_bb_ratio(stats: PitchingStats) -> Optional[float]:
        """삼진/볼넷 비율 (K/BB)"""
        if stats.walks == 0:
            return None if stats.strikeouts == 0 else float('inf')
        return stats.strikeouts / stats.walks

    @staticmethod
    def fip(stats: PitchingStats) -> Optional[float]:
        """수비무관 평균자책점 (FIP) = ((13*HR + 3*BB - 2*K) / IP) + 상수"""
        if stats.innings_decimal == 0:
            return None
        numerator = (13 * stats.home_runs_allowed) + (3 * stats.walks) - (2 * stats.strikeouts)
        return (numerator / stats.innings_decimal) + SabermetricsCalculator.FIP_CONSTANT


def format_stat(value: Optional[float], decimals: int = 3, multiply_100: bool = False) -> str:
    """지표값을 문자열로 포맷팅"""
    if value is None:
        return "-"
    if multiply_100:
        value *= 100
    return f"{value:.{decimals}f}"


def format_avg(value: Optional[float]) -> str:
    """타율 형식 (.000)"""
    if value is None:
        return "-"
    return f"{value:.3f}"


def format_era(value: Optional[float]) -> str:
    """ERA 형식 (0.00)"""
    if value is None:
        return "-"
    return f"{value:.2f}"


def format_percentage(value: Optional[float]) -> str:
    """백분율 형식 (00.0%)"""
    if value is None:
        return "-"
    return f"{value * 100:.1f}%"
