# Query-Bong 🚀

**Selective SQL-RAG Engine** for Safe & Accurate Data Retrieval.

**Query-Bong**은 사용자의 자연어 질문을 분석하여, 미리 검증된 **Golden SQL Templates**에서 최적의 쿼리를 선택하고, 사용자의 의도에 맞춰 **조건(WHERE 절)**만을 안전하게 수정하여 실행하는 차세대 RAG 엔진입니다.

---

## 🏗️ Architecture

```text
Query-Bong/
├── engine/             # Core Logic
│   ├── sql_analyzer.py # SQL Parser & JSON Converter (sqlglot based)
│   └── load_json_data.py # JSON to SQLite Migrator
├── mcp_server/         # MCP(Model Context Protocol) Interface
│   ├── query_mcp_server.py # LLM Tool Provider
│   └── llm_query_rebuilder.py # Dynamic SQL Rebuilder
├── data/               # Assets
│   ├── templates/      # Analyzed JSON Templates
│   └── db/             # Metadata DB (sql_queries.db)
└── docs/               # Documentation
    ├── WORKFLOW.md      # System Flowchart
    └── DATABASE_SCHEMA.md # Detailed DB & JSON Spec
```

## 🌟 Key Features

1.  **Safety First**: 복잡한 JOIN과 비즈니스 로직은 고정(Fixed)하고, 오직 검색 조건(Flexible Area)만 수정하여 실행합니다. Hallucination에 의한 잘못된 SQL 생성을 원천 차단합니다.
2.  **Context Aware**: 단순 텍스트 매칭이 아닌, 쿼리의 구조와 비즈니스 엔티티를 분석하여 가장 적합한 템플릿을 찾아냅니다.
3.  **Human Readable**: 생성된 모든 JSON 템플릿과 실행 이력은 사람이 읽고 검증할 수 있습니다.
4.  **MCP Ready**: `mcp` 프로토콜을 지원하여 Claude Desktop, Cursor 등 다양한 LLM 클라이언트와 즉시 연동됩니다.

## 🚀 Getting Started

### 1. Installation

Python 3.10+ 환경이 필요합니다.

```bash
# Clone Repository
git clone https://github.com/sangblee4528/Query-Bong.git
cd Query-Bong

# Setup Virtual Environment
python3 -m venv .venv
source .venv/bin/activate

# Install Dependencies
pip install -r requirements.txt
```

### 2. Run MCP Server (Dev Mode)

로컬에서 MCP 서버를 실행하여 LLM과 연동 테스트를 할 수 있습니다.

```bash
# Install MCP Inspector if needed
npm install -g @modelcontextprotocol/inspector

# Run Server
mcp dev mcp_server/query_mcp_server.py
```

### 3. Usage Examples

*   **새 쿼리 등록**: `.sql` 파일을 `data/source/inbox`에 넣고 `python engine/sql_analyzer.py` 실행.
*   **DB 마이그레이션**: `python engine/load_json_data.py` 실행.

## 📚 Documentation

더 자세한 기술 내용은 아래 문서를 참고하세요.

*   [📅 워크플로우 가이드 (Workflow)](docs/WORKFLOW.md)
*   [🗄️ 데이터베이스 스키마 및 JSON 구조 (Schema)](docs/DATABASE_SCHEMA.md)
*   [📓 쿼리 카탈로그 (Catalog)](docs/QUERY_CATALOG.md)

---

### License
MIT License. Created by **Query-Bong Team**.
