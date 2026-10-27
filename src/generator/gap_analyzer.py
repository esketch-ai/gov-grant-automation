"""
마스터 사업계획서 ↔ 공고별 양식 갭(Gap) 분석 엔진
(src/generator/gap_analyzer.py)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from .template_schemas import ProposalTemplate, SectionRequirement, get_template


@dataclass(frozen=True)
class SectionGapAnalysis:
    """섹션별 갭 분석 결과 스키마."""
    section_id: str
    title: str
    category_name: str
    status: str              # "DIRECT_FIT" | "ADAPT_FIT" | "DEFICIENT"
    status_label: str        # "완전 매핑" | "각색 필요" | "팩트 보완 필요"
    status_color: str        # "emerald" | "amber" | "rose"
    matched_master_text: str # 마스터 계획서에서 추출된 원문 텍스트 발췌본
    gap_reason: str          # 진단 사유 및 보완 가이드
    guiding_questions: List[str] # 코파일럿이 사업자에게 물어볼 핵심 질문

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProposalGapAnalyzer:
    """사업자의 마스터 사업계획서 데이터를 공고 템플릿과 대조하여 결손(Gap)을 진단하는 서비스."""

    def analyze(self, item_data: Dict[str, Any], template: Optional[ProposalTemplate] = None) -> Dict[str, Any]:
        """마스터 아이템 데이터와 템플릿 문항 간 갭 분석 수행."""
        tpl = template or get_template("PSST")
        specs = item_data.get("company_specs", {})
        raw_text = item_data.get("proposal_text", "") or ""
        summary = item_data.get("summary", "") or ""
        keywords = item_data.get("keywords", []) or []

        sections_result: List[SectionGapAnalysis] = []
        direct_count = 0
        adapt_count = 0
        deficient_count = 0

        for sec in tpl.sections:
            extracted_snippet, match_score = self._extract_relevant_context(
                sec=sec,
                item_data=item_data,
                specs=specs,
                raw_text=raw_text,
                summary=summary,
                keywords=keywords,
            )

            # 판정 로직:
            # - score >= 70: DIRECT_FIT (충분한 텍스트 및 핵심 키워드 일치)
            # - score >= 35: ADAPT_FIT (기본 내용은 있으나 공고 특화 관점 전환 필요)
            # - score < 35: DEFICIENT (결손 상태, 팩트 입력 필수)
            if match_score >= 70:
                status = "DIRECT_FIT"
                status_label = "완전 매핑"
                status_color = "emerald"
                gap_reason = "기본 계획서에 관련 내용이 충실하게 기술되어 있어 즉시 양식에 맞추어 변환 가능합니다."
                direct_count += 1
            elif match_score >= 35:
                status = "ADAPT_FIT"
                status_label = "각색 필요"
                status_color = "amber"
                gap_reason = f"기본 내용은 있으나 {tpl.name} 평가 관점({sec.evaluation_focus})에 맞춰 톤앤매너 전환 및 보강이 권장됩니다."
                adapt_count += 1
            else:
                status = "DEFICIENT"
                status_label = "팩트 보완 필요"
                status_color = "rose"
                gap_reason = f"기본 계획서에 해당 내용이 부재합니다. 코파일럿 가이드 질문에 답변하여 팩트를 보강해 주세요."
                deficient_count += 1

            sections_result.append(
                SectionGapAnalysis(
                    section_id=sec.section_id,
                    title=sec.title,
                    category_name=sec.category_name,
                    status=status,
                    status_label=status_label,
                    status_color=status_color,
                    matched_master_text=extracted_snippet,
                    gap_reason=gap_reason,
                    guiding_questions=sec.guiding_questions,
                )
            )

        total_sections = len(tpl.sections)
        # 준비도 점수 산출: (direct * 1.0 + adapt * 0.6) / total
        readiness_score = int(round(((direct_count * 1.0 + adapt_count * 0.6) / max(total_sections, 1)) * 100))

        return {
            "template_id": tpl.template_id,
            "template_name": tpl.name,
            "target_programs": tpl.target_programs,
            "total_sections": total_sections,
            "direct_count": direct_count,
            "adapt_count": adapt_count,
            "deficient_count": deficient_count,
            "readiness_score": readiness_score,
            "sections": [s.to_dict() for s in sections_result],
        }

    def _extract_relevant_context(
        self,
        sec: SectionRequirement,
        item_data: Dict[str, Any],
        specs: Dict[str, Any],
        raw_text: str,
        summary: str,
        keywords: List[str],
    ) -> tuple[str, int]:
        """문항 요구사항에 부합하는 마스터 문서 텍스트 발췌 및 일치 점수(0~100) 산정."""
        sec_id = sec.section_id
        kw_str = " ".join(keywords)
        matched_chunks: List[str] = []
        score = 0

        # 1. 문제인식 (1-1, 1-2)
        if sec_id.startswith("1-"):
            if summary:
                matched_chunks.append(f"사업 아이템 개요: {summary}")
                score += 35
            if kw_str:
                matched_chunks.append(f"핵심 키워드: {kw_str}")
                score += 15
            # 원문 텍스트 내 문제/배경 단락 탐색
            if raw_text:
                for line in raw_text.splitlines():
                    if any(w in line for w in ["배경", "필요성", "문제점", "한계", "동기", "고객", "수요", "현황"]):
                        matched_chunks.append(line.strip())
                        score += 15
                        if len(matched_chunks) >= 4:
                            break

        # 2. 솔루션 및 기술/개발내용 (2-1, 2-2)
        elif sec_id.startswith("2-"):
            trl = item_data.get("trl")
            if trl:
                matched_chunks.append(f"현재 기술성숙도(TRL): {trl}단계")
                score += 25
            if summary:
                matched_chunks.append(f"기술/제품 솔루션: {summary}")
                score += 30
            if raw_text:
                for line in raw_text.splitlines():
                    if any(w in line for w in ["기술", "기능", "차별성", "경쟁사", "아키텍처", "개발", "특허", "성능"]):
                        matched_chunks.append(line.strip())
                        score += 15
                        if len(matched_chunks) >= 4:
                            break

        # 3. 성장전략 및 사업화/자금 (3-1, 3-2)
        elif sec_id.startswith("3-"):
            if "매출" in raw_text or "시장" in raw_text or "비즈니스" in raw_text:
                for line in raw_text.splitlines():
                    if any(w in line for w in ["시장", "매출", "마케팅", "수익", "가격", "판로", "해외", "예산", "자금"]):
                        matched_chunks.append(line.strip())
                        score += 20
                        if len(matched_chunks) >= 3:
                            break
            # 기업 정보가 있으면 신뢰도 가산
            if specs.get("company_name"):
                score += 15

        # 4. 팀구성 및 고용/인프라 (4-1, 4-2)
        elif sec_id.startswith("4-"):
            rep_name = specs.get("rep_name")
            opened_date = specs.get("opened_date")
            employees = specs.get("employee_count") or specs.get("employees")

            if rep_name:
                matched_chunks.append(f"대표자: {rep_name} (설립일: {opened_date or '정보없음'})")
                score += 35
            if employees:
                matched_chunks.append(f"현재 임직원 수: {employees}명")
                score += 25
            if raw_text:
                for line in raw_text.splitlines():
                    if any(w in line for w in ["대표", "팀원", "경력", "이력", "고용", "인력", "장비", "연구원"]):
                        matched_chunks.append(line.strip())
                        score += 15
                        if len(matched_chunks) >= 3:
                            break

        snippet = "\n".join(matched_chunks[:3])
        if not snippet:
            snippet = "(기본 계획서 내 일치하는 항목이 없습니다. 코파일럿 질문을 통해 팩트를 입력해 주세요.)"
            score = 10

        return snippet, min(score, 100)
