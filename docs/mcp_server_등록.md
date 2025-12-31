# MCP Server 등록 가이드

이 문서는 `query_mcp_server.py`를 Void Editor, Cursor 등 MCP 호환 클라이언트에 등록하는 방법을 설명합니다.
이 설정은 **폐쇄망(Offline)** 환경에서도 로컬 파이썬을 이용해 안전하게 작동합니다.

## 1. 등록 정보

*   **서버 이름**: sql-query-rag (임의 지정 가능)
*   **실행 명령어**: `python` (또는 로컬 환경에 맞는 파이썬 경로)
*   **인자(Args)**: 서버 스크립트의 **절대 경로**

## 2. JSON 설정 예시

MCP 클라이언트의 설정 파일(예: `mcp_config.json`, `settings.json` 등) 내 `mcpServers` 섹션에 아래 내용을 추가하세요.

```json
{
  "mcpServers": {
    "sql-query-rag": {
      "command": "python",
      "args": [
        "/Users/bong/workspace/Query-Bong/mcp_server/query_mcp_server.py"
      ],
      "env": {
        "PYTHONUTF8": "1"
      }
    }
  }
}
```

> **주의**: `/Users/bong/workspace/Query-Bong/...` 부분은 실제 파일이 위치한 경로로 정확히 수정해주셔야 합니다.

## 3. Void Editor 등록 방법

1.  Void Editor를 실행합니다.
2.  설정(Settings) 메뉴로 이동하거나 `Ctrl+Shift+P` (Mac: `Cmd+Shift+P`)를 눌러 **MCP Config**를 검색합니다.
3.  설정 파일이 열리면 위 JSON 코드를 적절한 위치에 붙여넣습니다.
4.  에디터를 재시작(Reload Window)하면 AI가 해당 도구를 인식합니다.

## 4. HTTP/SSE 모드로 실행하기 (Void Editor, etc.)

Void Editor 등에서 `sse` (Server-Sent Events) 방식을 사용하려면 아래와 같이 실행하세요.

1.  **서버 실행**:
    ```bash
    python mcp_server/query_mcp_server.py --transport sse
    ```
    *   기본적으로 `8000` 포트에서 실행됩니다.
    *   `--port` 옵션으로 포트를 변경할 수 있습니다.

2.  **Void Editor 등록**:
    *   설정에서 **MCP Server** 추가 시 **Type**을 `SSE`로 선택합니다.
    *   **URL**: `http://localhost:8000/sse`

## 5. 문제 해결

*   **실행 안 됨**:
    *   파이썬 경로가 환경 변수(`PATH`)에 잡혀있는지 확인하세요.
    *   절대 경로(`args`)가 정확한지 다시 한번 확인하세요.
*   **SSE 연결 실패 ("Red Light")**:
    *   서버가 백그라운드에서 실행 중인지 확인하세요 (`python ... --transport sse`).
    *   URL이 `http://localhost:8000/sse` 인지 확인하세요 (`/messages` 아님).
*   **인코딩 오류**:
    *   `env` 설정에 `"PYTHONUTF8": "1"`을 포함하면 도움이 됩니다.
