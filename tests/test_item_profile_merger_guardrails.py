"""
성별/신분 판정 및 상속 가드레일 엄격 검증 테스트
- 미지정 성별에 대한 임의 추정(F/M) 100% 원천 차단
- 남성(M) 또는 미지정('') 대표자에 대한 여성기업 자격 법적 배제 원칙 보장
- 글로벌 프로필 상속 시 성별 불일치 가드레일 동작 검증
- AI 사업계획서 추출기(ProposalExtractor)의 성별 미추정 원칙 검증
"""
import pytest
from src.common.item_profile_merger import merge_item_company_specs
from src.matcher.preflight import PreflightService, DEFAULT_PROFILE
from src.matcher.applicant_profiler import ApplicantProfiler
from src.parser.proposal_extractor import ProposalExtractor


def test_merge_specs_empty_gender_no_female_cert_leakage():
    """글로벌 프로필의 대표자 성별이 미지정('')인 경우, 인증서에 여성기업이 오기재되어 있더라도 여성기업 배제."""
    global_p = {
        "company_name": "(주)마음숲연구소",
        "biz_reg_no": "607-81-12345",
        "founder_gender": "",  # 성별 미기재
        "certifications": ["여성기업", "벤처기업"],
    }
    item_specs = {
        "founder_gender": "",  # 미입력 (상속 요청)
    }
    effective = merge_item_company_specs(item_specs, global_p)

    # 대표자가 여성이 명백히 아니므로 여성기업 인증서 배제
    assert "여성기업" not in effective["certifications"]
    assert "벤처기업" in effective["certifications"]


def test_merge_specs_explicit_male_strips_female_cert():
    """대표자가 남성(M)인 경우, 여성기업 인증서 원천 제거."""
    global_p = {
        "company_name": "(주)글로벌테크",
        "biz_reg_no": "123-45-67890",
        "founder_gender": "F",
        "certifications": ["여성기업", "이노비즈"],
    }
    item_specs = {
        "founder_gender": "M",
    }
    effective = merge_item_company_specs(item_specs, global_p)

    assert effective["founder_gender"] == "M"
    assert "여성기업" not in effective["certifications"]
    assert "이노비즈" in effective["certifications"]


def test_merge_specs_explicit_none_gender():
    """성별 'NONE'(미지정/비공개) 선택 시 founder_gender='' 로 정규화되고 여성기업 배제."""
    global_p = {
        "company_name": "(주)한국인공지능",
        "biz_reg_no": "111-22-33333",
        "founder_gender": "F",
        "certifications": ["여성기업"],
    }
    item_specs = {
        "founder_gender": "NONE",
    }
    effective = merge_item_company_specs(item_specs, global_p)

    assert effective["founder_gender"] == ""
    assert "여성기업" not in effective["certifications"]


def test_preflight_compute_qualifications_male_never_female_founder():
    """남성(M) 대표는 어떠한 경우에도 is_female_founder=True가 될 수 없음."""
    pf = PreflightService()
    profile = {
        "founder_gender": "M",
        "certifications": ["여성기업", "벤처기업"],  # 잘못 섞여 들어왔더라도
        "opened_date": "2024-01-01",
        "founder_birth": "1995-01-01",
    }
    res = pf.compute_qualifications(profile)
    assert res["is_female_founder"] is False
    assert not any("여성기업" in tag for tag in res["tags"])


def test_preflight_compute_qualifications_empty_gender_never_assumes_female():
    """성별이 비어있는 경우('', None) 여성기업으로 임의 추정 금지."""
    pf = PreflightService()
    profile = {
        "founder_gender": "",
        "opened_date": "2024-01-01",
    }
    res = pf.compute_qualifications(profile)
    assert res["is_female_founder"] is False
    assert not any("여성기업" in tag for tag in res["tags"])


def test_applicant_profiler_legal_guardrail():
    """ApplicantProfiler: founder_gender == 'M'이면 is_female_founder는 무조건 False."""
    profiler = ApplicantProfiler()
    p = profiler.profile_from_data(
        company_name="테스트상사",
        biz_reg_no="123-45-67890",
        founder_gender="M",
        certifications=["여성기업"],  # 오기재된 경우
    )
    assert p.is_female_founder is False


def test_proposal_extractor_default_gender_is_empty():
    """성별 단서가 없는 일반 사업계획서에서는 성별을 'M'이나 'F'로 임의 단정하지 않고 ''로 추출."""
    text = """
    # 디지털 ESG 얼라이언스 소개서
    작성자: 홍길동
    회사: (주)아이디어
    설립: 2024년 1월
    내용: 디지털 탄소 배출량 측정 솔루션 개발
    """
    extractor = ProposalExtractor()
    extracted = extractor.extract_by_rules(text)
    specs = extracted["company_specs"]
    assert specs["founder_gender"] == ""
    assert "여성기업" not in specs["certifications"]
