"""
Query Catalog Generator - 쿼리 카탈로그 생성기
역할: DB의 모든 쿼리 정보를 읽어 사람이 읽기 쉬운 QUERY_CATALOG.md 문서로 자동 변환
구동자: 관리자 (수동 실행) 또는 mcp_server (메타데이터 업데이트시 자동으로 호출됨)
"""
import sqlite3
import os
import sys
import json
from datetime import datetime

# 프로젝트 루트 추가 및 설정 로드
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from config.loader import CFG

class QueryCatalogGenerator:
    def __init__(self, db_name=None):
        self.db_path = CFG['DB_PATH']
        self.output_path = CFG['CATALOG_PATH']
        
        # 출력 폴더 자동 생성
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

    def generate(self):
        if not os.path.exists(self.db_path):
            print(f"Error: Database not found at {self.db_path}")
            return

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. 헤더 작성
        md = "# 📊 SQL Query RAG Catalog\n\n"
        md += f"시스템에 등록된 SQL 템플릿 목록입니다. (업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n\n"

        # 2. 통계 요약
        cursor.execute("SELECT unit_type, COUNT(*) as cnt FROM queries GROUP BY unit_type")
        stats = cursor.fetchall()
        md += "## 📈 Summary\n"
        for stat in stats:
            md += f"- **{stat['unit_type']}**: {stat['cnt']}개\n"
        md += "\n---\n\n"

        # 3. 쿼리 상세 목록
        cursor.execute("SELECT * FROM queries ORDER BY unit_type, query_id")
        queries = cursor.fetchall()

        for q in queries:
            query_id = q['query_id']
            entities = json.loads(q['entities']) if q['entities'] else []
            
            md += f"### 🔹 {q['question']} (`{query_id}`)\n"
            md += f"- **설명**: {q['description'] or '설명 없음'}\n"
            md += f"- **분류**: {q['unit_type']} ({q['unit_description']})\n"
            md += f"- **엔티티**: {', '.join(entities) if entities else '없음'}\n"
            md += f"- **복잡도**: {q['complexity'] or 'N/A'}\n"
            
            # WHERE 조건 파라미터 추출
            cursor.execute("SELECT column_name, condition_type FROM query_where_conditions WHERE query_id = ?", (query_id,))
            params = cursor.fetchall()
            if params:
                param_list = [f"`{p['column_name'].split('.')[-1]}` ({p['condition_type']})" for p in params]
                md += f"- **수정 가능 파라미터**: {', '.join(param_list)}\n"

            md += "\n#### [SQL Template]\n"
            md += "```sql\n"
            md += q['normalized_sql'].strip() + "\n"
            md += "```\n\n"
            md += "---\n\n"

        conn.close()

        with open(self.output_path, "w", encoding="utf-8") as f:
            f.write(md)
        
        print(f"✅ 카탈로그 생성 완료: {self.output_path}")
        return self.output_path

if __name__ == "__main__":
    generator = QueryCatalogGenerator()
    generator.generate()
