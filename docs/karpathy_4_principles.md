# Andrej Karpathy's 4 Core Principles for Development
# (안드레이 카파시의 AI 개발 4원칙 지침)

본 프로젝트(`gov-grant-automation` / SSHAI-CWA)의 모든 개발(인간 및 AI 에이전트: QCWA, QQAQC 포함)은 안드레이 카파시의 4원칙을 **절대 헌장**으로 준수한다.

---

## 1. Think Before Coding (코딩 전 깊은 사고)
- **가정 금지 (No Silent Assumptions)**: 요구사항이 모호하거나 누락된 경우, 임의로 기본값(예: 성별 "M"/"F", 특정 주소, 임의의 더미값 등)을 하드코딩하여 넘겨짚지 않는다.
- **명시적 요구사항 정의**: 코드를 작성하기 전 입력(Input), 처리 로직(Processing), 출력 스키마(Output Schema), 실패/예외 처리(Exceptions)를 명확히 정의한다.
- **사전 질문 및 대안 검토**: 불분명한 사항은 작업을 진행하기 전에 명확히 묻고, 복잡한 설계보다 더 단순한 대안이 있는지 선제적으로 검토한다.

## 2. Simplicity First (단순성 최우선)
- **최소주의 구현 (Minimum Necessary Code)**: 오늘 해결해야 할 당면 문제를 푸는 데 필요한 최소한의 코드만 작성한다.
- **과잉 추상화 배제 (No Premature Complexity)**: 요청되지 않은 복잡한 설정 시스템, 1회용 확장 포인트, 불필요한 계층화(Over-engineering)를 엄격히 금지한다.
- **간결함 유지**: 50줄로 해결할 수 있는 일은 절대 200줄로 늘리지 않는다.

## 3. Surgical Changes (외과수술식 정밀 변경)
- **타깃 집중 (Targeted Edits Only)**: 요청받은 버그나 기능에 직접적으로 연결된 코드만 정밀하게 수정한다.
- **무관한 변경 금지 (Zero Drive-by Refactoring)**: 인접한 코드, 무관한 주석, 인용 부호 스타일, 타입 어노테이션 등을 임의로 건드리지 않는다.
- **사이드 이펙트 0화**: 기존 시스템의 스타일과 컨벤션을 철저히 존중하고, 변경 범위 외 기존 기능의 호환성을 100% 보장한다.

## 4. Goal-Driven Execution (목표 주도 실행 & 검증 루프)
- **검증 가능한 기준 설정 (Verifiable Criteria)**: 모든 태스크는 "버그를 재현하거나 새로운 요구사항을 검증하는 실패하는 테스트 작성 -> 이를 통과시키는 최소 코드 작성"의 루프로 실행한다.
- **테스트 주도 확인**: 코드를 수정한 후에는 반드시 자동화 테스트(`pytest`, QA Swarm, GAN Matrix 등)를 실행하여 통과를 직접 확인하고 증거를 남긴다.
- **진본성 검증 (Ground Truth Driven)**: 가상의 성공이 아니라 실제 라이브 데이터 및 런타임 결과물로 결과를 검증한다.
