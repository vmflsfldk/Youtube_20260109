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
2. YouTube Data API로 채널/메타 조회 후 등록된 아티스트만 분석 가능
3. `/videos/:videoId/analyze` 요청 시 BullMQ job 생성
4. 워커가 오디오 추출 → wav 변환 → 로컬 analyzer API 호출 → 세그먼트 저장
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

> `YOUTUBE_API_KEY`는 필수입니다.

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

> `yt-dlp`, `ffmpeg`가 로컬에 설치되어 있어야 합니다.
> 기본값은 `AUDIO_DOWNLOAD_MODE=ytdlp`입니다. 로컬 파일을 쓰려면 `AUDIO_DOWNLOAD_MODE=local`과 `AUDIO_SOURCE_PATH`를 설정하세요.
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
- YouTube Data API 키가 필요합니다. `.env`에 `YOUTUBE_API_KEY`를 설정하세요.
- 분석 결과는 로컬 analyzer 서비스가 반환합니다.
- 클립은 영상 업로드 없이 URL + start/end 메타만 저장합니다.

## 로컬 analyzer 서비스 기대 스펙
- Endpoint: `POST ${ANALYZER_ENDPOINT}/analyze`
- Request body:
```json
{
  "wavPath": "/tmp/audio.wav",
  "songs": [
    {
      "id": "uuid",
      "title": "song title",
      "originalArtist": "artist",
      "lyricsText": "lyrics",
      "language": "ja",
      "metadata": {}
    }
  ]
}
```
- Response body:
```json
{
  "segments": [
    {
      "songId": "uuid",
      "startSec": 10.5,
      "endSec": 56.2,
      "confidence": 0.82,
      "evidence": {
        "method": "asr+lyrics"
      }
    }
  ]
}
```

## 주요 엔드포인트
- `POST /videos/ingest`
- `POST /videos/:videoId/analyze`
- `GET /analysis/jobs/:jobId`
- `GET /videos/:videoId/segments`
- `POST /clips`
- `GET /clips?videoId=...`
- `POST /artists/seed`
- `POST /songs/seed`
