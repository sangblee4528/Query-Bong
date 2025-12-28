"""
SQL Query to JSON Converter (AST Based)
역할: 원본 SQL을 sqlglot AST로 분석하여 JSON 템플릿으로 변환 및 파일 이동 처리
"""

import os
import sys
import json
import shutil
import hashlib
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional

try:
    import sqlglot
    from sqlglot import exp, parse_one
    from sqlglot.optimizer import optimize
except ImportError:
    print("❌ sqlglot 패키지가 필요합니다. pip install sqlglot")
    sys.exit(1)

# 프로젝트 루트 추가 및 설정 로드
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from config.loader import CFG

class SQLQueryAnalyzer:
    """sqlglot AST 기반 SQL 분석기"""
    
    def __init__(self):
        self.source_dir = CFG.get('SOURCE_PATH')
        self.inbox_dir = os.path.join(self.source_dir, 'inbox')
        self.success_dir = os.path.join(self.source_dir, 'success')
        self.failed_dir = os.path.join(self.source_dir, 'failed')
        self.output_dir = CFG.get('TEMPLATES_PATH')
        
        # 디렉토리 생성
        for d in [self.inbox_dir, self.success_dir, self.failed_dir, self.output_dir]:
            os.makedirs(d, exist_ok=True)
            
    def _generate_identity_hash(self, from_table: str, select_exprs: List[str]) -> str:
        """쿼리 식별을 위한 해시 생성 (FROM + SELECT 조합)"""
        content = f"{from_table}|{'|'.join(sorted(select_exprs))}"
        return hashlib.md5(content.encode()).hexdigest()

    def analyze_file(self, filename: str) -> bool:
        """단일 파일 분석 및 처리 (Move logic 포함)"""
        filepath = os.path.join(self.inbox_dir, filename)
        if not os.path.exists(filepath):
            print(f"⚠️ 파일 없음: {filepath}")
            return False
            
        print(f"🔍 분석 시작: {filename}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                sql_content = f.read().strip()
                
            if not sql_content:
                raise ValueError("빈 파일입니다.")

            # AST 파싱
            parsed = parse_one(sql_content)
            
            # 메타데이터 추출 (파일명 기반)
            file_stem = os.path.splitext(filename)[0]
            # q001_설명.sql -> id: q001
            query_id = file_stem.split('_')[0] if '_' in file_stem else file_stem
            question = file_stem.replace('_', ' ')
            
            # 분석 실행
            result_json = self._analyze_ast(parsed, query_id, question, sql_content)
            
            # JSON 저장
            output_path = os.path.join(self.output_dir, f"query_{query_id}.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result_json, f, indent=2, ensure_ascii=False)
            
            # 성공 처리: Move to Success
            shutil.move(filepath, os.path.join(self.success_dir, filename))
            print(f"✅ 분석 성공 및 이동 완료: {filename} -> success/")
            return True
            
        except Exception as e:
            print(f"❌ 분석 실패: {filename} - {str(e)}")
            # 실패 처리: Move to Failed
            try:
                shutil.move(filepath, os.path.join(self.failed_dir, filename))
                
                # 에러 로그 작성
                log_path = os.path.join(self.failed_dir, f"{filename}.error.log")
                with open(log_path, 'w', encoding='utf-8') as f:
                    f.write(traceback.format_exc())
                print(f"⚠️ 실패 파일 이동 완료: {filename} -> failed/")
            except Exception as move_error:
                print(f"💀 파일 이동 중 치명적 오류: {move_error}")
            return False

    def _analyze_ast(self, ast: exp.Expression, query_id: str, question: str, original_sql: str) -> Dict[str, Any]:
        """AST 순회 및 데이터 구조화"""
        
        # 1. Initialization
        select_columns = []
        joins = []
        where_conditions = []
        group_by = []
        order_by = []
        from_table = "Unknown"
        
        # 2. Extract FROM
        from_exp = ast.find(exp.From)
        if from_exp:
            for source in from_exp.find_all(exp.Table):
                from_table = source.sql()
                break # Main table only
                
        # 3. Extract SELECT (Flexible Area)
        for projection in ast.find_all(exp.Select):
            for expression in projection.expressions:
                if isinstance(expression, exp.Alias):
                    alias = expression.alias
                    expr_sql = expression.this.sql()
                    # 간단한 aggregation 체크
                    agg = None
                    if expression.find(exp.AggFunc):
                        agg = expression.find(exp.AggFunc).sql()
                    
                    select_columns.append({
                        "alias": alias,
                        "expression": expr_sql,
                        "table": from_table, # 단순화 (실제로는 매핑 필요)
                        "column": expr_sql,
                        "aggregation": agg
                    })
                elif isinstance(expression, exp.Column):
                    select_columns.append({
                        "alias": expression.name,
                        "expression": expression.sql(),
                        "table": expression.table,
                        "column": expression.name,
                        "aggregation": None
                    })
            break # Main query select only

        # 4. Extract JOINs (Fixed Area)
        for join in ast.find_all(exp.Join):
            # sqlglot versions vary; safer to access via args
            join_kind = join.args.get("kind")
            join_type = join_kind.sql() if join_kind else "INNER"
            
            table = join.this.sql()
            
            on_arg = join.args.get("on") 
            on_cond = on_arg.sql() if on_arg else ""
            
            joins.append({
                "type": join_type,
                "table": table,
                "on_condition": on_cond,
                "relationship": on_cond # 단순 로직
            })

        # 5. Extract WHERE (Change Area)
        if ast.find(exp.Where):
            # 순회하며 조건 추출
            where_node = ast.find(exp.Where)
            
            # 재귀적으로 모든 조건절을 탐색하기보다, 최상위 AND 조건들만 분리하는 것이 이상적일 수 있으나
            # 현재 로직은 단순화를 위해 평탄화된 조건 리스트를 추출함
            
            for cond in where_node.find_all(exp.EQ, exp.GT, exp.LT, exp.GTE, exp.LTE, exp.NEQ, exp.In, exp.Between):
                col = ""
                val = ""
                operator = ""
                cond_type = "filter"
                
                if isinstance(cond, exp.Between):
                    operator = "BETWEEN"
                    col = cond.this.sql()
                    low = cond.args.get('low')
                    high = cond.args.get('high')
                    val = f"{low.sql()} AND {high.sql()}" if low and high else "Unknown"
                    
                elif isinstance(cond, exp.In):
                    operator = "IN"
                    col = cond.this.sql()
                    # args['expressions'] is a list of expressions
                    in_values = [e.sql() for e in cond.args.get('expressions', [])]
                    val = f"({', '.join(in_values)})"
                    
                else:
                    # Binary Operators (EQ, GT, LT ...)
                    if isinstance(cond, exp.EQ): operator = "="
                    elif isinstance(cond, exp.GT): operator = ">"
                    elif isinstance(cond, exp.LT): operator = "<"
                    elif isinstance(cond, exp.GTE): operator = ">="
                    elif isinstance(cond, exp.LTE): operator = "<="
                    elif isinstance(cond, exp.NEQ): operator = "<>"
                    
                    col = cond.this.sql()
                    val = cond.expression.sql() 
                    
                where_conditions.append({
                    "column": col,
                    "operator": operator,
                    "value": val,
                    "type": "filter"
                })

        # 6. Extract GROUP BY
        if ast.find(exp.Group):
            for grp in ast.find(exp.Group).expressions:
                group_by.append(grp.sql())

        # 7. Extract ORDER BY
        if ast.find(exp.Order):
            for ord in ast.find(exp.Order).expressions:
                order_by.append(ord.sql())
        
        # 8. Classification (Unit Logic)
        # Driven Table 기준 (LEFT/RIGHT OUTER 제외, INNER JOIN만 카운트)
        unit_type = "unitA"
        
        # 기본: FROM Table (1개)
        # INNER JOIN된 테이블만 카운트에 포함
        inner_join_tables = [j['table'] for j in joins if "LEFT" not in j['type'].upper() and "RIGHT" not in j['type'].upper() and "OUTER" not in j['type'].upper()]
        
        # 유효 엔티티 수 = Main + Inner Joins
        effective_entity_count = 1 + len(inner_join_tables)

        if effective_entity_count >= 3:
            unit_type = "unitC"
        elif effective_entity_count == 2:
            unit_type = "unitB"
        else:
            unit_type = "unitA"
        # 9. Construct JSON
        return {
            "query_id": query_id,
            "question": question,
            "description": "Auto-analyzed by sqlglot",
            "unit_type": unit_type,
            "unit_description": "Automated Unit Classification",
            "entities": list(set(entities)),
            "presentation_type": "table",
            "presentation_config": {},
            "sql": {
                "original": original_sql,
                "normalized": ast.sql(),
                "structure": {
                    "select_columns": select_columns,
                    "from_table": from_table,
                    "joins": joins,
                    "where_conditions": where_conditions,
                    "group_by": group_by,
                    "order_by": order_by
                }
            },
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "tags": entities,
                "complexity": "low",
                "estimated_rows": "unknown"
            }
        }

    def process_inbox(self):
        """Inbox의 모든 파일 처리"""
        files = [f for f in os.listdir(self.inbox_dir) if f.endswith('.sql') or f.endswith('.txt')]
        if not files:
            print("📭 Inbox가 비어있습니다.")
            return
            
        print(f"🚀 Inbox 처리 시작 ({len(files)}개 파일)...")
        success_count = 0
        
        for f in files:
            if self.analyze_file(f):
                success_count += 1
                
        print(f"\n✨ 처리 완료: 성공 {success_count} / 전체 {len(files)}")


if __name__ == "__main__":
    analyzer = SQLQueryAnalyzer()
    analyzer.process_inbox()
