"""
QQAQC GAN Framework · 8대 대한민국 대표 사업주 비즈니스 모델(BM) 원형
다양한 업종, 생애주기, 대표자 성별·나이, 지역, 인증 및 재무 스펙을 포괄합니다.
"""
from __future__ import annotations

from typing import Any, Dict, List


BUSINESS_MODEL_ARCHETYPES: List[Dict[str, Any]] = [
    # -------------------------------------------------------------
    # BM 1: 심리상담/멘탈헬스 비R&D 플랫폼 (서비스·소셜)
    # -------------------------------------------------------------
    {
        "bm_id": "BM-01-PSYCH-PLATFORM",
        "name": "마음숲 테크 (온라인 심리상담·마인드케어 플랫폼)",
        "industry": "사회서비스 / 디지털 헬스케어 (비R&D 플랫폼)",
        "company_name": "(주)마음숲연구소",
        "biz_reg_no": "607-81-12345",
        "opened_date": "2024-03-01",     # 업력 2.7년 (초기창업)
        "founder_birth": "1994-05-15",   # 만 32세 (청년)
        "founder_gender": "F",           # 여성기업
        "address": "부산광역시 해운대구 센텀중앙로 48",
        "debt_ratio_pct": 180.0,
        "has_rnd_lab": False,            # 연구소 없음 (비R&D)
        "is_capital_impaired": False,
        "has_tax_arrears": False,
        "current_pi_projects": 0,
        "registered_patents_count": 2,
        "prior_grant_history": ["2023년 예비창업패키지"],
        "certifications": ["여성기업", "벤처기업", "소셜벤처"],
        "keywords": ["심리상담", "정신건강", "마음건강", "멘탈케어", "사회서비스", "플랫폼"],
        "core_tech_type": "NON_RND_SERVICE",
    },

    # -------------------------------------------------------------
    # BM 2: 기후테크 탄소회계/dMRV B2B 딥테크 SaaS
    # -------------------------------------------------------------
    {
        "bm_id": "BM-02-CARBON-DMRV",
        "name": "카본매트릭스 (IoT/위성기반 탄소배출 모니터링 dMRV)",
        "industry": "기후테크 / 탄소중립 / B2B SaaS",
        "company_name": "(주)카본매트릭스",
        "biz_reg_no": "105-87-65432",
        "opened_date": "2022-09-01",     # 업력 4.1년 (도약기)
        "founder_birth": "1981-11-20",   # 만 45세 (비청년)
        "founder_gender": "M",           # 남성
        "address": "서울특별시 강남구 테헤란로 152",
        "debt_ratio_pct": 85.0,          # 우량 재무
        "has_rnd_lab": True,             # 기업부설연구소 보유
        "is_capital_impaired": False,
        "has_tax_arrears": False,
        "current_pi_projects": 1,
        "registered_patents_count": 5,
        "prior_grant_history": ["2023년 팁스(TIPS)"],
        "certifications": ["벤처기업", "이노비즈"],
        "keywords": ["탄소중립", "온실가스", "배출량 산정", "dMRV", "기후테크", "ESG"],
        "core_tech_type": "DEEP_TECH_RND",
    },

    # -------------------------------------------------------------
    # BM 3: 음성 AI 대화형 에이전트 스케일업
    # -------------------------------------------------------------
    {
        "bm_id": "BM-03-VOICE-AI",
        "name": "보이스웨이브 (온디바이스 LLM 음성 인터페이스)",
        "industry": "인공지능(AI) / 음성합성 / 생성형 AI",
        "company_name": "(주)보이스웨이브",
        "biz_reg_no": "314-86-11223",
        "opened_date": "2020-04-10",     # 업력 6.5년 (창업도약 3~7년)
        "founder_birth": "1984-08-01",   # 만 42세
        "founder_gender": "M",
        "address": "대전광역시 유성구 대학로 291",
        "debt_ratio_pct": 140.0,
        "has_rnd_lab": True,
        "is_capital_impaired": False,
        "has_tax_arrears": False,
        "current_pi_projects": 2,        # 2책 수행중 (추가 1개 가능)
        "registered_patents_count": 8,
        "prior_grant_history": ["2021년 초기창업패키지", "2023년 디딤돌 R&D"],
        "certifications": ["벤처기업", "메인비즈"],
        "keywords": ["인공지능", "음성인식", "음성합성", "온디바이스 AI", "자연어처리", "LLM"],
        "core_tech_type": "DEEP_TECH_RND",
    },

    # -------------------------------------------------------------
    # BM 4: 로컬 F&B 애그리테크 & 특산물 가공
    # -------------------------------------------------------------
    {
        "bm_id": "BM-04-LOCAL-AGRITECH",
        "name": "남도팜스 (친환경 나주배 바이오 가공 및 스마트 농식품)",
        "industry": "농식품 / 스마트팜 / 로컬크리에이터",
        "company_name": "(주)남도팜스",
        "biz_reg_no": "412-88-77889",
        "opened_date": "2025-02-15",     # 업력 1.7년 (초기창업)
        "founder_birth": "1998-02-10",   # 만 28세 (청년)
        "founder_gender": "F",           # 여성대표
        "address": "전라남도 나주시 배향로 100",
        "debt_ratio_pct": 60.0,
        "has_rnd_lab": False,
        "is_capital_impaired": False,
        "has_tax_arrears": False,
        "current_pi_projects": 0,
        "registered_patents_count": 1,
        "prior_grant_history": [],
        "certifications": ["여성기업", "농식품벤처"],
        "keywords": ["농식품", "스마트팜", "로컬크리에이터", "지역특산물", "식품가공", "친환경"],
        "core_tech_type": "LOCAL_AGRI_SERVICE",
    },

    # -------------------------------------------------------------
    # BM 5: 바이오·디지털치료제(DTx) 임상 R&D
    # -------------------------------------------------------------
    {
        "bm_id": "BM-05-BIO-DTX",
        "name": "오송뉴로바이오 (인지장애 개선 디지털치료기기 전자약)",
        "industry": "바이오헬스 / 의료기기 / 디지털치료제(DTx)",
        "company_name": "(주)오송뉴로바이오",
        "biz_reg_no": "503-82-44556",
        "opened_date": "2023-01-20",     # 업력 3.8년
        "founder_birth": "1974-06-30",   # 만 52세 (의사 출신)
        "founder_gender": "M",
        "address": "충청북도 청주시 흥덕구 오송읍 오송생명1로 10",
        "debt_ratio_pct": 280.0,
        "has_rnd_lab": True,             # 전담 연구소 필수
        "is_capital_impaired": False,
        "has_tax_arrears": False,
        "current_pi_projects": 1,
        "registered_patents_count": 7,
        "prior_grant_history": ["2023년 바이오 특화 R&D"],
        "certifications": ["벤처기업", "이노비즈"],
        "keywords": ["바이오헬스", "디지털치료제", "의료기기", "임상시험", "전자약", "신경인지"],
        "core_tech_type": "DEEP_TECH_RND",
    },

    # -------------------------------------------------------------
    # BM 6: 시니어 케어 및 취약계층 소셜벤처
    # -------------------------------------------------------------
    {
        "bm_id": "BM-06-SOCIAL-SENIOR",
        "name": "실버케어넷 (독거노인 AI 안심 돌봄 및 시니어 일자리 플랫폼)",
        "industry": "사회서비스 / 소셜벤처 / 돌봄복지",
        "company_name": "(주)실버케어넷",
        "biz_reg_no": "602-85-33441",
        "opened_date": "2023-09-01",     # 업력 3.1년
        "founder_birth": "1978-04-12",   # 만 48세
        "founder_gender": "F",           # 여성대표
        "address": "광주광역시 서구 상무중앙로 80",
        "debt_ratio_pct": 110.0,
        "has_rnd_lab": False,
        "is_capital_impaired": False,
        "has_tax_arrears": False,
        "current_pi_projects": 0,
        "registered_patents_count": 1,
        "prior_grant_history": ["2024년 사회적기업가육성사업"],
        "certifications": ["사회적기업", "여성기업", "소셜벤처"],
        "keywords": ["사회서비스", "돌봄", "노인복지", "취약계층", "사회적기업", "일자리"],
        "core_tech_type": "SOCIAL_POLICY_SERVICE",
    },

    # -------------------------------------------------------------
    # BM 7: 국방 방산 드론 및 항재밍 하드웨어
    # -------------------------------------------------------------
    {
        "bm_id": "BM-07-DEFENSE-DRONE",
        "name": "에어로디펜스 (군용 대드론 재밍건 및 군집비행 자율제어)",
        "industry": "국방 / 방위산업 / 항공우주 드론",
        "company_name": "(주)에어로디펜스",
        "biz_reg_no": "609-81-77665",
        "opened_date": "2021-06-15",     # 업력 5.4년 (도약기)
        "founder_birth": "1971-12-05",   # 만 54세 (군 장교 출신)
        "founder_gender": "M",
        "address": "경상남도 창원시 성산구 창원대로 700",
        "debt_ratio_pct": 190.0,
        "has_rnd_lab": True,
        "is_capital_impaired": False,
        "has_tax_arrears": False,
        "current_pi_projects": 1,
        "registered_patents_count": 9,
        "prior_grant_history": ["2023년 국방벤처과제"],
        "certifications": ["벤처기업", "방산전문기업등록"],
        "keywords": ["방위산업", "국방", "무인기", "드론", "항재밍", "레이더", "유도무기"],
        "core_tech_type": "DEEP_TECH_RND",
    },

    # -------------------------------------------------------------
    # BM 8: 글로벌 결제·외환 핀테크
    # -------------------------------------------------------------
    {
        "bm_id": "BM-08-FINTECH-PAY",
        "name": "페이글로벌 (소액 해외송금 및 AI 이상금융거래 탐지 FDS)",
        "industry": "핀테크 / 금융보안 / 글로벌 결제",
        "company_name": "(주)페이글로벌",
        "biz_reg_no": "118-87-88990",
        "opened_date": "2024-01-15",     # 업력 2.8년 (초기창업)
        "founder_birth": "1988-09-25",   # 만 38세 (청년)
        "founder_gender": "M",
        "address": "서울특별시 영등포구 여의대로 56",
        "debt_ratio_pct": 470.0,          # 부채비율 높음 (단, 3년미만 특례 해당)
        "has_rnd_lab": True,
        "is_capital_impaired": False,
        "has_tax_arrears": False,
        "current_pi_projects": 0,
        "registered_patents_count": 3,
        "prior_grant_history": ["2024년 핀테크 큐브"],
        "certifications": ["벤처기업"],
        "keywords": ["핀테크", "해외송금", "전자금융", "이상거래탐지", "FDS", "블록체인"],
        "core_tech_type": "DEEP_TECH_RND",
    },
]
