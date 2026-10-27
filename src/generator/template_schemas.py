"""
과제별 사업계획서 표준 템플릿 스키마 정의
(K-Startup PSST 표준 양식 및 중기부 SMTECH R&D 연구개발계획서 양식)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TemplateType(str, Enum):
    PSST = "PSST"
    RND_SMTECH = "RND_SMTECH"
    G2B_RFP = "G2B_RFP"
    LOCAL_HUB = "LOCAL_HUB"


@dataclass(frozen=True)
class SectionRequirement:
    """공고 양식 내 단일 섹션(문항)의 요구 규격."""
    section_id: str             # 예: "1-1", "1-2", "2-1"
    title: str                  # 예: "1-1. 창업아이템의 개발동기 및 필요성"
    category_name: str          # 대분류명 (예: "1. 문제인식 (Problem)")
    description: str            # 공고 지침 및 작성 가이드
    evaluation_focus: str       # 심사위원이 중점 평가하는 관점 (배점 요건)
    recommended_pages: str      # 권장 분량 (예: "1~2페이지")
    guiding_questions: List[str] # 팩트 결손 시 코파일럿이 사업자에게 물어볼 핵심 질문 2~3가지
    default_master_keys: List[str] = field(default_factory=list) # 마스터 프로필 연계 키

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProposalTemplate:
    """정부지원사업 표준 사업계획서 템플릿 마스터 정의."""
    template_id: str            # 고유 ID (예: "PSST", "RND_SMTECH")
    name: str                   # 템플릿 공식 명칭
    target_agency: str          # 주관 부처 / 전담기관
    target_programs: str        # 대표 적용 과제 (예창패, 초창패, 디딤돌 등)
    description: str            # 템플릿 성격 및 특징
    tone_directive: str         # AI 맞춤 변환 프롬프트 작문 지침 (톤앤매너)
    sections: List[SectionRequirement]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "target_agency": self.target_agency,
            "target_programs": self.target_programs,
            "description": self.description,
            "tone_directive": self.tone_directive,
            "sections": [s.to_dict() for s in self.sections],
        }


# ==============================================================================
# 1. K-Startup PSST 표준 창업사업계획서 (창업진흥원 예창패/초창패/창도패 공통)
# ==============================================================================
PSST_TEMPLATE = ProposalTemplate(
    template_id="PSST",
    name="K-Startup PSST 표준 창업사업계획서",
    target_agency="중소벤처기업부 / 창업진흥원",
    target_programs="예비창업패키지, 초기창업패키지, 창업도약패키지, 청년창업사관학교",
    description="국내 창업지원사업의 80% 이상이 채택하는 표준 양식(문제인식-실현가능성-성장전략-팀구성). 고객 미충족 수요와 시장성 중심 평가.",
    tone_directive="고객의 문제(Pain Point), 시장성 및 지불의사 검증 사례, 구체적 매출 창출 파이프라인, 대표자 및 팀원의 실행력을 최우선 강조할 것. 지나치게 난해한 학술적 용어는 피하고 비즈니스 임팩트에 집중할 것.",
    sections=[
        SectionRequirement(
            section_id="1-1",
            title="1-1. 창업아이템의 개발 배경 및 필요성",
            category_name="1. 문제인식 (Problem)",
            description="창업 아이템을 왜 개발하게 되었는지 배경과 시장의 기존 문제점(미충족 수요)을 서술합니다.",
            evaluation_focus="개발 동기의 진정성, 시장 내 페인포인트의 구체성 및 시장 수요의 객관적 근거",
            recommended_pages="1~2페이지",
            guiding_questions=[
                "기존 시장 제품이나 솔루션의 가장 치명적인 한계 또는 고객 불만은 무엇인가요?",
                "대표님께서 이 문제를 직접 겪으셨거나 해결해야겠다고 결심한 결정적 계기가 있으신가요?",
            ],
            default_master_keys=["problem", "summary", "keywords"],
        ),
        SectionRequirement(
            section_id="1-2",
            title="1-2. 목표 시장 및 고객 분석 (고객 검증)",
            category_name="1. 문제인식 (Problem)",
            description="목표로 하는 타깃 고객군(페르소나)의 특성과 시장 규모, 고객 검증 결과를 제시합니다.",
            evaluation_focus="타깃 고객의 명확성, 사전 고객 인터뷰/설문/POC 등 정량적 검증 실적",
            recommended_pages="1페이지 내외",
            guiding_questions=[
                "주요 타깃 고객층(연령, 성별, B2B 기업군 등)은 누구이며, 실제 인터뷰나 설문조사를 진행한 적이 있나요?",
                "타깃 고객이 본 솔루션에 실제로 지불할 의사가 있는 적정 가격대는 얼마인가요?",
            ],
            default_master_keys=["target_customers", "market_size", "summary"],
        ),
        SectionRequirement(
            section_id="2-1",
            title="2-1. 창업아이템의 개발 방안 및 구체화 현황",
            category_name="2. 실현가능성 (Solution)",
            description="아이템의 핵심 기능, 기술적 구현 방안, 현재 개발 진척도(시제품/MVP 여부)를 서술합니다.",
            evaluation_focus="개발 실현 가능성, 기술적 완성도, TRL 달성 수준, 협약 기간 내 제작 완료 가능 여부",
            recommended_pages="2~3페이지",
            guiding_questions=[
                "현재 개발 단계(아이디어 구상 / 와이어프레임 / 시제품 제작 완료 등)는 어디까지 진행되었나요?",
                "협약 기간 동안 구현할 핵심 기능 2~3가지는 무엇인가요?",
            ],
            default_master_keys=["solution", "tech_stack", "trl", "features"],
        ),
        SectionRequirement(
            section_id="2-2",
            title="2-2. 경쟁사 분석 및 차별화 경쟁우위",
            category_name="2. 실현가능성 (Solution)",
            description="국내외 주요 경쟁사 대비 자사 제품만의 독창적인 차별점 및 진입장벽을 비교 제시합니다.",
            evaluation_focus="경쟁사 대비 성능/가격/사용성 측면의 우위성, 지식재산권(특허) 확보 가능성",
            recommended_pages="1~2페이지 (비교 테이블 권장)",
            guiding_questions=[
                "기존 1위 경쟁사(또는 대체제)와 비교했을 때 자사만의 압도적인 차별점은 무엇인가요?",
                "경쟁사가 쉽게 모방하지 못하도록 방어할 수 있는 진입장벽(특허, 데이터, 노하우 등)이 있나요?",
            ],
            default_master_keys=["differentiation", "competitors", "patents"],
        ),
        SectionRequirement(
            section_id="3-1",
            title="3-1. 자금소요 및 조달 계획",
            category_name="3. 성장전략 (Scale-up)",
            description="정부지원금 사용 계획(인건비, 외주용역비, 마케팅비 등)과 자체 자금 확보 방안을 작성합니다.",
            evaluation_focus="예산 배분의 적정성, 자부담금 조달의 안정성, 사업비 집행의 구체성",
            recommended_pages="1페이지 내외 (소요예산 표 포함)",
            guiding_questions=[
                "지원받고자 하는 정부지원금의 주요 사용처(시제품 제작비, 마케팅비, 인건비 등) 비중은 어떻게 되나요?",
                "정부지원금 외에 기업 자부담금이나 외부 투자 유치 계획이 있으신가요?",
            ],
            default_master_keys=["funding_plan", "budget", "specs"],
        ),
        SectionRequirement(
            section_id="3-2",
            title="3-2. 시장진입 및 글로벌 마케팅 전략",
            category_name="3. 성장전략 (Scale-up)",
            description="수익 모델(BM), 고객 획득 채널, 단계별 판로 개척 및 해외 진출 로드맵을 서술합니다.",
            evaluation_focus="비즈니스 모델(BM)의 수익성, 구체적 고객 획득 비용(CAC) 절감 방안, 글로벌 확장성",
            recommended_pages="2페이지 내외",
            guiding_questions=[
                "주요 수익 모델(구독료, 건당 수수료, 완제품 판매 등)과 가격 책정 전략은 무엇인가요?",
                "초기 고객 100명(또는 10개 기업)을 유치하기 위한 구체적인 마케팅 채널은 무엇인가요?",
            ],
            default_master_keys=["business_model", "sales_channel", "marketing"],
        ),
        SectionRequirement(
            section_id="4-1",
            title="4-1. 대표자 및 팀원의 보유 역량",
            category_name="4. 팀구성 (Team)",
            description="대표자의 관련 전공/경력, 팀원의 전문성, 아이템 개발 수행 적합성을 서술합니다.",
            evaluation_focus="창업자의 실행력, 팀원의 기술/영업 전문성, 이전 창업 또는 실무 성공 경험",
            recommended_pages="1~2페이지",
            guiding_questions=[
                "대표자님의 전공이나 실무 경력 중 이번 아이템과 직결되는 핵심 강점은 무엇인가요?",
                "핵심 팀원(개발, 기획, 디자인 등)의 주요 이력이나 보유 기술 역량은 어떻게 되나요?",
            ],
            default_master_keys=["team", "founder_career", "company_specs"],
        ),
        SectionRequirement(
            section_id="4-2",
            title="4-2. 신규 고용 및 사회적 가치 실천 계획",
            category_name="4. 팀구성 (Team)",
            description="협약 기간 내 신규 인력 채용 계획, 청년 고용, ESG 및 지역사회 기여 방안을 서술합니다.",
            evaluation_focus="고용 창출 효과의 현실성, 근로 조건 및 성과공유제 도입 의지",
            recommended_pages="1페이지 내외",
            guiding_questions=[
                "올해 혹은 협약 기간 내 신규 채용 예정인 인원(직군, 인원수)은 몇 명인가요?",
                "친환경, 취약계층 고용, 지역사회 공헌 등 실천 가능한 사회적 가치가 있나요?",
            ],
            default_master_keys=["hiring_plan", "esg", "company_specs"],
        ),
    ],
)


# ==============================================================================
# 2. 중소벤처기업부 SMTECH 국가 R&D 연구개발계획서 (디딤돌 / TIPS / 창업성장)
# ==============================================================================
RND_SMTECH_TEMPLATE = ProposalTemplate(
    template_id="RND_SMTECH",
    name="중기부 SMTECH 국가R&D 연구개발계획서",
    target_agency="중소벤처기업부 / 중소기업기술정보진흥원 (TIPA)",
    target_programs="디딤돌 R&D, TIPS 프로그램, 창업성장기술개발, 중소기업 상용화 R&D",
    description="국가 R&D 자금 지원을 위한 연구개발계획서. 기술적 독창성, TRL 목표, 정량적 KPI 지표 테이블, 지재권 및 연구인프라 평가.",
    tone_directive="기술적 난제 극복 방안, 세계 최고 수준(Global Top Tier) 대비 기술적 우위, 정량적 성능 지표(공인인증기관 시험성적서 발급 계획), 특허 회피 및 선점 전략을 최우선 강조할 것. 추상적 다짐을 배제하고 엔지니어링 팩트와 수치로 서술할 것.",
    sections=[
        SectionRequirement(
            section_id="1-1",
            title="1-1. 기술개발의 필요성 및 개발 개요",
            category_name="1. 기술개발의 필요성",
            description="개발 대상 기술의 정의, 기존 기술의 한계점, 국가 차원의 개발 시급성을 기술합니다.",
            evaluation_focus="개발 대상 기술의 명확성, 기존 기술 대비 혁신성, R&D 지원의 당위성",
            recommended_pages="2~3페이지",
            guiding_questions=[
                "개발하고자 하는 핵심 기술의 메커니즘과 현재 시점의 기술적 한계(병목)는 무엇인가요?",
                "본 기술이 국산화 또는 글로벌 시장 선점을 위해 시급히 개발되어야 하는 이유는 무엇인가요?",
            ],
            default_master_keys=["summary", "problem", "tech_stack"],
        ),
        SectionRequirement(
            section_id="1-2",
            title="1-2. 국내외 관련 기술 및 시장 동향",
            category_name="1. 기술개발의 필요성",
            description="국내외 주요 선도 기업/연구기관의 기술 수준 비교, 시장 동향 및 특허 동향을 분석합니다.",
            evaluation_focus="국내외 선행기술 조사 충실도, 특허 회피/선점 전략, 시장 성장성(CAGR)",
            recommended_pages="2페이지 내외",
            guiding_questions=[
                "국내외 최고 수준(Global No.1) 경쟁사나 연구기관의 기술 스펙은 어느 수준인가요?",
                "선행 특허 침해 가능성을 검토하셨거나, 신규 회피설계/특허 출원 전략이 있으신가요?",
            ],
            default_master_keys=["competitors", "patents", "market_size"],
        ),
        SectionRequirement(
            section_id="2-1",
            title="2-1. 연구개발의 최종 목표 및 정량적 성능 지표 (KPI)",
            category_name="2. 연구개발의 목표 및 내용",
            description="연구개발의 최종 목표(TRL 도달 수준 포함)와 공인시험성적서를 통한 정량적 목표치를 제시합니다.",
            evaluation_focus="성능 지표의 객관성 및 도전성, 공인시험인증기관(KTR, KCL 등) 평가 가능 여부",
            recommended_pages="1~2페이지 (정량적 목표 테이블 필수)",
            guiding_questions=[
                "개발 완료 시 달성할 핵심 성능 지표 3~5가지(정확도, 응답속도, 내구성 등)와 목표 수치는 무엇인가요?",
                "이 성능 지표를 검증할 공인시험인증기관(예: KTL, KTR, TTA 등)이나 자체 평가 방법은 무엇인가요?",
            ],
            default_master_keys=["trl", "kpi", "performance_targets"],
        ),
        SectionRequirement(
            section_id="2-2",
            title="2-2. 세부 개발 내용 및 수행 방법 (추진 체계)",
            category_name="2. 연구개발의 목표 및 내용",
            description="시스템 아키텍처, 모듈별 세부 개발 계획, 연차별 마일스톤 및 위탁연구 연계 방안을 작성합니다.",
            evaluation_focus="개발 방법론의 타당성, 위험 요소(Risk)에 대한 대안 설계, 연구 추진 일정(Gantt)의 현실성",
            recommended_pages="4~6페이지",
            guiding_questions=[
                "핵심 개발 모듈(S/W 알고리즘, H/W 회로, 데이터 파이프라인 등)별 구체적인 구현 방식은 무엇인가요?",
                "개발 과정에서 발생할 수 있는 가장 큰 기술적 위험 요소와 이를 극복할 플랜 B는 무엇인가요?",
            ],
            default_master_keys=["solution", "tech_stack", "architecture"],
        ),
        SectionRequirement(
            section_id="3-1",
            title="3-1. 사업화 로드맵 및 양산·마케팅 계획",
            category_name="3. 사업화 전략 및 기대효과",
            description="과제 종료 후 양산 체계 구축, 판로 확보, 연차별 예상 매출액 및 투자 유치 계획을 제시합니다.",
            evaluation_focus="사업화 실현 가능성, 양산 및 단가 경쟁력 확보 방안, 초기 수요처(LoI/MOU) 확보 여부",
            recommended_pages="2페이지 내외",
            guiding_questions=[
                "R&D 종료 후 3년간 예상되는 연차별 매출액 목표(국내/해외)는 대략 얼마인가요?",
                "구매 의향서(LOI), 업무협약(MOU)을 맺었거나 협의 중인 초기 고객사/수요기업이 있나요?",
            ],
            default_master_keys=["business_model", "sales_channel", "financials"],
        ),
        SectionRequirement(
            section_id="3-2",
            title="3-2. 경제적·사회적 기대효과 및 고용 창출",
            category_name="3. 사업화 전략 및 기대효과",
            description="수입 대체 효과, 수출 증대, 신규 고용 창출, 산업 생태계 파급효과를 서술합니다.",
            evaluation_focus="국가 경제적 기여도, 양질의 청년/R&D 일자리 창출 효과",
            recommended_pages="1페이지 내외",
            guiding_questions=[
                "본 기술 개발 성공 시 해외 제품 수입 대체나 수출로 창출될 경제적 가치는 얼마인가요?",
                "향후 2년간 연구인력 및 일반 인력 신규 채용 계획은 몇 명인가요?",
            ],
            default_master_keys=["economic_impact", "hiring_plan"],
        ),
        SectionRequirement(
            section_id="4-1",
            title="4-1. 연구인력 및 연구시설·장비 보유 현황",
            category_name="4. 연구개발역량 및 인프라",
            description="연구책임자 및 참여연구원의 R&D 실적(논문, 특허, 유사과제), 보유 연구 장비를 작성합니다.",
            evaluation_focus="연구책임자의 R&D 수행 역량 및 투입률, 개발 환경의 구비 상태",
            recommended_pages="1~2페이지",
            guiding_questions=[
                "연구책임자(대표 또는 CTO)의 과거 주요 R&D 수행 이력, 특허 출원/등록 건수는 몇 건인가요?",
                "현재 보유하고 있거나 활용 가능한 핵심 연구 장비 및 서버/클라우드 환경은 무엇인가요?",
            ],
            default_master_keys=["team", "rnd_equipment", "company_specs"],
        ),
        SectionRequirement(
            section_id="4-2",
            title="4-2. 연구비 소요 명세 및 예산 비목",
            category_name="4. 연구개발역량 및 인프라",
            description="인건비, 연구시설장비비, 재료비, 연구활동비, 위탁연구개발비 등 비목별 산출 내역을 작성합니다.",
            evaluation_focus="연구비 계상의 적정성, 정부 R&D 연구비 관리 규정 준수 여부",
            recommended_pages="1~2페이지 (비목별 테이블)",
            guiding_questions=[
                "총 연구개발비 중 인건비와 시제품 제작/재료비, 외주용역비의 대략적인 비중은 어떻게 되나요?",
                "대학이나 연구소, 전문기업과의 위탁/공동연구 계획이 포함되어 있나요?",
            ],
            default_master_keys=["budget", "funding_plan"],
        ),
    ],
)


# ==============================================================================
# 레지스트리 및 헬퍼 함수
# ==============================================================================
TEMPLATES_REGISTRY: Dict[str, ProposalTemplate] = {
    TemplateType.PSST.value: PSST_TEMPLATE,
    TemplateType.RND_SMTECH.value: RND_SMTECH_TEMPLATE,
}


def get_template(template_id: str) -> ProposalTemplate:
    """템플릿 ID로 표준 템플릿 반환 (기본값 PSST)."""
    return TEMPLATES_REGISTRY.get(template_id, PSST_TEMPLATE)


def get_all_templates() -> List[Dict[str, Any]]:
    """모든 등록된 템플릿의 요약 목록 반환."""
    return [
        {
            "template_id": t.template_id,
            "name": t.name,
            "target_agency": t.target_agency,
            "target_programs": t.target_programs,
            "description": t.description,
            "section_count": len(t.sections),
        }
        for t in TEMPLATES_REGISTRY.values()
    ]


def detect_template_for_announcement(title: str, ministry: str = "") -> ProposalTemplate:
    """공고명과 소관 부처를 분석하여 가장 적합한 표준 템플릿 자동 판별."""
    lower_title = title.lower()
    lower_min = ministry.lower()

    # 1. R&D 계열 키워드 감지
    rnd_signals = ["r&d", "기술개발", "디딤돌", "팁스", "tips", "연구개발", "중소기업상용화", "산자부", "과기정통부"]
    if any(s in lower_title for s in rnd_signals) or any(s in lower_min for s in ["과학기술", "산업통상"]):
        return RND_SMTECH_TEMPLATE

    # 2. 기본값: 창업진흥원 PSST
    return PSST_TEMPLATE
