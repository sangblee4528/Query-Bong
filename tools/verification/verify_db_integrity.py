"""
DB Integrity Verification Tool
역할: 데이터베이스 스키마와 데이터 무결성을 검증합니다.
"""

import os
import sys
import sqlite3
import json

# 프로젝트 루트 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.loader import CFG

def verify_database():
    db_path = CFG['DB_PATH']
    print(f"🔍 검증 시작: {db_path}")
    
    if not os.path.exists(db_path):
        print("❌ DB 파일이 존재하지 않습니다.")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # 1. 테이블 존재 여부 확인
        print("\n[1] 테이블 존재 여부 확인")
        required_tables = [
            'TB_QUERY_ASSET', 
            'TB_QUERY_HISTORY', 
            'query_select_columns', 
            'query_joins', 
            'query_where_conditions'
        ]
        
        for table in required_tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone():
                print(f"  ✅ {table}: OK")
            else:
                print(f"  ❌ {table}: MISSING")

        # 2. 데이터 레코드 수 확인
        print("\n[2] 데이터 레코드 수 확인")
        for table in required_tables:
            cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
            cnt = cursor.fetchone()['cnt']
            print(f"  - {table}: {cnt} rows")

        # 3. TB_QUERY_ASSET 상세 검증
        print("\n[3] Active Asset 상세 검증")
        cursor.execute("SELECT * FROM TB_QUERY_ASSET LIMIT 5")
        rows = cursor.fetchall()
        for row in rows:
            print(f"  🔹 [{row['query_id']}] {row['question']} (Type: {row['unit_type']})")
            
            # 하위 테이블 연관성 확인
            cursor.execute("SELECT COUNT(*) as cnt FROM query_select_columns WHERE query_id = ?", (row['query_id'],))
            cols_cnt = cursor.fetchone()['cnt']
            print(f"     -> Columns: {cols_cnt}")
            
            cursor.execute("SELECT COUNT(*) as cnt FROM query_joins WHERE query_id = ?", (row['query_id'],))
            joins_cnt = cursor.fetchone()['cnt']
            print(f"     -> Joins: {joins_cnt}")

        # 4. History 검증
        print("\n[4] History 검증")
        cursor.execute("SELECT * FROM TB_QUERY_HISTORY ORDER BY history_id DESC LIMIT 3")
        rows = cursor.fetchall()
        if not rows:
            print("  ⚠️ History가 비어있습니다 (아직 수정/재등록이 발생하지 않았을 수 있음)")
        else:
            for row in rows:
                print(f"  🕰️ [Hist #{row['history_id']}] {row['query_id']} (Archived at: {row['archived_at']})")

    except Exception as e:
        print(f"❌ 검증 중 오류 발생: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    verify_database()
