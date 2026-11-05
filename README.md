# 📚 대학 강의 Ucheck 출석체크 & 시스템 모니터링 디스코드 봇

대학 정기 강의 시간에 맞춰 **Ucheck 전자출결 알림 DM**을 발송하고, 봇 프로세스 및 시스템 헬스를 모니터링하는 디스코드 봇입니다.

---

## ✨ 주요 기능

### 1. 🔔 스마트 강의 출석 알림
* `schedules.json`에 등록된 요일 및 시간(CronTrigger)에 맞춰 자동으로 사용자에게 임베드 DM 발송.
* **[🌐 Ucheck 전자출결 열기]** 원클릭 바로가기 버튼 제공.
* **[✅ 출석체크 완료]** 인터랙티브 버튼으로 출석 확인 완료 상태 토글.

### 2. 📅 동적 시간표 관리 슬래시 커맨드
* `/시간표 오늘`: 당일 남은 강의 일정 목록 조회.
* `/시간표 전체`: 화~금 전체 주간 강의 시간표 한눈에 보기.
* `/시간표 추가`: 봇 재부팅 없이 디스코드 내에서 실시간 과목 추가 및 스케줄러 동기화.
* `/시간표 삭제`: ID(`tue_01` 등)로 특정 강의 일정 삭제.

### 3. 📊 시스템 리소스 진단 & 6일 업타임 경고
* `/상태`: 봇 RAM 사용량(MB), CPU 부하(%), 호스트 전체 메모리, 웹소켓 핑(ms) 및 업타임 실시간 출력.
* `/test`: 스케줄러 테스트용 1분 뒤 알림 예약.
* 6일 이상 연속 가동 시 패널 재시작 권장 알림 발송.

---

## 🛠️ 프로젝트 구조

```
bb/
├── core/
│   ├── config.py         # .env 및 config.json 설정 관리
│   └── scheduler.py      # APScheduler 및 시간표 동적 관리자
├── cogs/
│   ├── attendance.py     # 출석 알림 및 시간표 명령어
│   └── monitoring.py     # 시스템 헬스체크 및 업타임 모니터링
├── main.py               # 봇 진입점 (Cog Loader)
├── config.json           # 봇 설정
├── schedules.json        # 강의 일정 데이터
├── requirements.txt      # 의존성 목록
├── .env.example          # 환경변수 템플릿
└── .gitignore            # 보안 및 가상환경 필터링
```

---

## 🚀 빠른 시작 (Quick Start)

### 1. 의존성 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정
`.env.example` 파일을 복사하여 `.env`를 생성하고 본인의 정보를 입력합니다:
```env
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_TARGET_USER_ID=your_discord_user_id_here
```

### 3. 봇 실행
```bash
python main.py
```
