# 🗄️ Database Schema & JSON Structure Documentation

본 문서는 **Query-Bong** 시스템의 핵심 데이터 구조인 **JSON 템플릿(Logic)** 과 이를 저장하는 **SQLite 데이터베이스(Physical)** 간의 매핑 상세를 기술합니다.

---

## 1. JSON Data Structure (Logical)

SQL 분석 엔진(`sql_analyzer.py`)이 `.sql` 파일을 파싱하여 생성하는 표준 JSON 포맷입니다.

### 1.1 Root Fields
| Field | Type | Description | Source Logic |
| :--- | :--- | :--- | :--- |
| `query_id` | String | 쿼리 식별자 | 파일명 파싱 (`q001_desc.sql` -> `q001`) |
| `question` | String | 자연어 질문 | 파일명 파싱 (`_` -> ` ` 변환) |
| `description` | String | 설명 | (Optional) `Auto-analyzed by sqlglot` |
| `unit_type` | String | 복잡도 분류 | **Driven Table Count** (Inner Join 수 + 1) 기준 (`UnitA`/`UnitB`/`UnitC`) |
| `metadata` | Object | 메타데이터 | 생성일시, 태그, 복잡도 등 |

### 1.2 SQL Structure (`sql.structure`)
AST 파싱을 통해 추출된 SQL의 구성 요소입니다.

```json
"structure": {
  "from_table": "TB_USER",
  "select_columns": [
    {
      "alias": "user_cnt",
      "expression": "COUNT(*)",
      "table": "TB_USER",
      "column": "id",
      "aggregation": "COUNT"
    }
  ],
  "joins": [
    {
      "type": "INNER",
      "table": "TB_ORDER",
      "on_condition": "TB_USER.id = TB_ORDER.user_id"
    }
  ],
  "where_conditions": [
    {
      "column": "TB_USER.status",
      "operator": "=",
      "value": "'ACTIVE'",
      "type": "filter"
    }
  ]
}
```

---

## 2. Database Schema (Physical DDL)

JSON 데이터를 적재하는 SQLite 테이블 생성 쿼리(DDL)입니다. (`load_json_data.py` 참조)

### 2.1 Master Metadata Table (`TB_QUERY_ASSET`)
```sql
CREATE TABLE IF NOT EXISTS TB_QUERY_ASSET (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id TEXT UNIQUE NOT NULL,
    question TEXT NOT NULL,
    description TEXT,
    unit_type TEXT,          -- UnitA, UnitB, UnitC
    unit_description TEXT,
    entities TEXT,           -- JSON Array
    presentation_type TEXT,  -- table, chart
    presentation_config TEXT,-- JSON Object
    from_table TEXT,
    group_by TEXT,           -- JSON Array
    order_by TEXT,           -- JSON Array
    original_sql TEXT,
    normalized_sql TEXT,
    created_at TEXT,
    modified_at TEXT,
    modification_count INTEGER DEFAULT 0,
    tags TEXT,
    complexity TEXT,
    estimated_rows TEXT,
    identity_hash TEXT       -- 쿼리 변경 감지용
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_asset_query_id ON TB_QUERY_ASSET(query_id);
CREATE INDEX IF NOT EXISTS idx_asset_question ON TB_QUERY_ASSET(question);
CREATE INDEX IF NOT EXISTS idx_asset_unit_type ON TB_QUERY_ASSET(unit_type);
```

### 2.2 History Table (`TB_QUERY_HISTORY`)
```sql
CREATE TABLE IF NOT EXISTS TB_QUERY_HISTORY (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER, -- 삭제되기 전의 ASSET ID
    query_id TEXT,
    question TEXT,
    original_sql TEXT,
    archived_at TEXT, -- 이력화(Archive) 시점
    reason TEXT       -- 'UPDATE', 'DELETE'
);
```

### 2.3 Detail Tables (Sub-Components)

**Select Columns (`query_select_columns`)**
```sql
CREATE TABLE IF NOT EXISTS query_select_columns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id TEXT NOT NULL,
    alias TEXT,
    expression TEXT,
    table_name TEXT,
    column_name TEXT,
    aggregation TEXT,
    category TEXT DEFAULT 'all', -- basic, detail, all
    FOREIGN KEY(query_id) REFERENCES TB_QUERY_ASSET(query_id)
);
```

**Joins (`query_joins`)**
```sql
CREATE TABLE IF NOT EXISTS query_joins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id TEXT NOT NULL,
    join_type TEXT,   -- INNER, LEFT, ...
    table_name TEXT,
    on_condition TEXT,
    relationship TEXT,
    FOREIGN KEY(query_id) REFERENCES TB_QUERY_ASSET(query_id)
);
```

**Where Conditions (`query_where_conditions`)**
```sql
CREATE TABLE IF NOT EXISTS query_where_conditions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id TEXT NOT NULL,
    column_name TEXT,
    operator TEXT,    -- =, >, <, IN, LIKE...
    value TEXT,
    condition_type TEXT, -- filter, partition
    FOREIGN KEY(query_id) REFERENCES TB_QUERY_ASSET(query_id)
);
```

### 2.4 Generated DB (`generated_queries`)
LLM 서비스 과정에서 생성된 파생 쿼리 저장소 (별도 DB 파일 권장: `query_rebuilder.db`)

```sql
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
