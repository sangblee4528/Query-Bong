# 변경 내역: mcp_server/query_mcp_server.py

**날짜**: 2025-12-29
**작업자**: Antigravity (AI Assistant)
**파일명**: mcp_server/query_mcp_server.py

## 변경 요약
오프라인 및 스크립트 단독 실행 시 발생하던 `ImportError` 수정 및 중복 데코레이터 제거.

## 상세 변경 내용

### 1. 상대 경로 Import 수정 (Line 33-37)
- **문제**: `mcp dev` 또는 `python`으로 직접 스크립트를 실행할 때 상대 경로(`from .llm_query_rebuilder ...`)가 작동하지 않아 에러 발생.
- **수정**: `try-except` 블록을 사용하여 패키지 실행과 스크립트 실행을 모두 지원하도록 변경.

```python
# [변경 전]
from .llm_query_rebuilder import SQLRebuilder

# [변경 후]
try:
    from .llm_query_rebuilder import SQLRebuilder
except ImportError:
    from llm_query_rebuilder import SQLRebuilder
```

### 2. 중복 데코레이터 제거 (Line 110 부근)
- **문제**: `search_queries` 함수 위에 `@mcp.tool()` 데코레이터가 두 번 적용되어 있어 불필요한 경고 발생 가능.
- **수정**: 중복된 `@mcp.tool()` 라인 제거.

```python
# [변경 전]
@mcp.tool()
@mcp.tool()
def search_queries(...):

# [변경 후]
@mcp.tool()
def search_queries(...):
```
