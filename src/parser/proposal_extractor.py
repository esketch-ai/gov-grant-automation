"""사업계획서 정형 스펙 추출기 (LLM + Rule-based Fallback)
(src/parser/proposal_extractor.py)
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

import httpx

from src.common.logging_config import get_logger

logger = get_logger("proposal_extractor")


class ProposalExtractor:
    """사업계획서 텍스트로부터 아이템 메타데이터 및 company_specs를 정형 추출하는 엔진."""

    def __init__(
        self,
        ollama_base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: float = 8.0,
    ) -> None:
        self.ollama_base_url = ollama_base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", "qwen3.8:27b")
        self.timeout = timeout_seconds

    async def extract(self, text: str) -> Dict[str, Any]:
        """비동기 추출: LLM 우선 시도 후 실패 시 Rule-based 폴백."""
        if not text or not text.strip():
            return self._build_empty_result()

        # 1차: LLM 호출 시도
        llm_result = await self._try_llm_extraction(text)
        if llm_result:
            # LLM 결과에 빈 필드가 있으면 룰 기반으로 보강
            rule_fallback = self.extract_by_rules(text)
            return self._merge_results(llm_result, rule_fallback, text)

        # 2차: 룰 기반 정규식 추출기 (100% 안전 보장)
        return self.extract_by_rules(text)

    def extract_sync(self, text: str) -> Dict[str, Any]:
        """동기 추출 (테스트 및 일반 동기 코드용)."""
        if not text or not text.strip():
            return self._build_empty_result()
        # 동기 모드에서는 빠른 규칙 기반을 우선 사용하거나 즉시 반환
        return self.extract_by_rules(text)

    async def _try_llm_extraction(self, text: str) -> Optional[Dict[str, Any]]:
        """로컬 Ollama LLM을 호출하여 JSON 스키마 추출 시도."""
        # 긴 문서는 핵심 개요가 포함된 앞단 8000자 사용
        truncated = text[:8000].strip()

        prompt = f"""당신은 대한민국 정부지원사업 사업계획서 전문 분석가입니다.
제공된 사업계획서 텍스트를 정밀 분석하여 아래 JSON 규격에 맞게 정보를 추출하세요.
반드시 순수 JSON 형식으로만 응답하고, 마크다운 코드블록(```json)이나 다른 설명은 일절 포함하지 마세요.

추출 JSON 스키마:
{{
  "item": {{
    "id": "영문 소문자 및 하이픈 슬러그 (예: ai-speech-agent)",
    "name": "아이템 또는 사업과제 정식 명칭",
    "summary": "1~2문장의 핵심 사업화 및 기술 요약",
    "trl": 4, // 기술성숙도 1~9 사이 정수
    "keywords": ["핵심키워드1", "핵심키워드2", "핵심키워드3", "핵심키워드4", "핵심키워드5"],
    "target_stage": "초기창업" // "예비창업", "초기창업", "도약기업", "전분야" 중 선택
  }},
  "company_specs": {{
    "company_name": "회사명 (예: (주)테크솔루션)",
    "biz_reg_no": "사업자등록번호 (000-00-00000 포맷)",
    "opened_date": "설립일 (YYYY-MM-DD)",
    "founder_birth": "대표자 생년월일 (YYYY-MM-DD)",
    "founder_gender": "F 또는 M",
    "address": "사업장 주소",
    "debt_ratio_pct": 100.0, // 부채비율 퍼센트 (숫자)
    "has_rnd_lab": true, // 연구소 또는 전담부서 보유 여부
    "is_capital_impaired": false, // 자본잠식 여부
    "has_tax_arrears": false, // 국세/지방세 체납 여부
    "current_pi_projects": 0, // 현재 수행중인 정부과제 연구책임자 수
    "registered_patents_count": 0, // 등록 특허 건수
    "prior_grant_history": [], // 과거 수혜 이력 (예: ["2023년 초기창업패키지"])
    "certifications": [] // 인증 (예: ["벤처기업", "여성기업"])
  }}
}}

[사업계획서 텍스트]:
{truncated}
"""
        url = f"{self.ollama_base_url.rstrip('/')}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1},
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    raw_content = resp.json().get("response", "")
                    cleaned = self._clean_json_str(raw_content)
                    parsed = json.loads(cleaned)
                    if isinstance(parsed, dict) and "item" in parsed:
                        return parsed
        except Exception as e:
            logger.info("Ollama LLM 추출 미사용 (룰 기반 폴백 전환): %s", e)
        return None

    def extract_by_rules(self, text: str) -> Dict[str, Any]:
        """한국어 정부과제 양식 특화 정규식 기반 정형 데이터 추출기."""
        # 1. 회사명
        company_name = ""
        m_corp = re.search(r"(\([주유]\)\s*[가-힣A-Za-z0-9]+|[가-힣A-Za-z0-9]+\s*\([주유]\)|주식회사\s+[가-힣A-Za-z0-9]+)", text)
        if m_corp:
            company_name = m_corp.group(1).strip()
        else:
            m_comp = re.search(r"(?:기업명|회사명|상호명|업체명)\s*[:：]\s*([가-힣A-Za-z0-9\(\)]+)", text)
            if m_comp:
                company_name = m_comp.group(1).strip()

        # 2. 사업자등록번호 (000-00-00000)
        biz_reg_no = ""
        m_biz = re.search(r"\b(\d{3}-\d{2}-\d{5})\b", text)
        if m_biz:
            biz_reg_no = m_biz.group(1)

        # 3. 개업연월일 / 설립일
        opened_date = ""
        m_date = re.search(r"(?:설립일|개업일|설립연월일|창업일)\s*[:：]?\s*(\d{4})[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})", text)
        if m_date:
            opened_date = f"{int(m_date.group(1)):04d}-{int(m_date.group(2)):02d}-{int(m_date.group(3)):02d}"

        # 4. 대표자 생년월일 및 성별 (미명시 시 임의 하드코딩 금지)
        founder_birth = ""
        founder_gender = ""
        m_birth = re.search(r"(?:생년월일|생년|출생)\s*[:：]?\s*(\d{4})[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})", text)
        if m_birth:
            founder_birth = f"{int(m_birth.group(1)):04d}-{int(m_birth.group(2)):02d}-{int(m_birth.group(3)):02d}"

        if any(k in text for k in ("여성기업", "여성대표", "대표자(여)", "성별 : 여", "성별: 여", "여성창업")):
            founder_gender = "F"
        elif any(k in text for k in ("대표자(남)", "성별 : 남", "성별: 남", "성별:남")):
            founder_gender = "M"

        # 5. 주소
        address = ""
        m_addr = re.search(r"(?:소재지|본사\s*주소|사업장\s*주소|주소)\s*[:：]?\s*([가-힣0-9\s\-]+(?:시|도|구|군|로|길)\s+[0-9\-번지]+)", text)
        if m_addr:
            address = m_addr.group(1).strip()
        else:
            # 시도 키워드 기반 탐색
            m_addr2 = re.search(r"((?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)[가-힣0-9\s\-]{5,35}(?:로|길|동|리|층|호))", text)
            if m_addr2:
                address = m_addr2.group(1).strip()

        # 6. 연구소 유무
        has_rnd_lab = any(k in text for k in ("기업부설연구소", "연구개발전담부서", "부설연구소", "R&D연구소"))

        # 7. 부채비율
        debt_ratio_pct = None
        m_debt = re.search(r"(?:부채비율|부채율)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*%", text)
        if m_debt:
            try:
                debt_ratio_pct = float(m_debt.group(1))
            except ValueError:
                pass

        # 8. 특허 수
        patents_count = 0
        m_pat = re.findall(r"(?:등록특허|특허등록|특허)\s*[:：]?\s*(\d+)\s*건", text)
        if m_pat:
            try:
                patents_count = sum(int(x) for x in m_pat)
            except ValueError:
                pass
        elif "특허" in text:
            patents_count = min(len(re.findall(r"10-\d{4}-\d{7}", text)) or 1, 10)

        # 9. 인증
        certs = []
        for c in ("벤처기업", "이노비즈", "메인비즈", "여성기업", "사회적기업", "소셜벤처", "연구소기업"):
            if c in text and c not in certs:
                certs.append(c)

        # 법적 배제 원칙: 대표자가 남성(M)이면 "여성기업" 인증 절대 포함 금지
        if founder_gender == "M" and "여성기업" in certs:
            certs.remove("여성기업")

        # 10. 기수혜 이력
        grants = []
        for g in ("예비창업패키지", "초기창업패키지", "창업도약패키지", "청년창업사관학교", "디딤돌", "팁스", "TIPS"):
            if g in text and g not in grants:
                grants.append(g)

        # 11. 아이템 명칭 및 요약
        item_name = ""
        m_item = re.search(r"(?:과제명|사업명|아이템명|제품명|개발과제)\s*[:：]\s*([가-힣A-Za-z0-9\s\-–—\(\)]+)", text)
        if m_item:
            item_name = m_item.group(1).strip().split("\n")[0]
        else:
            # 본문 첫 번째 유효 제목 줄
            lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) >= 5]
            if lines:
                item_name = lines[0][:40]

        # 12. TRL
        trl = 4
        m_trl = re.search(r"(?:TRL|기술성숙도)\s*[:：]?\s*(\d)\s*단계?", text, re.IGNORECASE)
        if m_trl:
            try:
                trl = max(1, min(9, int(m_trl.group(1))))
            except ValueError:
                pass

        # 13. 키워드
        keywords = self._extract_keywords(text)

        # 14. 영문 슬러그 생성
        item_id = self._generate_slug(item_name or company_name)

        summary = ""
        m_sum = re.search(r"(?:개발\s*개요|사업\s*개요|핵심\s*내용|요약)\s*[:：]?\s*([^\n]+(?:\n[^\n]+)?)", text)
        if m_sum:
            summary = m_sum.group(1).strip().replace("\n", " ")[:200]
        if not summary and len(text) > 30:
            summary = text[:150].replace("\n", " ").strip()

        return {
            "item": {
                "id": item_id,
                "name": item_name or "신규 개발 과제",
                "summary": summary or f"{company_name}의 신규 사업화 아이템",
                "trl": trl,
                "keywords": keywords,
                "target_stage": "초기창업" if (opened_date and "2023" in opened_date or "2024" in opened_date or "2025" in opened_date) else "전분야",
            },
            "company_specs": {
                "company_name": company_name,
                "biz_reg_no": biz_reg_no,
                "opened_date": opened_date,
                "founder_birth": founder_birth,
                "founder_gender": founder_gender,
                "address": address,
                "debt_ratio_pct": debt_ratio_pct,
                "has_rnd_lab": has_rnd_lab,
                "is_capital_impaired": False,
                "has_tax_arrears": False,
                "current_pi_projects": 0,
                "registered_patents_count": patents_count,
                "prior_grant_history": grants,
                "certifications": certs,
            },
            "extracted_proposal_md": self._format_as_markdown(item_name, summary, text),
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """텍스트에서 산업/기술 핵심 키워드 추출."""
        CANDIDATES = [
            "인공지능", "AI", "머신러닝", "딥러닝", "LLM", "온디바이스 AI",
            "빅데이터", "클라우드", "SaaS", "플랫폼", "보안", "블록체인",
            "바이오", "의료기기", "디지털치료제", "헬스케어", "임상",
            "탄소중립", "친환경", "신재생에너지", "순환경제", "배터리",
            "스마트팜", "농식품", "푸드테크", "로컬크리에이터",
            "로봇", "드론", "모빌리티", "자율주행", "센서", "반도체",
        ]
        found = []
        for kw in CANDIDATES:
            if kw in text and kw not in found:
                found.append(kw)
        if len(found) < 3:
            found.extend(["플랫폼", "기술개발", "사업화"])
        return found[:6]

    @staticmethod
    def _generate_slug(name: str) -> str:
        """한글/영문 명칭으로부터 고유한 kebab-case 슬러그 생성."""
        cleaned = re.sub(r"[^\w\s-]", "", name).strip().lower()
        cleaned = re.sub(r"[-\s]+", "-", cleaned)
        if not cleaned:
            return "new-project-item"
        # 영문이 아닌 경우 transliteration 대안으로 간단한 해시/단어 조합
        if not re.search(r"[a-z0-9]", cleaned):
            import hashlib
            short_h = hashlib.md5(name.encode("utf-8")).hexdigest()[:6]
            return f"item-{short_h}"
        return cleaned[:25].strip("-")

    @staticmethod
    def _clean_json_str(s: str) -> str:
        """마크다운 백틱 및 군더더기 제거."""
        s = re.sub(r"^```json\s*", "", s, flags=re.MULTILINE)
        s = re.sub(r"^```\s*", "", s, flags=re.MULTILINE)
        s = s.strip()
        # 최초 '{' 와 마지막 '}' 추출
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1:
            return s[start : end + 1]
        return s

    def _merge_results(self, llm: Dict[str, Any], rule: Dict[str, Any], original_text: str) -> Dict[str, Any]:
        """LLM 결과에 빈 필드가 있으면 룰 기반으로 메꿔주는 안전 합성."""
        res = dict(llm)
        if "item" not in res:
            res["item"] = rule["item"]
        if "company_specs" not in res:
            res["company_specs"] = rule["company_specs"]

        # 주요 필드 폴백
        for k, v in rule["company_specs"].items():
            if not res["company_specs"].get(k) and v:
                res["company_specs"][k] = v

        for k, v in rule["item"].items():
            if not res["item"].get(k) and v:
                res["item"][k] = v

        if not res.get("extracted_proposal_md"):
            res["extracted_proposal_md"] = rule["extracted_proposal_md"]

        return res

    @staticmethod
    def _format_as_markdown(title: str, summary: str, text: str) -> str:
        """사업계획서 원문을 깔끔한 마크다운 문서로 포맷팅."""
        header = f"# {title or '사업계획서 요약'}\n\n**개요**: {summary}\n\n---\n\n## 사업계획서 본문 발췌\n\n"
        body = text[:5000].strip()
        return header + body

    @staticmethod
    def _build_empty_result() -> Dict[str, Any]:
        return {
            "item": {"id": "new-item", "name": "", "summary": "", "trl": 3, "keywords": [], "target_stage": "전분야"},
            "company_specs": {},
            "extracted_proposal_md": "",
        }
