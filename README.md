# SSHAI-CWA
# 로컬 정부/R&D·조달 과제 자동 매칭 (Carbon Work Agent)
#
# - README.md ... 에이전트별 역할/협업 프로토콜 (상위 레벨)
# - STATUS.md   ... 실무 개발 현황 보고 및 SSOT (Gemini 총괄 PM 대상)
# - SYNC/       ... 양방향 요청/현황 관리 프로토콜 및 INBOX/REGISTRY
# - DEV_BASE.md ... 5대 파이프라인 설계 청사진
# - TEAM.md     ... 30년차 교수급 전문가 6인 팀 + Task Packet + 품질게이트
#
# 빠른 시작
# ```bash
# ollama serve & ollama pull qwen3:32b
# python3 -m venv .venv && source .venv/bin/activate
# pip install -r requirements.txt   # + python -m playwright install chromium
# cp .env.example .env             # 실제 값으로 수정
# pytest -q
# python -m src.main gov-grant-automation
# ```
#
# 계층 구성 (보일러플레이트 완결 구현)
#   src/common/llm      : 로컬 Ollama(1순위) / Cloud(선택) Structured Output
#   src/collector       : 5 어댑터 + 오픈웹 (타임아웃/미인증/부분실패 폴백)
#   src/deduplicator    : 행정공고번호 정규식 + fuzzy 병합
#   src/parser          : ZIP/HWP/PDF 파싱 + RFP 청크 분할 (메모리 방어)
#   src/matcher         : Pydantic 스키마 + degrade (LLM/JSON 실패 시 안전 기본)
#   src/notifier        : HTML 리포트 + 자동ZIP + SMTP STARTTLS + 보안감사
#   src/main.py         : item별 try/except 격리 오케스트레이터
#
# 테스트는 로컬/오프라인에서 통과됨(실 API·실 SMTP 미의존).
