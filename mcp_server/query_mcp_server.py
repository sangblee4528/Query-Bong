"""
Query Server - SQL Query RAG 시스템 메인 컨트롤러 (MCP 서버)
역할: LLM에게 검색, 수정, 실행 도구(Tool)를 제공하고 내부 엔진(rebuilder)을 제어
구동자: LLM (사용자가 대화형 인터페이스에서 질문 시 실시간으로 구동함)

흐름:
1. sql_json_result.py → JSON 생성
2. query_json_to_sqlite.py → JSON → SQLite 저장
3. query_server.py (이 파일) → SQLite에서 읽어서 MCP Tool 제공
4. LLM이 질문 → SQLite 검색 → WHERE 조건만 수정 → 새 쿼리 생성

제약사항:
- JOIN 조건: 고정 (수정 불가)
- SELECT 절: 고정 (Presentation 방식으로 미리 지정)
- WHERE 조건: 수정 가능 (값 변경, 조건 추가 가능)
- 쿼리 분류: unitA (단순), unitB (상세), unitC (복합)
"""

import os
import sys
import sqlite3
import json
from typing import Optional, List, Dict, Any

# 프로젝트 루트를 Python 경로에 추가 및 설정 로드
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from config.loader import CFG

from mcp.server.fastmcp import FastMCP
try:
    from .llm_query_rebuilder import SQLRebuilder
except ImportError:
    from llm_query_rebuilder import SQLRebuilder

# MCP 서버 초기화
mcp = FastMCP("SQL-Query-RAG-Server")

# 데이터베이스 경로
DB_PATH = CFG['DB_PATH']
GEN_DB_PATH = CFG['GEN_DB_PATH']


def initialize_generated_db():
    """generated_queries 테이블이 포함된 별도 DB 초기화"""
    if os.path.exists(GEN_DB_PATH):
        return

    print(f"📦 초기 생성 쿼리 DB 생성 중... ({GEN_DB_PATH})")
    conn = sqlite3.connect(GEN_DB_PATH)
    cursor = conn.cursor()
    
    # 생성 테이블 정의
    cursor.execute("""
        CREATE TABLE generated_queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_id TEXT UNIQUE NOT NULL,
            parent_query_id TEXT NOT NULL,
            question TEXT,
            description TEXT,
            normalized_sql TEXT,
            created_at TEXT,
            tags TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE generated_query_where_conditions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_id TEXT NOT NULL,
            column_name TEXT,
            operator TEXT,
            value TEXT,
            condition_type TEXT,
            FOREIGN KEY(query_id) REFERENCES generated_queries(query_id)
        )
    """)
    
    cursor.execute("CREATE INDEX idx_gen_query_id ON generated_queries(query_id)")
    conn.commit()
    conn.close()


# 초기화 실행
initialize_generated_db()


def query_db(query: str, params=(), db_type: str = 'master') -> Any:
    """SQLite 쿼리 실행 헬퍼 (master 또는 gen)"""
    path = DB_PATH if db_type == 'master' else GEN_DB_PATH
    
    if not os.path.exists(path):
        return f"Error: DB file not found at {path}"
    
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        rv = cursor.fetchall()
        conn.close()
        return rv
    except Exception as e:
        conn.close()
        return f"[{db_type}] Query Error: {str(e)}"


# ============================================================================
# Tool 1: 쿼리 검색 (자연어)
# ============================================================================
@mcp.tool()
def search_queries(search_text: str, unit_type: Optional[str] = None) -> str:
    """
    자연어로 기존 SQL 쿼리 템플릿을 검색합니다. 사용자의 질문과 가장 유사한 구조의 쿼리를 찾는 데 사용하세요.
    
    Args:
        search_text: 검색 키워드 (예: '노선별 이용객', '정류장 위치'). 질문, 설명, 연관 엔티티 내에서 검색합니다.
        unit_type: 쿼리의 복잡도 필터 ('unitA': 단순, 'unitB': 상세, 'unitC': 복합). 생략 가능.
    
    Returns:
        검색된 쿼리 목록 (ID, 질문, 분류 등)
    """
    try:
        # 검색 쿼리 구성 (설명과 질문에 가중치를 둠)
        sql = """
            SELECT query_id, question, description, unit_type, entities, tags, created_at
            FROM TB_QUERY_ASSET
            WHERE (question LIKE ? OR description LIKE ? OR entities LIKE ? OR tags LIKE ?)
        """
        params = [f"%{search_text}%", f"%{search_text}%", f"%{search_text}%", f"%{search_text}%"]
        
        if unit_type:
            sql += " AND unit_type = ?"
            params.append(unit_type)
        
        sql += " ORDER BY created_at DESC"
        
        rows = query_db(sql, tuple(params), db_type='master')
        
        if isinstance(rows, str):
            return rows
        
        if not rows:
            return f"🔍 '{search_text}'에 대한 검색 결과가 없습니다."
        
        # 결과 포맷팅
        summary = f"🔍 '{search_text}' 검색 결과 (총 {len(rows)}개)\n\n"
        
        for r in rows:
            entities = json.loads(r['entities']) if r['entities'] else []
            tags = r['tags'].split(',') if r['tags'] else []
            summary += f"🔹 {r['query_id']}\n"
            summary += f"   질문: {r['question']}\n"
            summary += f"   설명: {r['description'] or '없음'}\n"
            summary += f"   분류: {r['unit_type']}\n"
            if tags:
                summary += f"   태그: {', '.join(tags)}\n"
            if entities:
                summary += f"   엔티티: {', '.join(entities)}\n"
            summary += "\n"
        
        return summary
        
    except Exception as e:
        return f"❌ 검색 실패: {str(e)}"





# ============================================================================
# Tool 2: 쿼리 상세 조회
# ============================================================================
@mcp.tool()
def get_query_details(query_id: str) -> str:
    """
    특정 쿼리의 상세 구조 및 파라미터 정보를 조회합니다. 쿼리 수정(modify_where_conditions) 전 필수 단계입니다.
    
    이 도구를 통해 다음 정보를 확인하세요:
    - 고정된 JOIN 관계 (수정 불가)
    - 수정 가능한 WHERE 조건 컬럼 및 현재 값
    - 사용 가능한 SELECT 프리셋 카테고리 (basic, detail 등)
    
    Args:
        query_id: 조회할 쿼리 ID (예: 'q_001')
    
    Returns:
        쿼리의 논리적 구조, 파라미터, 재생성된 SQL 등의 상세 정보
    """
    try:
        # 쿼리 메타데이터 조회 (마스터 및 생성 테이블 모두 확인)
        rows = query_db("SELECT * FROM TB_QUERY_ASSET WHERE query_id = ?", (query_id,), db_type='master')
        if not rows or isinstance(rows, str):
            rows = query_db("SELECT * FROM generated_queries WHERE query_id = ?", (query_id,), db_type='gen')
            is_generated = True
        else:
            is_generated = False
        
        if isinstance(rows, str) or not rows:
            return f"❌ 쿼리를 찾을 수 없습니다: {query_id}"
        
        query = rows[0]
        entities = json.loads(query['entities']) if not is_generated and query['entities'] else []
        presentation_config = json.loads(query['presentation_config']) if not is_generated and query['presentation_config'] else {}
        
        # 실제 원본 query_id (조인/컬럼 조회용)
        base_query_id = query['parent_query_id'] if is_generated else query_id

        # JOIN 정보 조회 (고정 - 항상 마스터 DB)
        joins = query_db("SELECT * FROM query_joins WHERE query_id = ?", (base_query_id,), db_type='master')
        
        # WHERE 조건 조회
        if is_generated:
            conditions = query_db("SELECT * FROM generated_query_where_conditions WHERE query_id = ?", (query_id,), db_type='gen')
        else:
            conditions = query_db("SELECT * FROM query_where_conditions WHERE query_id = ?", (query_id,), db_type='master')
        
        # SELECT 컬럼 조회 (카테고리별 - 항상 마스터 DB)
        select_cols = query_db("SELECT * FROM query_select_columns WHERE query_id = ? ORDER BY category, id", (base_query_id,), db_type='master')
        
        # 상세 정보 포맷팅
        details = f"""
📋 쿼리 상세 정보

🆔 ID: {query['query_id']}
❓ 질문: {query['question']}
📝 설명: {query['description'] or '없음'}

🏷️ 분류:
  - 타입: {query.get('unit_type', 'Generated')} ({query.get('unit_description', '수정된 쿼리')})
  - 엔티티: {', '.join(entities) if entities else '없음'}
  - 복잡도: {query.get('complexity', 'N/A')}

🔧 SQL 구조:
  - FROM: {query['from_table']}
  - JOINs: {len(joins) if not isinstance(joins, str) else 0}개
"""
        
        # JOIN 정보 (고정, 수정 불가)
        if joins and not isinstance(joins, str) and len(joins) > 0:
            details += "\n  📎 JOIN 관계 (고정, 수정 불가):\n"
            for join in joins:
                details += f"    - {join['join_type']} {join['table_name']}\n"
                details += f"      ON {join['on_condition']}\n"
        
        # WHERE 조건 (수정 가능)
        if conditions and not isinstance(conditions, str):
            details += "\n  🔍 WHERE 조건 (수정 가능):\n"
            for cond in conditions:
                details += f"    - {cond['column_name']} {cond['operator']} {cond['value']} ({cond['condition_type']})\n"
        
        # SELECT 컬럼 정보
        if select_cols and not isinstance(select_cols, str):
            details += "\n  📊 SELECT 컬럼 (카테고리별):\n"
            current_cat = None
            for col in select_cols:
                if col['category'] != current_cat:
                    current_cat = col['category']
                    details += f"    [{current_cat}]\n"
                details += f"      - {col['alias']} ({col['expression']})\n"

        # Presentation
        details += f"\n📈 Presentation:\n"
        details += f"  - 타입: {query['presentation_type']}\n"
        details += f"  - 차트: {presentation_config.get('chart_type', 'N/A')}\n"
        
        # SQL
        details += f"\n📝 정규화된 SQL:\n{query['normalized_sql']}\n"
        
        # 메타데이터
        details += f"\n📅 메타데이터:\n"
        details += f"  - 생성일: {query['created_at']}\n"
        if query['modified_at']:
            details += f"  - 수정일: {query['modified_at']}\n"
            details += f"  - 수정 횟수: {query['modification_count']}\n"
        
        return details
        
    except Exception as e:
        return f"❌ 쿼리 조회 실패: {str(e)}"


# ============================================================================
# Tool 3: WHERE 조건 수정
# ============================================================================
@mcp.tool()
def modify_where_conditions(
    query_id: str,
    new_conditions: str,
    user_question: str = "",
    category: str = 'all'
) -> str:
    """
    기존 쿼리의 WHERE 조건을 변경하거나 프레젠테이션 수준을 조정하여 새로운 SQL을 생성합니다.
    
    Args:
        query_id: 기반이 되는 원본 쿼리 ID
        new_conditions: 변경할 WHERE 조건들의 JSON 배열 문자열. 
                       형식: '[{"column": "테이블.컬럼", "operator": "=", "value": "값", "type": "filter"}]'
        user_question: 사용자가 입력한 원래 자연어 질문 (검증 및 로깅용)
        category: 출력할 데이터 수준 ('basic': 요약 정보, 'detail': 상세 정보, 'all': 모든 정보)
    
    Returns:
        새로 생성된 쿼리의 ID와 변경 사항 요약
    """
    try:
        # 기존 쿼리 조회
        rows = query_db("SELECT * FROM TB_QUERY_ASSET WHERE query_id = ?", (query_id,), db_type='master')
        
        if isinstance(rows, str) or not rows:
            return f"❌ 쿼리를 찾을 수 없습니다: {query_id}"
        
        query = rows[0]
        
        # 새로운 조건 파싱
        try:
            conditions_list = json.loads(new_conditions)
        except:
            return "❌ 조건 형식이 올바르지 않습니다. JSON 배열 형식이어야 합니다."
        
        # 새로운 쿼리 ID 생성
        new_query_id = f"{query_id}_modified_{query['modification_count'] + 1}"
        
        # 트랜잭션 시작 (여기서는 2개의 DB를 다룸)
        # 1. 마스터에서 읽기
        cols_rows = query_db("SELECT * FROM query_select_columns WHERE query_id = ? AND category = ?", (query_id, category), db_type='master')
        if not cols_rows or isinstance(cols_rows, str):
            cols_rows = query_db("SELECT * FROM query_select_columns WHERE query_id = ? AND category = 'all'", (query_id,), db_type='master')
        
        cols = [dict(r) for r in cols_rows] if not isinstance(cols_rows, str) else []
        
        joins_rows = query_db("SELECT * FROM query_joins WHERE query_id = ?", (query_id,), db_type='master')
        joins = [dict(r) for r in joins_rows] if not isinstance(joins_rows, str) else []
        
        # 2. 생성 DB에 쓰기
        conn_gen = sqlite3.connect(GEN_DB_PATH)
        cursor_gen = conn_gen.cursor()
        
        # 3. 마스터 DB 업데이트 (수정 횟수)
        conn_master = sqlite3.connect(DB_PATH)
        cursor_master = conn_master.cursor()

        try:
            # 새 SQL 생성
            new_sql = SQLRebuilder.rebuild(
                select_columns=cols,
                from_table=query['from_table'],
                joins=joins,
                where_conditions=conditions_list,
                group_by=json.loads(query['group_by']) if query['group_by'] else [],
                order_by=json.loads(query['order_by']) if query['order_by'] else []
            )

            # 1. 생성된 쿼리 메타데이터 저장 (Generated DB)
            cursor_gen.execute("""
                INSERT INTO generated_queries (
                    query_id, parent_query_id, question, description,
                    normalized_sql, created_at, tags
                ) VALUES (?, ?, ?, ?, ?, datetime('now'), ?)
            """, (
                new_query_id, 
                query_id, 
                user_question if user_question else f"RE: {query['question']}", 
                f"Modified from {query_id} at {category} level",
                new_sql,
                query['tags']
            ))
            
            # 2. 새로운 WHERE 조건 저장 (Generated DB)
            for cond in conditions_list:
                cursor_gen.execute("""
                    INSERT INTO generated_query_where_conditions (query_id, column_name, operator, value, condition_type)
                    VALUES (?, ?, ?, ?, ?)
                """, (new_query_id, cond['column'], cond['operator'], cond['value'], cond.get('type', 'filter')))
            
            # 3. 마스터 테이블의 수정 횟수 업데이트
            cursor_master.execute("UPDATE TB_QUERY_ASSET SET modification_count = modification_count + 1 WHERE query_id = ?", (query_id,))
            
            conn_gen.commit()
            conn_master.commit()
            
            summary = f"""
✅ 쿼리 수정 완료!

📋 원본 쿼리: {query_id}
📝 새 쿼리: {new_query_id}

🔄 수정된 조건:
"""
            for cond in conditions_list:
                summary += f"  - {cond['column']} {cond['operator']} {cond['value']}\n"
            
            summary += f"\n💾 새 쿼리가 데이터베이스에 저장되었습니다."
            summary += f"\n\n💡 get_query_details('{new_query_id}')로 상세 정보를 확인하세요."
            
            return summary
            
        except Exception as e:
            if 'conn_gen' in locals(): conn_gen.rollback()
            if 'conn_master' in locals(): conn_master.rollback()
            return f"❌ 쿼리 수정 실패: {str(e)}"
        finally:
            if 'conn_gen' in locals(): conn_gen.close()
            if 'conn_master' in locals(): conn_master.close()
        
    except Exception as e:
        return f"❌ 쿼리 수정 실패: {str(e)}"


# ============================================================================
# Tool 4: 쿼리 목록 조회
# ============================================================================
@mcp.tool()
def list_queries(unit_type: Optional[str] = None, limit: int = 10) -> str:
    """
    저장된 쿼리 목록을 조회합니다.
    
    Args:
        unit_type: 쿼리 타입 필터 (unitA, unitB, unitC) - 선택
        limit: 최대 결과 수 (기본: 10)
    
    Returns:
        쿼리 목록
    """
    try:
        sql = "SELECT query_id, question, unit_type, entities, created_at FROM TB_QUERY_ASSET"
        params = []
        
        if unit_type:
            sql += " WHERE unit_type = ?"
            params.append(unit_type)
        
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        rows = query_db(sql, tuple(params), db_type='master')
        
        if isinstance(rows, str):
            return rows
        
        if not rows:
            return "📭 저장된 쿼리가 없습니다."
        
        summary = f"📚 저장된 쿼리 목록 (총 {len(rows)}개)\n\n"
        
        for q in rows:
            entities = json.loads(q['entities']) if q['entities'] else []
            summary += f"🔹 {q['query_id']}\n"
            summary += f"   질문: {q['question']}\n"
            summary += f"   분류: {q['unit_type']}\n"
            if entities:
                summary += f"   엔티티: {', '.join(entities)}\n"
            summary += "\n"
        
        return summary
        
    except Exception as e:
        return f"❌ 쿼리 목록 조회 실패: {str(e)}"


# ============================================================================
# Tool 5: 시스템 상태 확인
# ============================================================================
@mcp.tool()
def check_system_status() -> str:
    """
    SQL Query RAG 시스템의 상태를 확인합니다.
    
    Returns:
        시스템 상태 정보
    """
    try:
        # 전체 쿼리 수
        total_queries = query_db("SELECT COUNT(*) as cnt FROM TB_QUERY_ASSET", db_type='master')
        # 생성된 쿼리 수
        total_gen_queries = query_db("SELECT COUNT(*) as cnt FROM generated_queries", db_type='gen')
        
        # 타입별 통계 (마스터)
        stats = query_db("""
            SELECT unit_type, COUNT(*) as count 
            FROM TB_QUERY_ASSET 
            GROUP BY unit_type
        """, db_type='master')
        
        # JOIN 관계 수
        total_joins = query_db("SELECT COUNT(*) as cnt FROM query_joins", db_type='master')
        
        # WHERE 조건 수
        total_conditions = query_db("SELECT COUNT(*) as cnt FROM query_where_conditions", db_type='master')
        
        status = f"""
🔧 SQL Query RAG 시스템 상태

📁 마스터 DB: {DB_PATH}
📁 생성 DB: {GEN_DB_PATH}
📊 마스터 쿼리: {total_queries[0]['cnt'] if not isinstance(total_queries, str) else 'N/A'}개
📊 생성된 쿼리: {total_gen_queries[0]['cnt'] if not isinstance(total_gen_queries, str) else 'N/A'}개

📈 마스터 쿼리 분류 통계:
"""
        
        if not isinstance(stats, str):
            for row in stats:
                status += f"  - {row['unit_type']}: {row['count']}개\n"
        
        status += f"\n - 총 JOIN 관계 (고정): {total_joins[0]['cnt'] if not isinstance(total_joins, str) else 'N/A'}개"
        status += f"\n - 총 WHERE 조건 (수정 가능): {total_conditions[0]['cnt'] if not isinstance(total_conditions, str) else 'N/A'}개"
        status += "\n\n✅ 시스템 정상 작동 중"
        
        return status
        
    except Exception as e:
        return f"❌ 상태 확인 실패: {str(e)}"


# ============================================================================
# Tool 6: 쿼리 실행
# ============================================================================
@mcp.tool()
def execute_query(query_id: str) -> str:
    """
    저장된 쿼리를 실행하여 결과를 가져옵니다.
    
    Args:
        query_id: 실행할 쿼리 ID
    
    Returns:
        쿼리 실행 결과 (JSON 형식)
    """
    try:
        # 쿼리 조회 (마스터 및 생성 테이블 모두 확인)
        rows = query_db("SELECT normalized_sql FROM TB_QUERY_ASSET WHERE query_id = ?", (query_id,), db_type='master')
        if not rows or isinstance(rows, str):
            rows = query_db("SELECT normalized_sql FROM generated_queries WHERE query_id = ?", (query_id,), db_type='gen')
        
        if isinstance(rows, str) or not rows:
            return f"❌ 쿼리를 찾을 수 없습니다: {query_id}"
        
        sql = rows[0]['normalized_sql']
        
        # 실제 데이터베이스 연결 (여기서는 예시로 sql_queries.db 자체에서 혹은 별도 DB에서 실행)
        # 쿼리 RAG 시스템이므로 실제 업무 DB에 연결되어야 함.
        # 여기서는 동작 확인을 위해 샘플 DB(bus_data.db 등)가 있다고 가정하거나 
        # 결과를 시뮬레이션 할 수 있음.
        
        # 현재는 DB_PATH가 sql_queries.db (메타데이터 DB)이므로 
        # 실제 데이터가 있는 DB가 따로 필요함.
        # 유저 요청에 따라 현재 동작 확인을 위해 dummy 결과를 반환함.
        
        return f"🚀 쿼리 실행 시뮬레이션 ({query_id}):\n\nSQL:\n{sql}\n\n✅ 실행 결과: [Data Table Content...]"
        
    except Exception as e:
        return f"❌ 실행 실패: {str(e)}"


# ============================================================================
# 서버 실행
# ============================================================================
if __name__ == "__main__":
    # MCP 서버 실행 (stdio 모드)
    mcp.run()
