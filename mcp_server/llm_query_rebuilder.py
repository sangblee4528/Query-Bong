"""
SQL Rebuilder - 쿼리 재구성 엔진
역할: DB에 저장된 쿼리 조각(SELECT, JOIN, WHERE 등)을 조합하여 실행 가능한 SQL 문장 생성
구동자: LLM (mcp_server의 도구 호출을 통해 실시간으로 구동됨)
"""
from typing import List, Dict, Any

class SQLRebuilder:
    """SQL 구성 요소를 사용하여 SQL 쿼리를 재구성합니다."""
    
    @staticmethod
    def rebuild(
        select_columns: List[Dict[str, Any]],
        from_table: str,
        joins: List[Dict[str, Any]],
        where_conditions: List[Dict[str, Any]],
        group_by: List[str] = None,
        order_by: List[str] = None
    ) -> str:
        """
        구성 요소를 조합하여 SQL 문자열 생성
        """
        # 1. SELECT 절
        select_parts = []
        for col in select_columns:
            expr = col.get('expression')
            alias = col.get('alias')
            
            # aggregation이 있는 경우 처리 (예: COUNT(T.trip_id))
            # 이미 expression에 포함되어 있을 가능성이 높음
            
            if alias and alias != expr and " AS " not in expr.upper():
                clean_alias = alias.strip("'\"")
                select_parts.append(f"{expr} AS '{clean_alias}'")
            else:
                select_parts.append(expr)
        
        select_clause = "SELECT\n    " + ",\n    ".join(select_parts)
        
        # 2. FROM 절
        # 만약 normalized_sql을 사용한다면 alias가 없을 수 있음.
        # 여기서는 원본 쿼리의 형식을 따르기 위해 alias를 고려해야 할 수도 있음.
        # 하지만 현재 시스템은 normalized_sql을 지향하므로 alias 없이 작성함.
        from_clause = f"FROM {from_table}"
        
        # 3. JOIN 절
        join_parts = []
        for join in joins:
            join_parts.append(f"{join['join_type']} {join['table_name']} ON {join['on_condition']}")
        
        join_clause = "\n".join(join_parts)
        
        # 4. WHERE 절
        where_parts = []
        for cond in where_conditions:
            col_name = cond.get('column') or cond.get('column_name')
            where_parts.append(f"{col_name} {cond['operator']} {cond['value']}")
        
        where_clause = ""
        if where_parts:
            where_clause = "WHERE " + "\n  AND ".join(where_parts)
        
        # 5. GROUP BY 절
        group_by_clause = ""
        if group_by:
            group_by_clause = "GROUP BY " + ", ".join(group_by)
            
        # 6. ORDER BY 절
        order_by_clause = ""
        if order_by:
            order_by_clause = "ORDER BY " + ", ".join(order_by)
            
        # 전체 쿼리 조합
        query_parts = [select_clause, from_clause]
        if join_clause:
            query_parts.append(join_clause)
        if where_clause:
            query_parts.append(where_clause)
        if group_by_clause:
            query_parts.append(group_by_clause)
        if order_by_clause:
            query_parts.append(order_by_clause)
            
        return "\n".join(query_parts)
