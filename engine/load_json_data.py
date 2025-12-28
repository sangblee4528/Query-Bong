"""
Query JSON to SQLite Migrator
3: 
4: SQL 쿼리 JSON 파일을 SQLite 데이터베이스로 마이그레이션합니다.
5: - 쿼리 메타데이터 저장 (TB_QUERY_ASSET)
6: - 쿼리 이력 저장 (TB_QUERY_HISTORY)
7: - Move-then-Insert 전략 구현
"""

import sqlite3
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any

# 프로젝트 루트 추가 및 설정 로드
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from config.loader import CFG


class QueryIndexerDB:
    """SQL 쿼리 JSON을 SQLite로 마이그레이션 (이력 관리 포함)"""
    
    def __init__(self, db_name=None):
        self.db_path = CFG['DB_PATH']
        self.data_dir = CFG['TEMPLATES_PATH']
        
    def create_tables(self):
        """데이터베이스 스키마 생성 (IF NOT EXISTS)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. TB_QUERY_ASSET: 현재 유효한 쿼리 자산
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS TB_QUERY_ASSET (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_id TEXT UNIQUE NOT NULL,
                question TEXT NOT NULL,
                description TEXT,
                unit_type TEXT,
                unit_description TEXT,
                entities TEXT,
                presentation_type TEXT,
                presentation_config TEXT,
                from_table TEXT,
                group_by TEXT,
                order_by TEXT,
                original_sql TEXT,
                normalized_sql TEXT,
                created_at TEXT,
                modified_at TEXT,
                modification_count INTEGER DEFAULT 0,
                tags TEXT,
                complexity TEXT,
                estimated_rows TEXT,
                identity_hash TEXT -- 쿼리 식별용 해시 (나중에 추가 확장 가능)
            )
        """)
        
        # 2. TB_QUERY_HISTORY: 변경/삭제된 이력 보관
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS TB_QUERY_HISTORY (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_id INTEGER, -- TB_QUERY_ASSET의 id (삭제 전)
                query_id TEXT,
                question TEXT,
                original_sql TEXT,
                archived_at TEXT, -- 이력 화 된 시점
                reason TEXT -- 'UPDATE', 'DELETE' 등
            )
        """)
        
        # 3. 하위 테이블들 (ASSET과 연결)
        # 심플함을 위해 하위 테이블은 ASSET ID가 아닌 query_id로 연결 유지
        
        # query_select_columns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_select_columns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_id TEXT NOT NULL,
                alias TEXT,
                expression TEXT,
                table_name TEXT,
                column_name TEXT,
                aggregation TEXT,
                category TEXT DEFAULT 'all',
                FOREIGN KEY(query_id) REFERENCES TB_QUERY_ASSET(query_id)
            )
        """)
        
        # query_joins
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_joins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_id TEXT NOT NULL,
                join_type TEXT,
                table_name TEXT,
                on_condition TEXT,
                relationship TEXT,
                FOREIGN KEY(query_id) REFERENCES TB_QUERY_ASSET(query_id)
            )
        """)
        
        # query_where_conditions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_where_conditions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_id TEXT NOT NULL,
                column_name TEXT,
                operator TEXT,
                value TEXT,
                condition_type TEXT,
                FOREIGN KEY(query_id) REFERENCES TB_QUERY_ASSET(query_id)
            )
        """)

        # 인덱스
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_asset_query_id ON TB_QUERY_ASSET(query_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_asset_question ON TB_QUERY_ASSET(question)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_asset_unit_type ON TB_QUERY_ASSET(unit_type)")
        
        conn.commit()
        conn.close()
        print(f"✅ DB 스키마 생성 완료 (TB_QUERY_ASSET/HISTORY 적용): {self.db_path}")
    
    def _archive_existing_query(self, cursor, query_id: str):
        """
        동일한 query_id가 존재하면 History로 이동(Move) 후 삭제.
        설계서의 'Move-then-Insert' 로직 구현.
        """
        # 기존 데이터 조회
        cursor.execute("SELECT id, query_id, question, original_sql FROM TB_QUERY_ASSET WHERE query_id = ?", (query_id,))
        existing = cursor.fetchone()
        
        if existing:
            asset_id, q_id, question, sql = existing
            # History에 Insert
            cursor.execute("""
                INSERT INTO TB_QUERY_HISTORY (asset_id, query_id, question, original_sql, archived_at, reason)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (asset_id, q_id, question, sql, datetime.now().isoformat(), 'UPDATE'))
            
            # Asset에서 Delete
            cursor.execute("DELETE FROM TB_QUERY_ASSET WHERE id = ?", (asset_id,))
            
            # 하위 테이블 데이터 삭제 (Cascade가 없으므로 수동 삭제)
            cursor.execute("DELETE FROM query_select_columns WHERE query_id = ?", (q_id,))
            cursor.execute("DELETE FROM query_joins WHERE query_id = ?", (q_id,))
            cursor.execute("DELETE FROM query_where_conditions WHERE query_id = ?", (q_id,))
            
            print(f"  Start Archiving: 기존 {query_id} 쿼리를 History로 이동하고 삭제했습니다.")
            return True
        return False

    def migrate_json_file(self, json_filepath: str):
        """단일 JSON 파일을 DB로 마이그레이션"""
        if not os.path.exists(json_filepath):
            print(f"❌ 파일을 찾을 수 없습니다: {json_filepath}")
            return False
        
        with open(json_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            query_id = data['query_id']
            
            # 1. Move (Archive if exists)
            self._archive_existing_query(cursor, query_id)
            
            # 2. Insert New Asset
            cursor.execute("""
                INSERT INTO TB_QUERY_ASSET (
                    query_id, question, description, unit_type, unit_description,
                    entities, presentation_type, presentation_config,
                    from_table, group_by, order_by,
                    original_sql, normalized_sql,
                    created_at, modified_at, modification_count,
                    tags, complexity, estimated_rows
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['query_id'],
                data['question'],
                data.get('description'),
                data['unit_type'],
                data['unit_description'],
                json.dumps(data.get('entities', []), ensure_ascii=False),
                data['presentation_type'],
                json.dumps(data.get('presentation_config', {}), ensure_ascii=False),
                data['sql']['structure']['from_table'],
                json.dumps(data['sql']['structure'].get('group_by', []), ensure_ascii=False),
                json.dumps(data['sql']['structure'].get('order_by', []), ensure_ascii=False),
                data['sql']['original'],
                data['sql']['normalized'],
                data['metadata']['created_at'],
                data['metadata'].get('modified_at'),
                data['metadata'].get('modification_count', 0),
                json.dumps(data['metadata'].get('tags', []), ensure_ascii=False),
                data['metadata']['complexity'],
                data['metadata'].get('estimated_rows')
            ))
            
            # 3. Insert Sub-tables
            # SELECT Columns
            if 'presentation_presets' in data:
                for category, cols in data['presentation_presets'].items():
                    for col in cols:
                        cursor.execute("""
                            INSERT INTO query_select_columns (
                                query_id, alias, expression, table_name, column_name, aggregation, category
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            query_id, col.get('alias'), col.get('expression'),
                            col.get('table'), col.get('column'), col.get('aggregation'), category
                        ))
            else:
                 # Legacy Fallback
                for col in data['sql']['structure']['select_columns']:
                    cursor.execute("""
                        INSERT INTO query_select_columns (
                            query_id, alias, expression, table_name, column_name, aggregation, category
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        query_id, col.get('alias'), col.get('expression'),
                        col.get('table'), col.get('column'), col.get('aggregation'), 'all'
                    ))

            # JOINS
            for join in data['sql']['structure']['joins']:
                cursor.execute("""
                    INSERT INTO query_joins (
                        query_id, join_type, table_name, on_condition, relationship
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    query_id, join['type'], join['table'], join['on_condition'], join['relationship']
                ))
            
            # WHERE Conditions
            for cond in data['sql']['structure']['where_conditions']:
                cursor.execute("""
                    INSERT INTO query_where_conditions (
                        query_id, column_name, operator, value, condition_type
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    query_id, cond['column'], cond['operator'], cond['value'], cond['type']
                ))
            
            conn.commit()
            print(f"  ✅ {query_id} 등록 완료")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"  ❌ {json_filepath} 등록 실패: {str(e)}")
            return False
        finally:
            conn.close()
    
    def migrate_all_queries(self):
        """data 디렉토리의 모든 query_*.json 파일을 마이그레이션"""
        print(f"🚀 쿼리 자산 등록 시작 (Move-then-Insert Strategy)...")
        
        migrated_count = 0
        failed_count = 0
        
        if not os.path.exists(self.data_dir):
             print(f"⚠️ 템플릿 디렉토리({self.data_dir})가 없습니다.")
             return

        for filename in os.listdir(self.data_dir):
            if filename.startswith("query_") and filename.endswith(".json"):
                filepath = os.path.join(self.data_dir, filename)
                if self.migrate_json_file(filepath):
                    migrated_count += 1
                else:
                    failed_count += 1
        
        print(f"\n✨ 작업 완료!")
        print(f"  - 성공(신규/갱신): {migrated_count}개")
        print(f"  - 실패: {failed_count}개")
    
    def verify_db(self):
        """데이터베이스 무결성 검증"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        print("\n📊 [DB 현황 리포트]")
        
        cursor.execute("SELECT COUNT(*) FROM TB_QUERY_ASSET")
        print(f" - 현재 자산(Active): {cursor.fetchone()[0]}개")
        
        cursor.execute("SELECT COUNT(*) FROM TB_QUERY_HISTORY")
        print(f" - 변경 이력(History): {cursor.fetchone()[0]}개")
        
        conn.close()


if __name__ == "__main__":
    # 데이터베이스 생성 및 마이그레이션
    indexer = QueryIndexerDB()
    indexer.create_tables()
    indexer.migrate_all_queries()
    indexer.verify_db()
