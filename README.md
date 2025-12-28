# Query-Bong 🚀

**Query-Bong**은 사용자의 자연어 질문을 분석하여, 미리 검증된 SQL 템플릿의 조건(WHERE 절)만 스마트하게 수정해 안전하고 정확한 데이터를 제공하는 **Selective SQL-RAG 엔진**입니다.

## 🏗️ 프로젝트 구조

```text
Query-Bong/
├── engine/             # 핵심 분석 및 생성 엔진
│   ├── sql_analyzer.py # SQL 분석 및 JSON 템플릿 생성기
│   ├── load_json_data.py # 파싱된 JSON을 SQLite DB로 인덱싱
├── mcp_server/         # MCP(Model Context Protocol) 레이어
│   ├── query_mcp_server.py # LLM 도구 인터페이스 제공 (핵심 서버)
│   └── llm_query_rebuilder.py # SQL 조립 및 신규 호출 쿼리 생성 엔진
├── tools/              # 운영 및 생산성 도구
│   ├── catalog_gen.py  # 쿼리 카탈로그(Markdown) 자동 생성 도구
│   └── verification/   # 시스템 정상 작동 검증 스크립트 모음
├── config/             # 환경 설정
│   └── config.json     # DB 경로, 카탈로그 위치 등 중앙 설정
├── data/               # 데이터 저장소
│   ├── db/             # 메타데이터 SQLite DB (sql_queries.db)
│   └── templates/      # 분석된 SQL 템플릿 (JSON)
└── docs/                # 시스템 문서 및 카탈로그
    ├── WORKFLOW.md      # 시스템 전체 흐름도
    └── DATABASE_SCHEMA.md # 상세 DB 스키마 정의서
```

## 🚀 시작하기

### 1. 환경 설치
이 프로젝트는 Python 3.10+ 환경을 권장합니다.

```bash
# 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate

# 필수 패키지 설치
pip install -r requirements.txt
```

### 2. 서버 실행 (MCP Inspector)
LLM이 도구를 어떻게 인식하고 사용하는지 로컬에서 즉시 테스트할 수 있습니다.

```bash
mcp dev mcp_server/query_mcp_server.py
```

### 3. 주요 운영 명령어
*   **새 쿼리 등록**: `python engine/sql_analyzer.py`로 SQL 분석 후 `engine/load_json_data.py`로 DB 반영.
*   **카탈로그 업데이트**: `python tools/catalog_gen.py` 실행 (메타데이터 수정 시 자동 실행됨).
*   **시스템 전체 검증**: `python tools/verification/system_e2e_test.py`.

## 🛡️ 핵심 철학
1.  **Safety First**: 모든 JOIN과 SELECT는 고정되어 있으며, 오직 관리자가 승인한 WHERE 조건만 수정 가능합니다.
2.  **Context Aware**: 단순 검색이 아닌, 비즈니스 엔티티와 태그를 기반으로 최적의 쿼리를 선택합니다.
3.  **Human Readable**: 생성된 모든 쿼리는 즉시 문서화(Catalog)되어 사람이 검토 가능합니다.

## 📄 관련 문서
*   **[워크플로우 가이드](file:///Users/bong/workspace/Query-Bong/docs/WORKFLOW.md)**: 전체 시스템 흐름도
*   **[DB 스키마 상세](file:///Users/bong/workspace/Query-Bong/docs/DATABASE_SCHEMA.md)**: 테이블 및 컬럼 상세 정의서
*   **[워크스루(Walkthrough)](file:///Users/bong/.gemini/antigravity/brain/8389759b-45a9-4d8d-91a5-15cf3b39ba33/walkthrough.md)**: 최근 변경 사항 요약

---
Created by Query-Bong Team.
