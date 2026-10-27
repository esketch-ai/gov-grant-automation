"""
정부지원사업 자동화 시스템 전역 핵심 도메인 상수 (SSOT: Single Source of Truth)
- 안드레이 카파시 2원칙 (Simplicity First) 준수: 최소주의 단순 상수 정의
"""
import os

# 1. 청년 연령 기준 (만 나이)
YOUTH_AGE_LIMIT_GENERAL = 39   # 중소기업창업지원법 제2조 등 일반 청년창업 기준
YOUTH_AGE_LIMIT_SPECIAL = 34   # 조세특례제한법 및 특정 고용지원 기준

# 2. 기업 생애주기 업력 기준 (년)
BIZ_AGE_EARLY_STAGE_YEARS = 3.0   # 초기창업 (3년 이내)
BIZ_AGE_GROWTH_STAGE_YEARS = 7.0  # 창업도약 (7년 이내)

# 3. 매칭 및 적합도 기준
DEFAULT_MIN_MATCH_SCORE = 75      # 기본 최소 매칭 컷오프 점수 (0~100)

# 4. 기본 알림 및 시스템 환경
DEFAULT_NOTIFICATION_EMAIL = os.environ.get("DEFAULT_NOTIFICATION_EMAIL", "").strip()
