# VTuber Live Analyzer MVP

VTuber 라이브 영상에서 노래 구간을 탐지하고, 곡/원곡자를 매칭한 결과를 타임라인으로 제공하는 MVP입니다. 사용자는 유튜브 URL을 입력해 분석 작업을 생성하고, 완료된 세그먼트를 기반으로 클립 메타(원본 URL + 구간 시간)만 저장합니다.

## 구성 요소
- **Backend**: NestJS + TypeORM + PostgreSQL + BullMQ
- **Worker**: Node.js(BullMQ consumer) + ffmpeg + 플러그형 오디오 분석기
- **Frontend**: Vite + React + TypeScript
- **DevOps**: docker-compose (Postgres/Redis)

## 디렉토리 구조
```
.
├── backend
│   ├── migrations
│   └── src
├── frontend
│   └── src
├── worker-node
│   └── src
├── docker-compose.yml
├── .env.example
└── README.md
```

## 핵심 플로우
1. 프론트에서 유튜브 URL 입력 → `/videos/ingest`
2. 등록된 아티스트(channelId)만 영상 등록/분석 가능
3. `/videos/:videoId/analyze` 요청 시 BullMQ job 생성
4. 워커가 오디오 추출 → wav 변환 → 더미 analyzer 분석 → 세그먼트 저장
5. 프론트에서 `/analysis/jobs/:jobId`, `/videos/:videoId/segments`로 상태/결과 표시
6. 세그먼트 선택 후 클립 메타 `/clips` 저장

## 로컬 실행 가이드

### 1) 인프라 실행
```bash
docker-compose up -d
```

### 2) 환경 변수
```bash
cp .env.example .env
```

### 3) DB 마이그레이션
```bash
psql "$DATABASE_URL" -f backend/migrations/001_init.sql
```

### 4) 백엔드 실행
```bash
cd backend
npm install
npm run start:dev
```

### 5) 워커 실행
```bash
cd worker-node
npm install
npm run start
```

> `AUDIO_DOWNLOAD_MODE=mock`을 유지하면 `worker-node/assets/mock.wav`를 사용합니다. 실제 다운로드는 `AUDIO_DOWNLOAD_MODE=yt-dlp`로 전환하세요.
> 워커는 최초 실행 전에 `songs` 시드가 필요합니다.

### 6) 프론트 실행
```bash
cd frontend
npm install
npm run dev
```

### 7) 시드 데이터 예시
```bash
curl -X POST http://localhost:3000/artists/seed \\\n  -H 'Content-Type: application/json' \\\n  -d '[{\"channelId\":\"UCxxxx\",\"name\":\"Sample Artist\"}]'

curl -X POST http://localhost:3000/songs/seed \\\n  -H 'Content-Type: application/json' \\\n  -d '[{\"title\":\"Sample Song\",\"originalArtist\":\"Original Artist\",\"lyricsText\":\"La la la\"}]'
```

## MVP 주의사항
- YouTube Data API 연동 전까지 **영상 URL에 channelId 쿼리를 추가**해야 합니다.
  - 예: `https://www.youtube.com/watch?v=VIDEO_ID&channelId=UCxxxx`
- 분석 결과는 더미 analyzer가 생성한 고정 세그먼트입니다.
- 클립은 영상 업로드 없이 URL + start/end 메타만 저장합니다.

## 주요 엔드포인트
- `POST /videos/ingest`
- `POST /videos/:videoId/analyze`
- `GET /analysis/jobs/:jobId`
- `GET /videos/:videoId/segments`
- `POST /clips`
- `GET /clips?videoId=...`
- `POST /artists/seed`
- `POST /songs/seed`
