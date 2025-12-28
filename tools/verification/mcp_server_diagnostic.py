#!/usr/bin/env python3
"""
Detailed MCP Test - MCP 서버 정밀 진단 도구
역할: MCP 서버가 정상적으로 로드되는지, 도구들이 올바르게 등록되었는지 내부 상태 점검
구동자: 관리자 (서버 구동 문제 발생 시 디버깅 용도로 실행)
"""

import sys
import os

# 프로젝트 루트 추가 및 설정 로드
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from config.loader import CFG

def test_server_py():
    """server.py 테스트"""
    print("\n" + "="*60)
    print("Testing: Code Analysis Server (server.py)")
    print("="*60 + "\n")
    
    # server.py 임포트 및 테스트
    sys.path.insert(0, os.path.join(project_root, "mcp-server"))
    
    try:
        # FastMCP 객체 가져오기
        import server
        mcp = server.mcp
        
        print(f"✅ Server Name: {mcp.name}")
        print(f"✅ Server loaded successfully\n")
        
        # 등록된 도구 확인
        tools = mcp._tool_manager._tools
        print(f"📊 Registered Tools: {len(tools)}")
        for tool_name, tool in tools.items():
            print(f"   🔧 {tool_name}")
            if hasattr(tool, '__doc__') and tool.__doc__:
                doc = tool.__doc__.strip().split('\n')[0]
                print(f"      → {doc[:70]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_query_server_py():
    """query_server.py 테스트"""
    print("\n" + "="*60)
    print("Testing: Query RAG Server (query_server.py)")
    print("="*60 + "\n")
    
    # 이전 임포트 제거
    if 'server' in sys.modules:
        del sys.modules['server']
    
    try:
        # query_server.py 임포트
        import query_server
        mcp = query_server.mcp
        
        print(f"✅ Server Name: {mcp.name}")
        print(f"✅ Server loaded successfully\n")
        
        # 등록된 도구 확인
        tools = mcp._tool_manager._tools
        print(f"📊 Registered Tools: {len(tools)}")
        for tool_name, tool in tools.items():
            print(f"   🔧 {tool_name}")
            if hasattr(tool, '__doc__') and tool.__doc__:
                doc = tool.__doc__.strip().split('\n')[0]
                print(f"      → {doc[:70]}...")
        
        # 데이터베이스 확인
        print(f"\n📁 Database Path: {CFG['DB_PATH']}")
        print(f"   Exists: {os.path.exists(CFG['DB_PATH'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n🚀 Query-Bong 서버 상세 테스트 시작\n")
    
    # query_server.py 테스트
    result = test_query_server_py()
    
    # 결과 요약
    print("\n" + "="*60)
    print("테스트 결과 요약")
    print("="*60)
    print(f"Query-Bong Server: {'✅ PASS' if result else '❌ FAIL'}")
    print("="*60 + "\n")
