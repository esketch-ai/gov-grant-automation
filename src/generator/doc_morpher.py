"""
공고 심사 요건 분석 및 필수 대응 가이드 도출 엔진
(src/generator/doc_morpher.py)
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import httpx

from src.common.logging_config import get_logger
from .template_schemas import ProposalTemplate, SectionRequirement, get_template

logger = get_logger("doc_morpher")


class DocMorpher:
    """마스터 계획서 원문과 사용자 입력 팩트를 결합하여 공고 심사 요건 분석 및 필수 대응 가이드를 도출하는 어시스턴트 엔진."""

    def __init__(
        self,
        ollama_base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: float = 8.0,
    ) -> None:
        self.ollama_base_url = ollama_base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", "qwen3.8:27b")
        self.timeout = timeout_seconds

    async def generate_section_draft(
        self,
        section: SectionRequirement,
        template: ProposalTemplate,
        master_context: str,
        user_facts: Dict[str, str],
        item_meta: Dict[str, Any],
    ) -> str:
        """비동기 섹션 대응 가이드 생성: LLM 호출 시도 ➔ 실패 시 고품질 규칙 기반 합성기 폴백."""
        # 1차: LLM 생성 시도
        llm_draft = await self._try_llm_generation(section, template, master_context, user_facts, item_meta)
        if llm_draft and len(llm_draft.strip()) >= 100:
            return llm_draft.strip()

        # 2차: 규칙 기반 합성기 (오프라인 및 즉시 응답 100% 안전 보장)
        return self.synthesize_rule_based_draft(section, template, master_context, user_facts, item_meta)

    def generate_section_draft_sync(
        self,
        section: SectionRequirement,
        template: ProposalTemplate,
        master_context: str,
        user_facts: Dict[str, str],
        item_meta: Dict[str, Any],
    ) -> str:
        """동기 호출용 메서드."""
        return self.synthesize_rule_based_draft(section, template, master_context, user_facts, item_meta)

    async def _try_llm_generation(
        self,
        section: SectionRequirement,
        template: ProposalTemplate,
        master_context: str,
        user_facts: Dict[str, str],
        item_meta: Dict[str, Any],
    ) -> Optional[str]:
        """로컬 Ollama LLM을 통한 맞춤형 섹션 요건 대응 가이드 도출."""
        facts_formatted = "\n".join([f"- [사용자 보완 팩트] {k}: {v}" for k, v in user_facts.items() if v.strip()])
        item_name = item_meta.get("name", "과제 아이템")
        summary = item_meta.get("summary", "")

        system_prompt = f"""당신은 2026 대한민국 정부지원사업 공고 요건 정밀 분석 및 심사위원 대응 전략 수립 수석 컨설턴트입니다.
적용 템플릿: {template.name} ({template.target_agency})
톤앤매너 지침: {template.tone_directive}

분석 섹션: {section.title} ({section.category_name})
공고 요건 가이드: {section.description}
심사위원 평가 중점 사항: {section.evaluation_focus}

위 공고 요건에 부합하도록 창업자가 심사위원의 평가 기준을 완벽히 충족할 수 있는 '핵심 대응 전략 가이드 및 작성 착안점 메모'를 체계적으로 도출하세요.
- 본 서비스는 대필을 제공하지 않으며, 창업자가 본인 사업의 강점을 드러낼 수 있는 전략적 작성 지침을 제공합니다.
- 불필요한 서두("안녕하세요", "네 알겠습니다")나 메타 설명은 완전히 생략하고, 개조식 체크포인트와 대응 가이드만 출력하세요.
- 번호가 매겨진 소제목(1), 2), ①, ②) 및 필수 증빙 지표를 명확히 제시하세요."""

        user_prompt = f"""[기본 정보]
- 과제/아이템명: {item_name}
- 핵심 요약: {summary}

[기업 사업소개 발췌 내용]
{master_context}

[사업자가 입력한 추가 팩트/답변]
{facts_formatted or "(추가 입력 없음 - 기본 정보 기반 분석)"}

위 정보를 바탕으로 '{section.title}' 항목의 심사위원 채점 기준별 핵심 대응 전략 가이드 및 필수 착안점 메모를 3~4개 항목으로 명확히 도출해 주세요."""

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.4, "top_p": 0.9},
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.ollama_base_url}/api/chat", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("message", {}).get("content", "")
        except Exception as e:
            logger.info("Ollama 연동 건너뜀 또는 타임아웃 (%s) -> 규칙 합성기 활용", e)
        return None

    def synthesize_rule_based_draft(
        self,
        section: SectionRequirement,
        template: ProposalTemplate,
        master_context: str,
        user_facts: Dict[str, str],
        item_meta: Dict[str, Any],
    ) -> str:
        """LLM 부재 시에도 심사위원 기준에 부합하는 공고 요건별 전략 메모 및 대응 가이드 합성."""
        item_name = item_meta.get("name", "본 사업 아이템")
        summary = item_meta.get("summary", "혁신 기술 기반 솔루션")
        sec_id = section.section_id

        # 사용자 입력 팩트 모음
        facts_list = [f"{v.strip()}" for v in user_facts.values() if v and v.strip()]
        combined_facts = " ".join(facts_list) if facts_list else ""

        lines: List[str] = []

        # ----------------------------------------------------------------------
        # 1. 문제인식 (PSST 1-1, 1-2 / R&D 1-1, 1-2)
        # ----------------------------------------------------------------------
        if sec_id == "1-1":
            lines.append(f"가. 개발 배경 및 추진 필요성")
            lines.append(f"  ○ 현 시장의 핵심 문제점 및 한계")
            lines.append(f"    - 현재 관련 산업 분야에서는 기존 시스템의 비효율성과 높은 운영 비용으로 인해 고객 및 기업의 페인포인트가 심화되고 있음.")
            if combined_facts:
                lines.append(f"    - 특히 실무 현장에서는 \"{combined_facts}\"와 같은 구체적 제약 사항이 빈번히 발생하여 근본적인 개선 솔루션이 절실한 실정임.")
            lines.append(f"  ○ 「{item_name}」의 개발 당위성")
            lines.append(f"    - 당사는 이러한 시장의 미충족 수요(Unmet Needs)를 해결하고자, {summary}을(를) 핵심 가치로 하는 혁신 과제를 기획함.")
            lines.append(f"    - 이를 통해 기존 레거시 방식 대비 공정 효율을 획기적으로 개선하고 시장의 구조적 진입장벽을 극복하고자 함.")

        elif sec_id == "1-2":
            lines.append(f"가. 목표 시장 분석 및 고객 검증(Customer Validation)")
            lines.append(f"  ○ 타깃 시장 규모 및 특성")
            lines.append(f"    - 1차 목표 시장은 디지털 전환(DX) 및 고도화 수요가 집중된 기업/소비자군을 중심으로 설정하였으며, 연평균 성장률(CAGR)이 높은 잠재 시장임.")
            if combined_facts:
                lines.append(f"  ○ 현장 고객 인터뷰 및 지불의사(Willingness to Pay) 확인")
                lines.append(f"    - 목표 고객층을 대상으로 사전 조사를 실시한 결과: {combined_facts}")
            else:
                lines.append(f"  ○ 고객 페르소나 및 요구사항 검증")
                lines.append(f"    - 사전 설문 및 이해관계자 인터뷰를 통해 본 솔루션 도입 시 업무 시간 단축 및 비용 절감에 대한 긍정적 지불 의사를 확인하였음.")

        # ----------------------------------------------------------------------
        # 2. 실현가능성 / 기술개발목표 (PSST 2-1, 2-2 / R&D 2-1, 2-2)
        # ----------------------------------------------------------------------
        elif sec_id == "2-1":
            trl = item_meta.get("trl", 3)
            lines.append(f"가. 창업아이템의 구현 방안 및 기술적 구체화 현황")
            lines.append(f"  ○ 현재 개발 단계(TRL {trl}단계 진입) 및 추진 진척도")
            lines.append(f"    - 현재 핵심 아키텍처 설계 및 개념 검증(PoC)을 성공적으로 완료하였으며, 본 지원사업을 통해 상용 수준의 시제품(MVP)을 완성하고자 함.")
            if combined_facts:
                lines.append(f"  ○ 세부 개발 스펙 및 구현 계획")
                lines.append(f"    - 주요 구현 내용: {combined_facts}")
            lines.append(f"  ○ 핵심 기술 및 정량적 성능 지표 관리 방안")
            lines.append(f"    - 시스템의 안정성, 처리 속도, 정확도를 최우선 지표로 설정하고 공인시험인증 및 단계별 통합 테스트를 엄격히 적용함.")

        elif sec_id == "2-2":
            lines.append(f"가. 경쟁사 비교 분석 및 독창적 경쟁우위(Moat)")
            lines.append(f"  ○ 국내외 주요 경쟁사 대비 차별성")
            lines.append(f"    - [기존 경쟁 제품]: 높은 도입 단가와 복잡한 유지보수, 폐쇄적 환경으로 범용적 확장에 한계 존재.")
            lines.append(f"    - [당사 솔루션({item_name})]: 경량화 모듈 설계, 직관적 UI/UX, 뛰어난 비용 효율성 및 상호운용성 제공.")
            if combined_facts:
                lines.append(f"  ○ 핵심 기술 진입장벽 및 모방 방지 전략")
                lines.append(f"    - {combined_facts}")
            else:
                lines.append(f"  ○ 지식재산권(IP) 보호 및 데이터 장벽")
                lines.append(f"    - 핵심 알고리즘에 대한 국내외 특허 출원과 독점적 데이터셋 구축을 통해 후발주자의 카피캣 시도를 원천 차단함.")

        # ----------------------------------------------------------------------
        # 3. 성장전략 / 사업화 (PSST 3-1, 3-2 / R&D 3-1, 3-2)
        # ----------------------------------------------------------------------
        elif sec_id == "3-1":
            lines.append(f"가. 사업화 자금 소요 및 자금 조달 계획")
            lines.append(f"  ○ 정부지원금 집행 계획 (합리적 비목 배분)")
            lines.append(f"    - 시제품 고도화 및 외주 시험제작비(40%), 핵심 연구개발 전담 인건비(35%), 고객 유치 마케팅 및 지재권 출원비(25%)로 균형 있게 편성함.")
            if combined_facts:
                lines.append(f"  ○ 세부 소요 예산 및 추가 자금 조달 방안")
                lines.append(f"    - {combined_facts}")
            else:
                lines.append(f"  ○ 자부담금 조달 및 후속 투자 유치 로드맵")
                lines.append(f"    - 기업 내부 유보금 및 지자체 연계 펀드, 시드/프리A 단계 VC 투자 유치를 병행하여 개발 중단 리스크를 원천 제거함.")

        elif sec_id == "3-2":
            lines.append(f"가. 시장 진입(GTM) 및 단계별 판로 개척 전략")
            lines.append(f"  ○ 수익 모델(Business Model)")
            lines.append(f"    - B2B 구독 모델(SaaS) 및 기업 맞춤형 라이선스 판매를 결합한 하이브리드 수익 구조 확립.")
            if combined_facts:
                lines.append(f"  ○ 초기 마케팅 및 판로 개척 방안")
                lines.append(f"    - {combined_facts}")
            else:
                lines.append(f"  ○ 단계별 스케일업 로드맵")
                lines.append(f"    - [1단계: 런칭]: 거점 기관 및 파트너사 대상 레퍼런스 확보.")
                lines.append(f"    - [2단계: 성장]: 온라인 다이렉트 세일즈 및 유통망 입점 확대를 통한 매출 규모화 달성.")

        # ----------------------------------------------------------------------
        # 4. 팀구성 / 인프라 (PSST 4-1, 4-2 / R&D 4-1, 4-2)
        # ----------------------------------------------------------------------
        elif sec_id == "4-1":
            specs = item_meta.get("company_specs", {})
            rep_name = specs.get("rep_name", "대표자")
            lines.append(f"가. 대표자 및 핵심 인력의 보유 역량")
            lines.append(f"  ○ 대표자({rep_name})의 전문성 및 사업 수행 의지")
            lines.append(f"    - 동종 도메인 실무 전문성과 네트워크를 보유하고 있으며, 본 과제의 기획부터 사업화 전 과정을 총괄 지휘할 수 있는 실행력을 검증받음.")
            if combined_facts:
                lines.append(f"  ○ 주요 팀원 역량 및 업무 분장")
                lines.append(f"    - {combined_facts}")
            else:
                lines.append(f"  ○ 전담 개발 및 비즈니스 인력 체계")
                lines.append(f"    - 핵심 S/W 아키텍트, 도메인 전문가, 사업화 마케터가 유기적으로 협업하는 원팀(One-team) 구조를 완비함.")

        elif sec_id == "4-2":
            lines.append(f"가. 신규 고용 및 사회적 가치 실천 계획")
            lines.append(f"  ○ 협약 기간 내 신규 일자리 창출 계획")
            if combined_facts:
                lines.append(f"    - 구체적 채용 계획: {combined_facts}")
            else:
                lines.append(f"    - 과제 수행에 따른 사업화 본격화에 발맞추어, 청년 인재 및 전문 연구원 채용을 단계별로 추진하여 지역 일자리 창출에 기여함.")
            lines.append(f"  ○ 근로환경 개선 및 성과 공유")
            lines.append(f"    - 유연근무제 운영, 청년 내일채움공제 연계, 직무발명보상제 도입 등 지속 가능한 고용 안정을 적극 실천함.")

        # 기타 범용 문항
        else:
            lines.append(f"가. {section.title} 추진 내용")
            lines.append(f"  ○ {section.description}")
            if combined_facts:
                lines.append(f"  ○ 주요 사실 및 추진 방안: {combined_facts}")
            if master_context:
                lines.append(f"  ○ 마스터 계획서 연계: {master_context}")

        return "\n".join(lines)

    def assemble_full_document(
        self,
        item_meta: Dict[str, Any],
        template: ProposalTemplate,
        section_drafts: Dict[str, str],
    ) -> str:
        """전체 완성된 섹션별 공고 대응 가이드 및 전략 노트를 취합하여 공식 마크다운 문서로 조립."""
        item_name = item_meta.get("name", "과제 아이템")
        specs = item_meta.get("company_specs", {})
        company_name = specs.get("company_name", "(주)자사명")
        rep_name = specs.get("rep_name", "대표자")

        doc_lines: List[str] = [
            f"# {template.name}",
            f"> **지원과제**: {template.target_programs} | **전담기관**: {template.target_agency}",
            f"> **신청기업**: {company_name} | **대표자**: {rep_name} | **과제명**: {item_name}",
            f"",
            f"---",
            f"",
            f"## [목차 및 요약]",
        ]

        for sec in template.sections:
            doc_lines.append(f"- **{sec.title}** ({sec.category_name})")

        doc_lines.append("")
        doc_lines.append("---")
        doc_lines.append("")

        current_category = ""
        for sec in template.sections:
            if sec.category_name != current_category:
                current_category = sec.category_name
                doc_lines.append(f"## {current_category}")
                doc_lines.append("")

            draft = section_drafts.get(sec.section_id, "").strip()
            if not draft:
                draft = "(분석 대기 중 - [심사 기준별 대응 가이드 도출]을 실행해 주세요.)"

            doc_lines.append(f"### {sec.title}")
            doc_lines.append(f"*{sec.description}*")
            doc_lines.append("")
            doc_lines.append(draft)
            doc_lines.append("")

        return "\n".join(doc_lines)
