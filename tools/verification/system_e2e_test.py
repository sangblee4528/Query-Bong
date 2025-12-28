"""
Verify All - 시스템 종합 검진 스크립트
역할: 분석, 저장, 수정, 재생성으로 이어지는 RAG 시스템의 전체 공정이 정상인지 확인
구동자: 관리자 (시스템 점검, 코드 수정 후 유지보수 시 수동 실행)
"""

import sys
import os
import sqlite3
import json

# 프로젝트 루트를 Python 경로에 추가 및 설정 로드
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from config.loader import CFG

from engine.sql_analyzer import SQLQueryAnalyzer
from engine.load_json_data import QueryIndexerDB
from mcp_server.query_mcp_server import modify_where_conditions, get_query_details

def verify_end_to_end():
    print("Step 1: Parsing SQL to JSON (Testing Unit Classification)")
    analyzer = SQLQueryAnalyzer()
    
    # LEFT JOIN이 포함된 쿼리 - unitA로 분류되어야 함 (기존 로직은 unitB)
    sql = """
    SELECT 
        T.trip_id,
        T.base_date,
        R.route_nm
    FROM Trip_Log T
    LEFT JOIN Route_Master R ON T.route_id = R.route_id
    WHERE T.base_date = '20251219'
    """
    result = analyzer.analyze_query(sql, "노선의 승차 로그 (LEFT JOIN 테스트)", "v_unit_test")
    print(f"  - Classified as: {result['unit_type']} ({result['unit_description']})")
    analyzer.save_to_json(result)
    
    print("\nStep 2: JSON to SQLite Migration")
    indexer = QueryIndexerDB()
    indexer.create_tables()
    indexer.migrate_all_queries()
    
    print("\nStep 3: Modifying conditions with 'basic' category")
    new_conds = json.dumps([
        {"column": "Trip_Log.base_date", "operator": "=", "value": "'20251225'", "type": "partition_key"}
    ])
    
    # 'basic' 카테고리 및 사용자 질문 로깅 테스트
    user_q = "2025년 크리스마스날 노선의 승차 로그를 요약해서 보여줘"
    modify_result = modify_where_conditions("v_unit_test", new_conds, user_question=user_q, category="basic")
    print(modify_result)
    
    print("\nStep 4: Verifying Regenerated SQL (Basic Category)")
    details = get_query_details("v_unit_test_modified_1")
    print(details)

if __name__ == "__main__":
    verify_end_to_end()
