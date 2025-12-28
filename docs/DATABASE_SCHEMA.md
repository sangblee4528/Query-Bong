# 🗄️ Database Schema Documentation

Query-Bong 시스템은 데이터를 물리적으로 분리하여 관리합니다. **Master DB**는 관리자가 승인한 황금 템플릿(Golden Templates)을 보관하고, **Generated DB**는 사용자의 질문과 그에 따라 생성된 SQL(QA Pairs)을 기록합니다.

---

## 1. Master Database (`data/db/sql_queries.db`)

관리자가 등록한 원본 SQL 템플릿의 구조를 보관하는 핵심 데이터베이스입니다.

### 📊 `queries` (Master Metadata)
시스템에 등록된 전체 쿼리의 마스터 정보를 담고 있습니다.

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | INTEGER | 자동 증가 PK |
| `query_id` | TEXT | 쿼리 고유 ID (예: `q_001`, `v_q_001`) |
| `question` | TEXT | 쿼리를 대표하는 표준 질문 |
| `description` | TEXT | 쿼리의 비즈니스 목적 및 상세 설명 |
| `unit_type` | TEXT | 쿼리 복잡도 분류 (`unitA`, `unitB`, `unitC`) |
| `unit_description` | TEXT | 분류에 대한 상세 설명 |
| `entities` | TEXT | 관련 비즈니스 엔티티 (JSON Array: `["노선", "정류장"]`) |
| `presentation_type` | TEXT | 결과 데이터 형태 (`table`, `chart` 등) |
| `presentation_config`| TEXT | 시각화 설정 (JSON Object) |
| `from_table` | TEXT | 메인 테이블 명 |
| `group_by` | TEXT | 그룹화 기준 (JSON Array) |
| `order_by` | TEXT | 정렬 기준 (JSON Array) |
| `original_sql` | TEXT | 분석 전 원본 SQL 문 |
| `normalized_sql` | TEXT | 분석 및 정규화를 거친 표준 SQL 템플릿 |
| `tags` | TEXT | 검색용 태그 (JSON Array: `["통계", "이용객"]`) |
| `complexity` | TEXT | 쿼리 복잡도 (상/중/하) |
| `estimated_rows` | TEXT | 예상 데이터 규모 |
| `modification_count`| INTEGER | 이 템플릿을 기반으로 수정된 횟수 |
| `created_at` | TEXT | 등록 일시 |
| `modified_at` | TEXT | 최종 수정 일시 |

### 📋 `query_select_columns` (SELECT Clauses)
각 쿼리에서 추출 가능한 고정 컬럼들을 정의합니다.

| Column | Type | Description |
| :--- | :--- | :--- |
| `query_id` | TEXT | 원본 쿼리 ID (FK) |
| `alias` | TEXT | 컬럼 별칭 (AS) |
| `expression` | TEXT | 실제 SQL 표현식 (예: `SUM(cnt)`) |
| `table_name` | TEXT | 소속 테이블 명 |
| `column_name` | TEXT | 원본 컬럼 명 |
| `aggregation` | TEXT | 집계 함수 종류 (`SUM`, `AVG` 등) |
| `category` | TEXT | 노출 등급 (`basic`, `detail`, `all`) |

### 🔗 `query_joins` (JOIN Relationships)
쿼리가 참조하는 고정된 조인 관계를 정의합니다. (수정 불가)

| Column | Type | Description |
| :--- | :--- | :--- |
| `query_id` | TEXT | 원본 쿼리 ID (FK) |
| `join_type` | TEXT | 조인 종류 (`INNER JOIN`, `LEFT JOIN` 등) |
| `table_name` | TEXT | 조인 대상 테이블 명 |
| `on_condition` | TEXT | 조인 조건 (ON 절 내용) |

### 📍 `query_where_conditions` (Template filters)
템플릿 단계에서 미리 정의된 필터 조건들입니다.

| Column | Type | Description |
| :--- | :--- | :--- |
| `query_id` | TEXT | 원본 쿼리 ID (FK) |
| `column_name` | TEXT | 필터 대상 컬럼 |
| `operator` | TEXT | 연산자 (`=`, `>`, `IN` 등) |
| `value` | TEXT | 기본값 (Placeholder) |
| `condition_type` | TEXT | 필터 성격 (`partition_key`, `filter` 등) |

---

## 2. Generated Database (`data/db/query_rebuilder.db`)

사용자의 요청에 따라 실시간으로 생성된 쿼리와 이력을 관리합니다.

### 📈 `generated_queries` (Execution & QA Logs)
사용자의 실제 질문과 그에 따라 생성된 최종 SQL을 보관하는 **평가용 데이터 저장소**입니다.

| Column | Type | Description |
| :--- | :--- | :--- |
| `query_id` | TEXT | 생성된 쿼리의 고유 ID (예: `q_001_modified_1`) |
| `parent_query_id` | TEXT | 기반이 된 마스터 쿼리 ID |
| `question` | TEXT | **사용자의 실제 자연어 질문** |
| `description` | TEXT | 생성 맥락 설명 |
| `normalized_sql` | TEXT | **최종 조립된 완성형 SQL** |
| `tags` | TEXT | 마스터에서 상속된 태그 |
| `created_at` | TEXT | 생성 일시 |

### 🎯 `generated_query_where_conditions` (Modified Filters)
마스터 템플릿의 어떤 조건이 어떻게 수정되었는지 기록합니다.

| Column | Type | Description |
| :--- | :--- | :--- |
| `query_id` | TEXT | 생성된 쿼리 ID (FK) |
| `column_name` | TEXT | 수정된 컬럼 명 |
| `operator` | TEXT | 사용된 연산자 |
| `value` | TEXT | 사용자가 입력/주입한 실제 값 |
| `condition_type` | TEXT | 필터 성격 |

---

## 💡 Schema Management Policy
1. **Purity**: Master DB(`sql_queries.db`)는 에이전트 구동 중에 절대 직접 수정되지 않습니다.
2. **Evaluation**: `generated_queries` 테이블은 시스템의 정확도를 측정(Evaluation)하기 위한 핵심 질문-결과 데이터셋으로 활용됩니다.
3. **Traceability**: 모든 생성 쿼리는 `parent_query_id`를 통해 어떤 마스터 템플릿에서 파생되었는지 추적 가능합니다.
