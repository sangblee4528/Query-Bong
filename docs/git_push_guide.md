# Git 업데이트 가이드

Query-Bong 프로젝트의 변경 사항을 GitHub에 업로드하는 방법입니다.

## 1. 상태 확인 및 파일 추가
현재 변경된 파일들을 확인하고 스테이징(Staging) 영역에 추가합니다.

```bash
# 변경 상태 확인
git status

# 변경된 모든 파일 추가 (수정 및 신규 파일)
git add .
```

## 2. 커밋 (Commit)
변경 사항에 대한 설명(메시지)을 적어 저장합니다.

```bash
# 예시: 오프라인 실행 버그 수정
git commit -m "Fix: query_mcp_server.py offline execution error and registration docs"
```

## 3. 푸시 (Push)
로컬 저장소의 내용을 원격 GitHub 저장소로 업로드합니다.

```bash
# 메인 브랜치로 푸시
git push origin main
```

---

### [참고] 자주 사용하는 명령어 요약

*   `git status`: 현재 어떤 파일이 바뀌었는지 봅니다.
*   `git diff`: 정확히 코드가 어떻게 바뀌었는지 봅니다.
*   `git log`: 과거 커밋 내역을 확인합니다.
