# 시스템 설계서 (System Design Document)

## 1. 개요 (Overview)
본 문서는 `Design-Doc-Bong` 프로젝트의 목표인 "프로그램 작성을 위한 완벽한 설계서"의 양식을 따릅니다.
각 모듈과 파일별로 **파일명(File)**, **요구사항(Question/Instruction)**, **구현명세(Answer/Response)** 형식으로 기술합니다.

## 2. 모듈별 상세 설계 (Detailed Specification)

### 2.1. SQL 분석 엔진 (SQL Analysis Engine)

#### 파일명 (File): `engine/sql_analyzer.py`
- **지문 (Question)**
    - 인박스(`data/source/inbox`)에 있는 `.sql` 파일을 읽어 `sqlglot`을 이용해 AST 기반으로 분석하시오.
    - 쿼리를 Normalization하고, 구성 요소(SELECT, JOIN, WHERE)를 추출하여 JSON 구조로 변환하시오.
    - 분석 성공 시 원본 파일을 `success/`로 이동, 실패 시 `failed/`로 이동하고 에러 로그를 남기시오.
    - 쿼리의 복잡도에 따라 `UnitA`(단일), `UnitB`(상세), `UnitC`(복합)로 분류하시오.

- **답변 (Answer)**
    - **라이브러리**: `sqlglot` 패키지 사용 (AST 파싱).
    - **클래스 구조**:
        ```python
        class SQLQueryAnalyzer:
            def __init__(self):
                # 경로 설정 (inbox, success, failed, templates)
            
            def analyze_file(self, filename: str) -> bool:
                # 파일 읽기 -> 파싱 -> JSON 생성 -> 파일 이동 (shutil.move)
            
            def _analyze_ast(self, ast, ...) -> Dict:
                # AST 순회 로직:
                # - exp.From, exp.Join -> Tables (Fixed Area)
                # - exp.Where -> Conditions (Change Area)
                # - exp.Select -> Columns (Flexible Area)
        ```
    - **예외 처리**: `traceback` 모듈을 사용하여 상세 에러 로그 기록.
    - **유닛 분류 로직 (Unit Logic)**:
        - **Driven Table 수**를 기준으로 분류 (LEFT/OUTER JOIN 제외, **INNER JOIN**만 카운트).
        - 유효 엔티티 수 = 1 (Main) + N (Inner Joins).
        - `UnitA` (단순): 유효 엔티티 1개.
        - `UnitB` (상세): 유효 엔티티 2개.
        - `UnitC` (복합): 유효 엔티티 3개 이상.

#### 파일명 (File): `engine/load_json_data.py`
- **지문 (Question)**
    - 생성된 JSON 템플릿 파일을 읽어 SQLite 데이터베이스(`sql_queries.db`)에 적재하시오.
    - 스키마는 `TB_QUERY_ASSET`(Master)과 `TB_QUERY_HISTORY`(Archive)로 구성하시오.
    - 데이터 적재 시, 이미 존재하는 `query_id`라면 기존 데이터를 `HISTORY` 테이블로 이동시키고(Archiving), 새로운 데이터를 `ASSET` 테이블에 저장하는 **"Move-then-Insert"** 전략을 구현하시오.

- **답변 (Answer)**
    - **테이블 스키마**: (아래 3.데이터베이스 스키마 섹션 참조)
    - **적재 로직**:
        1. DB 연결 (없으면 테이블 생성 with `IF NOT EXISTS`).
        2. JSON 파일 로드.
        3. `SELECT count(*) FROM TB_QUERY_ASSET WHERE query_id = ?` 확인.
        4. 존재하면 `INSERT INTO TB_QUERY_HISTORY SELECT ... FROM TB_QUERY_ASSET`.
        5. `DELETE FROM TB_QUERY_ASSET`.
        6. `INSERT INTO TB_QUERY_ASSET ...` (신규 데이터).

---

### 2.2. MCP 서버 및 서비스 (MCP Server & Service)

#### 파일명 (File): `mcp_server/query_mcp_server.py`
- **지문 (Question)**
    - LLM이 SQL 쿼리 자산을 활용할 수 있도록 MCP(Model Context Protocol) 서버를 구축하시오.
    - `FastMCP`를 사용하여 다음 도구(Tool)들을 제공하시오:
        1. `search_queries`: 자연어로 쿼리 템플릿 검색.
        2.  `get_query_details`: 특정 쿼리의 고정/변경 영역 상세 조회.
        3. `modify_where_conditions`: WHERE 조건 수정 및 새로운 SQL 생성 요청.
    - 사용자가 쿼리를 수정할 경우, 원본(`TB_QUERY_ASSET`)을 건드리지 않고 별도의 `generated_queries` 테이블(Generated DB)에 저장하시오.

- **답변 (Answer)**
    - **서버 초기화**: `mcp = FastMCP("SQL-Query-RAG-Server")`.
    - **DB 연결**: Master DB와 Generated DB(`query_rebuilder.db`) 분리 운영.
    - **Tool 구현**:
        - `modify_where_conditions`: `SQLRebuilder` 클래스를 호출하여 SQL 재조립 후 `generated_queries`에 INSERT.

#### 파일명 (File): `mcp_server/llm_query_rebuilder.py`
- **지문 (Question)**
    - 분해된 SQL 구성 요소(SELECT columns, JOINs, WHERE conditions)를 입력받아 실행 가능한 완전한 SQL 문자열로 재조립하는 엔진을 구현하시오.
    - 입력받은 WHERE 조건 리스트를 SQL의 `WHERE` 절로 정확히 변환하시오.

- **답변 (Answer)**
    - **메서드 서명**:
        ```python
        class SQLRebuilder:
            @staticmethod
            def rebuild(select_columns, from_table, joins, where_conditions, ...) -> str:
        ```
    - **로직**:
        - 리스트형태의 데이터를 루프 돌며 `SELECT ...`, `FROM ...`, `JOIN ... ON ...`, `WHERE ... AND ...` 문자열 조합.

---

## 3. 데이터베이스 스키마 (Database Schema Definitions)

- **지문 (Question)**
    - 시스템에서 사용하는 SQLite 테이블 생성 쿼리(DDL)를 모두 나열하시오.

- **답변 (Answer)**

```sql
-- 1. 쿼리 자산 (Master Asset)
CREATE TABLE IF NOT EXISTS TB_QUERY_ASSET (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id TEXT UNIQUE NOT NULL,
    question TEXT NOT NULL,
    description TEXT,
    unit_type TEXT, -- UnitA, UnitB, UnitC
    unit_description TEXT,
    entities TEXT, -- JSON Array
    from_table TEXT,
    original_sql TEXT,
    normalized_sql TEXT,
    created_at TEXT,
    modified_at TEXT,
    modification_count INTEGER DEFAULT 0
    -- (기타 Presentation 필드 생략)
);

-- 2. 쿼리 이력 (History)
CREATE TABLE IF NOT EXISTS TB_QUERY_HISTORY (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER,
    query_id TEXT,
    question TEXT,
    original_sql TEXT,
    archived_at TEXT,
    reason TEXT
);

-- 3. 생성된 쿼리 (Generated - for LLM Service)
CREATE TABLE IF NOT EXISTS generated_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id TEXT UNIQUE NOT NULL,
    parent_query_id TEXT NOT NULL, -- 원본 Query ID
    question TEXT,
    description TEXT,
    normalized_sql TEXT,
    created_at TEXT
);
```

## 4. 데이터 명세 (Data Structure Specifications)

## 5. 메타-프로그램 명세 (The Meta-Designer Specification)

#### 주제 (Topic): `Self-Generating Documentation System` (Meta-Doc-Bong)
- **지문 (Question)**
    - 소스 코드를 읽어 이 설계서(`Design_Document.md`)를 자동으로 생성하거나 역으로 검증하는 프로그램(`meta_generator.py`)을 설계하시오.
    - 입력(Input)은 프로젝트 루트 경로이며, 출력(Output)은 `docs/Design_Document.md` 파일이다.
    - 소스 코드와 설계서가 항상 일치함(Sync)을 보장하는 알고리즘을 정의하시오.

- **답변 (Answer)**
    - **프로그램 개요**: 소스 코드의 주석(Docstring)과 구조(AST)를 파싱하여 설계서의 "답변(Answer)" 섹션을 자동 업데이트하는 도구.
    - **핵심 알고리즘 (Sync Loop)**:
        1. **Code to Doc (Generate)**: 
            - 파이썬 파일(`*.py`)을 AST로 파싱.
            - 클래스/함수 시그니처와 Docstring을 추출.
            - 설계서의 해당 `파일명` 섹션을 찾아 `답변` 영역을 최신 코드로 덮어쓰기.
        2. **Doc to Code (Verify)**:
            - 설계서의 `답변`에 기술된 로직(예: Unit 분류 기준)과 실제 코드를 비교.
            - 불일치 시 경고(Warning) 리포트 생성 (코드를 직접 수정하지는 않음 - 안전장치).
    - **입출력 정의**:
        - **Input**: `/engine/*.py`, `/mcp_server/*.py`, `/data/db/*.db` (Schema)
        - **Output**: `docs/Design_Document.md` (Markdown 포맷 유지)
    - **사용 기술**: `Astroid` (파이썬 정적 분석), `CheckSum` (변경 감지)
