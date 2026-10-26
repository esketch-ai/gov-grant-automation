"""
QQAQC GAN Framework · 최진혁 수석적대공격관 (Red Team Generator)
시스템의 사각지대, 경계선 조건, 기만형 공고 및 위장 기업 프로필을 합성하여 생성합니다.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Tuple
from src.common.schemas import RawNotice


class AdversarialGenerator:
    """적대적 결함 및 기만형 데이터 생성기 (GAN Generator)."""

    def __init__(self, reference_date: date | None = None) -> None:
        self.ref_date = reference_date or date(2026, 10, 26)

    def generate_all_adversarial_scenarios(self) -> List[Dict[str, Any]]:
        """10대 적대적 결함 시나리오 일괄 합성."""
        return [
            self.scenario_age_boundary_over_39(),
            self.scenario_debt_ratio_over_500_mature(),
            self.scenario_year_disguised_notice(),
            self.scenario_fake_search_url_notice(),
            self.scenario_keyword_spoofing_military(),
            self.scenario_three_pi_projects_over_limit(),
            self.scenario_capital_impairment_violation(),
            self.scenario_tax_arrears_violation(),
            self.scenario_regional_mismatch(),
            self.scenario_package_double_benefit(),
            # --- RED TEAM 지속 고도화 추가 (2026-10-26 QAQC 감사 임무) ---
            self.scenario_debt_ratio_boundary_inclusive(),
            self.scenario_5ball_over_member_minor(),
            self.scenario_safe_degrade_unnormal_input(),
        ]

    # 1. 청년 나이 경계선: 만 39세 + 1일 초과
    def scenario_age_boundary_over_39(self) -> Dict[str, Any]:
        # 만 39세가 되는 날보다 하루 더 과거에 출생 -> 오늘 만 40세 0일
        birth_date = date(self.ref_date.year - 40, self.ref_date.month, self.ref_date.day) - timedelta(days=1)
        profile = {
            "company_name": "(주)경계선에이지",
            "biz_reg_no": "111-81-99991",
            "opened_date": "2024-01-01",
            "founder_birth": birth_date.isoformat(),
            "founder_gender": "F",
            "address": "서울특별시 강남구 테헤란로 1",
            "debt_ratio_pct": 120.0,
            "has_rnd_lab": True,
            "is_capital_impaired": False,
            "has_tax_arrears": False,
            "certifications": ["벤처기업"],
        }
        notice = RawNotice(
            portal_id="k_startup",
            title="2026년 청년창업사관학교(만 39세 이하 전용) 입교생 모집",
            organization="중진공",
            ministry="중기부",
            deadline="2026-11-30",
            detail_url="https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=175783",
            body_text="만 39세 이하의 청년 창업자만을 대상으로 하며 초과 시 즉시 결격 처리됩니다.",
        )
        return {
            "id": "ADV-01-AGE-BOUNDARY",
            "name": "만 39세 1일 초과 청년 가점 기만 공격",
            "expected_verdict": "RED_OR_DISQUALIFIED_FROM_YOUTH",
            "profile": profile,
            "notice": notice,
            "attack_description": "생년월일이 만 39세를 1일 초과하였으나 청년전용 사업에 신청하여 가점을 편취하려는 시도",
        }

    # 2. 부채비율 500% 초과 + 창업 5년차 (창업 3년 특례 사칭)
    def scenario_debt_ratio_over_500_mature(self) -> Dict[str, Any]:
        profile = {
            "company_name": "(주)과다부채기업",
            "biz_reg_no": "222-81-99992",
            "opened_date": "2021-01-01",  # 5.8년차 성숙기업 (3년 특례 제외)
            "founder_birth": "1988-03-01",
            "founder_gender": "M",
            "address": "서울특별시 서초구 반포대로 1",
            "debt_ratio_pct": 501.2,  # 500% 초과
            "has_rnd_lab": True,
            "is_capital_impaired": False,
            "has_tax_arrears": False,
        }
        notice = RawNotice(
            portal_id="iris",
            title="2026년도 산학연 Collabo R&D 신규지원 공고",
            organization="한국산학연협회",
            ministry="중기부",
            deadline="2026-11-15",
            detail_url="https://www.iris.go.kr/contents/retrieveBsnsAncmView.do?ancmId=022696",
            body_text="부채비율 500% 이상인 기업은 지원 제외 대상입니다. (단, 창업 3년 미만 기업은 예외 적용)",
        )
        return {
            "id": "ADV-02-DEBT-RATIO-MATURE",
            "name": "창업 5년차 부채비율 500.1% 특례 위장 공격",
            "expected_verdict": "RED",
            "profile": profile,
            "notice": notice,
            "attack_description": "창업 5년차로 3년 미만 부채비율 면제 특례를 받을 수 없으나 부채비율 501.2%로 신청한 케이스",
        }

    # 3. 2025년 과거 과제 제목만 위장한 공고
    def scenario_year_disguised_notice(self) -> Dict[str, Any]:
        profile = {
            "company_name": "(주)마음숲연구소",
            "biz_reg_no": "607-81-12345",
            "opened_date": "2024-03-01",
            "founder_birth": "1994-05-15",
            "founder_gender": "F",
            "address": "부산광역시 해운대구 센텀중앙로 48",
            "debt_ratio_pct": 180.0,
            "has_rnd_lab": False,
        }
        notice = RawNotice(
            portal_id="iris",
            title="2026년도 착시위장 국방 미래 무기체계 연구개발 공고 (실제 2025년 종료 과제)",
            organization="방위사업청",
            ministry="국방부",
            deadline="2025-10-31",  # 과거 마감
            detail_url="https://www.iris.go.kr/contents/retrieveBsnsAncmView.do?ancmId=015634",
            body_text="2025년도에 기 마감된 국방 과제로서 본문 내 마감일은 2025년 10월 31일입니다.",
        )
        return {
            "id": "ADV-03-YEAR-DISGUISED",
            "name": "과거 연도(2025) 제목 교묘 위장 공고 공격",
            "expected_verdict": "EXPIRED_OR_YEAR_REJECTED",
            "profile": profile,
            "notice": notice,
            "attack_description": "제목 앞단에만 '2026년'을 삽입하고 실제 마감일과 사업 연도는 2025년인 착시 공고",
        }

    # 4. 상세 ID가 누락된 가짜 검색 목록 URL
    def scenario_fake_search_url_notice(self) -> Dict[str, Any]:
        profile = {"company_name": "(주)정상기업", "opened_date": "2024-01-01"}
        notice = RawNotice(
            portal_id="iris",
            title="2026년 정보통신 방송 기술개발사업 공고",
            organization="IITP",
            ministry="과기정통부",
            deadline="2026-11-20",
            detail_url="https://www.iris.go.kr/contents/retrieveBsnsAncmList.do",  # 목록 URL (ancmId 누락)
            body_text="과기정통부 ICT R&D 공고입니다.",
        )
        return {
            "id": "ADV-04-FAKE-SEARCH-URL",
            "name": "식별자 없는 검색 목록 URL 기만 공격",
            "expected_verdict": "DEEPLINK_SYNTAX_FAILED",
            "profile": profile,
            "notice": notice,
            "attack_description": "상세 식별자(ancmId) 없이 검색 리스트 URL을 제공하여 브라우저 직링크 클릭을 무력화하려는 시도",
        }

    # 5. 키워드 스푸핑 (심리상담 키워드를 1회 사칭한 무기 R&D)
    def scenario_keyword_spoofing_military(self) -> Dict[str, Any]:
        profile = {
            "company_name": "(주)마음치유",
            "biz_reg_no": "333-81-99993",
            "opened_date": "2024-01-01",
            "founder_birth": "1995-01-01",
            "founder_gender": "F",
            "address": "부산광역시 해운대구",
            "debt_ratio_pct": 100.0,
            "has_rnd_lab": False,
        }
        notice = RawNotice(
            portal_id="ntis",
            title="2026년 첨단 유도미사일 초정밀 탄두 설계 기술개발 (심리상담 조종사 멘탈 관리 체계 일부 포함)",
            organization="국방과학연구소",
            ministry="국방부",
            deadline="2026-12-01",
            detail_url="https://www.ntis.go.kr/rndgate/eg/un/ra/view.do?roRndUid=1279968",
            body_text="본 과제는 고폭탄두 및 비행제어 소프트웨어를 개발하는 하드웨어 방위산업 R&D입니다. 조종사 심리 안정 관련은 부차적 요소입니다.",
        )
        return {
            "id": "ADV-05-KEYWORD-SPOOFING",
            "name": "군사 무기 체계의 심리상담 키워드 스푸핑 공격",
            "expected_verdict": "RED",
            "profile": profile,
            "notice": notice,
            "attack_description": "방위산업 무기 과제 본문에 '심리상담' 단어를 1회 끼워넣어 비R&D 플랫폼 기업에 오매칭을 유도하는 기만 공격",
        }

    # 6. 3책5공 위반: 이미 3개 과제 총괄책임자(PI) 수행 중
    def scenario_three_pi_projects_over_limit(self) -> Dict[str, Any]:
        profile = {
            "company_name": "(주)스타연구소",
            "biz_reg_no": "444-81-99994",
            "opened_date": "2023-01-01",
            "founder_birth": "1985-01-01",
            "address": "대전광역시 유성구",
            "current_pi_projects": 3,  # 3책 도달
            "has_rnd_lab": True,
            "debt_ratio_pct": 150.0,
        }
        notice = RawNotice(
            portal_id="iris",
            title="2026년도 바이오헬스 신약개발 기술개발사업 공고",
            organization="한국보건산업진흥원",
            ministry="복지부",
            deadline="2026-11-25",
            detail_url="https://www.iris.go.kr/contents/retrieveBsnsAncmView.do?ancmId=022696",
            body_text="국가연구개발혁신법에 따른 3책 5공 제한 규정이 엄격히 적용됩니다.",
        )
        return {
            "id": "ADV-06-3BOOK-5BALL-OVER",
            "name": "3책5공(총괄책임자 3건 한도) 초과 신청 공격",
            "expected_verdict": "RED",
            "profile": profile,
            "notice": notice,
            "attack_description": "이미 주관연구책임자(PI)로 3건을 수행 중인 연구자가 신규 R&D 주관기관으로 신청한 결격 케이스",
        }

    # 7. 자본전액잠식 상태 숨김
    def scenario_capital_impairment_violation(self) -> Dict[str, Any]:
        profile = {
            "company_name": "(주)잠식테크",
            "biz_reg_no": "555-81-99995",
            "opened_date": "2023-01-01",
            "is_capital_impaired": True,  # 자본전액잠식
            "debt_ratio_pct": 800.0,
            "has_rnd_lab": True,
        }
        notice = RawNotice(
            portal_id="iris",
            title="2026년도 ICT 융복합 글로벌 진출 지원사업 공고",
            organization="NIPA",
            ministry="과기정통부",
            deadline="2026-11-30",
            detail_url="https://www.iris.go.kr/contents/retrieveBsnsAncmView.do?ancmId=022696",
            body_text="자본전액잠식 기업은 신청 자격이 없습니다.",
        )
        return {
            "id": "ADV-07-CAPITAL-IMPAIRMENT",
            "name": "자본전액잠식 결격 사유 은닉 공격",
            "expected_verdict": "RED",
            "profile": profile,
            "notice": notice,
            "attack_description": "자본전액잠식 상태로 정부지원금 R&D 신청 시 즉시 탈락해야 함",
        }

    # 8. 국세/지방세 체납
    def scenario_tax_arrears_violation(self) -> Dict[str, Any]:
        profile = {
            "company_name": "(주)체납기업",
            "biz_reg_no": "666-81-99996",
            "opened_date": "2024-01-01",
            "has_tax_arrears": True,  # 국세/지방세 체납
            "debt_ratio_pct": 100.0,
            "has_rnd_lab": True,
        }
        notice = RawNotice(
            portal_id="k_startup",
            title="2026년도 혁신 스타트업 기술사업화 지원사업",
            organization="창진원",
            ministry="중기부",
            deadline="2026-11-30",
            detail_url="https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=175783",
            body_text="국세 및 지방세 체납자는 신청 제외됩니다.",
        )
        return {
            "id": "ADV-08-TAX-ARREARS",
            "name": "국세·지방세 체납 결격 은닉 공격",
            "expected_verdict": "RED",
            "profile": profile,
            "notice": notice,
            "attack_description": "국세 또는 지방세 체납 중인 기업이 지원하는 경우 무관용 결격 처리",
        }

    # 9. 지역 불일치 (부산 기업이 서울 한정 공고 지원)
    def scenario_regional_mismatch(self) -> Dict[str, Any]:
        profile = {
            "company_name": "(주)부산로컬",
            "biz_reg_no": "777-81-99997",
            "opened_date": "2024-01-01",
            "address": "부산광역시 해운대구 센텀중앙로 48",
            "debt_ratio_pct": 100.0,
            "has_rnd_lab": False,
        }
        notice = RawNotice(
            portal_id="k_startup",
            title="2026년 서울창업허브 공덕 입주기업 모집 (서울시 본점 한정)",
            organization="서울경제진흥원",
            ministry="서울시",
            deadline="2026-11-20",
            detail_url="https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=175783",
            body_text="신청 자격: 서울특별시에 사업자등록을 필한 본점 또는 연구소 소재 기업 한정. 타 시도 지원 불가.",
        )
        return {
            "id": "ADV-09-REGIONAL-MISMATCH",
            "name": "타 지자체(서울) 전용 공고에 부산 기업 오지원 공격",
            "expected_verdict": "RED_OR_DISQUALIFIED_FROM_REGION",
            "profile": profile,
            "notice": notice,
            "attack_description": "서울시 전용 공고에 부산 소재 기업이 지원할 때 지역 필터가 즉시 탈락 또는 감점 처리해야 함",
        }

    # 10. 패키지 중복 수혜 (2025 초기창업패키지 수혜 후 2026 예비/초기창업 재신청)
    def scenario_package_double_benefit(self) -> Dict[str, Any]:
        profile = {
            "company_name": "(주)기수혜기업",
            "biz_reg_no": "888-81-99998",
            "opened_date": "2024-01-01",
            "prior_grant_history": ["2025년도 초기창업패키지"],  # 기수혜 이력
            "debt_ratio_pct": 120.0,
            "has_rnd_lab": False,
        }
        notice = RawNotice(
            portal_id="k_startup",
            title="2026년도 초기창업패키지 창업기업 모집공고",
            organization="창진원",
            ministry="중기부",
            deadline="2026-11-20",
            detail_url="https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=175783",
            body_text="기존 예비·초기·도약패키지 수혜 기업은 중복 지원이 제한됩니다.",
        )
        return {
            "id": "ADV-10-PACKAGE-DOUBLE-BENEFIT",
            "name": "초기창업패키지 기수혜자의 중복지원 기만 공격",
            "expected_verdict": "RED",
            "profile": profile,
            "notice": notice,
            "attack_description": "동일 생애주기 패키지를 이미 수혜한 이력이 있으면서 또다시 초기창업패키지에 신청한 결격 케이스",
        }

    # 11. 부채비율 상한 경계값(500%) 포함 탈락 편취 공격 (성숙기업)
    def scenario_debt_ratio_boundary_inclusive(self) -> Dict[str, Any]:
        # 부채비율이 상한(500%)에 정확히 일치하는 성숙기업 -> '500% 미만' 기준 오인 시 오탐 방어 필요
        profile = {
            "company_name": "(주)경계선에이지",
            "biz_reg_no": "121-81-99991",
            "opened_date": "2021-01-01",  # 5.8년차 성숙기업 (창업 3년 특례 적용 불가)
            "founder_birth": "1985-03-01",
            "founder_gender": "M",
            "address": "서울특별시 서초구 반포대로 1",
            "debt_ratio_pct": 500.0,  # 상한 경계값 포함(500%)
            "has_rnd_lab": True,
            "is_capital_impaired": False,
            "has_tax_arrears": False,
            "tags": ["인공지능"],
        }
        notice = RawNotice(
            portal_id="iris",
            title="2026년도 인공지능(AI) 바이오헬스 신약개발 기술개발사업 공고",
            organization="한국보건산업진흥원",
            ministry="복지부",
            deadline="2026-11-15",
            detail_url="https://www.iris.go.kr/contents/retrieveBsnsAncmView.do?ancmId=022696",
            body_text="인공지능 기반 신약개발 R&D 수행. 기업부설연구소 및 AI R&D 보유가 요구됩니다. 부채비율 500% 이상인 기업은 지원 제외 대상입니다. (단, 창업 3년 미만 기업은 예외 적용)",
        )
        return {
            "id": "ADV-11-DEBT-RATIO-BOUNDARY-INCLUSIVE",
            "name": "부채비율 상한 경계값(500%) 포함 탈락 편취 공격",
            "expected_verdict": "RED",
            "profile": profile,
            "notice": notice,
            "attack_description": "부채비율이 상한(500%)에 정확히 도달한 성숙기업이 '500% 초과' 기준으로만 오인하여 오탐 방어(지원 허용)하는 기만 시도",
        }

    # 12. 참여연구원(멤버) 합산 5공 한도 초과 공격
    def scenario_5ball_over_member_minor(self) -> Dict[str, Any]:
        profile = {
            "company_name": "(주)스타연구소",
            "biz_reg_no": "144-81-99997",
            "opened_date": "2023-01-01",
            "founder_birth": "1985-01-01",
            "address": "대전광역시 유성구",
            "debt_ratio_pct": 150.0,
            "has_rnd_lab": True,
            "current_pi_projects": 2,  # PI 2건 수행 중
            "current_member_projects": 3,  # PI 2 + 멤버 3 = 총 5공 한도 초과
        }
        notice = RawNotice(
            portal_id="iris",
            title="2026년도 바이오헬스 신약개발 기술개발사업 공고",
            organization="한국보건산업진흥원",
            ministry="복지부",
            deadline="2026-11-25",
            detail_url="https://www.iris.go.kr/contents/retrieveBsnsAncmView.do?ancmId=022696",
            body_text="국가연구개발혁신법에 따른 3책 5공 제한 규정이 엄격히 적용됩니다.",
        )
        return {
            "id": "ADV-12-5BALL-OVER-MEMBER-MINOR",
            "name": "참여연구원 5공 동시 수행 한도 초과 공격",
            "expected_verdict": "RED",
            "profile": profile,
            "notice": notice,
            "attack_description": "PI 2건 + 참여연구원 3명이 동시에 총 5공을 수행 중인데, PI 한계(3책)는 미달임에도 불구하고 5공 한도를 초과하는 신청을 허용하는 기만 시도",
        }

    # 13. 비정상 입력 타입 크래시 공격 (안전 디그레이드 검증)
    def scenario_safe_degrade_unnormal_input(self) -> Dict[str, Any]:
        profile = {
            "company_name": "(주)비정상기업",
            "biz_reg_no": "155-81-99998",
            "opened_date": "2024-01-01",
            "founder_birth": "1995-01-01",
            "founder_gender": "F",
            "address": "부산광역시 해운대구",
            "debt_ratio_pct": "INVALID_NUMERIC_TYPE",  # 비정상 타입 주입
            "has_rnd_lab": True,
        }
        notice = RawNotice(
            portal_id="k_startup",
            title="2026년도 혁신 스타트업 기술사업화 지원사업",
            organization="창진원",
            ministry="중기부",
            deadline="2026-11-30",
            detail_url="https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=175783",
            body_text="국세 및 지방세 체납자는 신청 제외됩니다.",
        )
        return {
            "id": "ADV-13-SAFER-DEGRADE-UNNORMAL-INPUT",
            "name": "비정상 입력 타입 크래시 공격",
            "expected_verdict": "RED",
            "profile": profile,
            "notice": notice,
            "attack_description": "재무 수치 필드에 비정상 타입 문자열을 주입하여 판정 엔진 크래시 유발 시도 -> 안전 디그레이드(Safe Degrade)에 의한 무결한 RED 처리 검증",
        }
