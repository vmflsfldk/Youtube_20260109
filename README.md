# Youtube_202601091. 프로젝트 개요
1.1 목적

본 프로젝트는 유튜브 채널(우타와꾸 방송 등)의 모든 영상을 대상으로 음성 데이터를 수집·분석하여,
방송 내에서 노래가 불린 구간을 자동 탐지하고,
각 구간에 대해 어떤 노래가 불렸는지 및 해당 노래의 원곡자를 식별하는 시스템을 구축하는 것을 목표로 한다.

1.2 핵심 특징

입력 단위: 유튜브 채널 URL

처리 대상: 해당 채널의 모든 영상 (라이브 영상은 별도 수집 가능)

판별 대상:

노래 구간 시작/종료 시점

곡 제목

원곡자(Original Artist)

방송 스트리머는 식별 대상이 아님

사용자 수정 데이터를 활용한 재귀개선(Recursive Improvement) 구조 포함

2. 최종 출력 정의
{
  "channel_id": "UCxxxx",
  "video_id": "abcd1234",
  "results": [
    {
      "start_time": 125.32,
      "end_time": 312.87,
      "song_title": "노래 제목",
      "original_artist": "원곡자",
      "confidence": 0.94
    }
  ]
}

3. 시스템 전체 아키텍처
[YouTube Channel URL]
        ↓
[채널 영상 목록 수집]
        ↓
[각 영상 오디오 추출]
        ↓
[노래 구간 탐지 (≥60초)]
        ↓
(옵션) [보컬 분리]
        ↓
[오디오 기반 곡 후보 검색]
        ↓
[가사 기반 재검증/정렬]
        ↓
[곡 확정]
        ↓
[원곡자 메타 매핑]
        ↓
[DB 저장 & 결과 제공]

4. 파이프라인 상세 설계
4.1 유튜브 채널 크롤링

입력: 유튜브 채널 URL

처리:

채널 ID 추출

채널 내 전체 영상 목록 수집

신규 영상만 증분 처리 가능

출력: video_id 목록

4.2 오디오 추출

영상별 오디오 추출

포맷 표준화:

WAV

16kHz ~ 48kHz

오디오는 내부 처리용으로만 사용

4.2.1 라이브 영상 음성 데이터 수집

채널 URL을 입력하면 해당 채널의 모든 라이브 영상(스트리밍/아카이브)에서 오디오를 추출하여
`audio/` 디렉터리에 저장한다. 파이프라인의 기본 CLI 실행은 라이브 영상 오디오 수집 결과를 출력한다.

출력 예시:
{
  "requested_at": "2025-01-01T00:00:00+00:00",
  "channel_url": "https://www.youtube.com/channel/UCxxxx",
  "outputs": [
    {
      "channel_id": "UCxxxx",
      "video_id": "live01",
      "title": "Sample Live Stream 1",
      "audio_path": "audio/live01.wav",
      "sample_rate": 44100,
      "is_live": true
    }
  ]
}

4.3 노래 구간 탐지 (Song Segment Detection)
목적

방송 전체에서 실제로 노래가 불린 구간만 추출하여 연산 비용 감소 및 정확도 향상

처리 방식

Speech / Music 분류

Singing Voice Detection

연속 구간 병합

60초 미만 구간 제거

출력
[
  { "start": 120.0, "end": 310.5 },
  { "start": 480.2, "end": 650.9 }
]

4.4 (선택) 보컬 분리

반주 제거 후 vocal stem 생성

ASR 및 오디오 임베딩 정확도 향상

MVP 단계에서는 옵션

4.5 곡 후보 검색 (핵심 단계)
4.5.1 오디오 기반 매칭 (Primary)

노래 구간 오디오 → 임베딩/핑거프린트 추출

사전 구축된 원곡 음원 DB와 유사도 비교

Top-K 후보 선정

장점

커버곡 환경에 매우 강함

가사 변경/애드립에도 안정적

4.5.2 가사 기반 매칭 (Secondary)

노래 구간 ASR 수행

가사 DB와 퍼지 매칭

용도:

오디오 후보 재랭킹

구간 정밀화

4.6 곡 확정 및 구간 정밀화

오디오 유사도 + 가사 정렬 점수 종합

최종 곡 1개 확정

가사-전사 시퀀스 정렬로 정확한 start/end 보정

4.7 원곡자 매핑

곡 DB 기준으로 원곡자 매핑

방송에서 부른 사람(스트리머)은 고려하지 않음

5. 재귀개선(Recursive Improvement) 구조
5.1 개선 데이터 수집

사용자가 결과 수정 가능

저장 항목:

잘못된 곡

정답 곡

실제 구간

5.2 개선 대상
영역	개선 내용
구간 탐지	노래/비노래 오탐 감소
곡 매칭	Top-K 정확도
ASR	도메인 적응
메타	표기/별칭 정규화
5.3 개선 루프
결과 생성 → 사용자 검수 → 데이터 축적 → 주기적 재학습/룰 개선

6. DB 스키마 (Postgres / D1 공용)
6.1 channels
CREATE TABLE channels (
  channel_id TEXT PRIMARY KEY,
  channel_url TEXT,
  channel_name TEXT,
  last_crawled_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

6.2 videos
CREATE TABLE videos (
  video_id TEXT PRIMARY KEY,
  channel_id TEXT,
  title TEXT,
  duration_sec INTEGER,
  published_at TIMESTAMP,
  processed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

6.3 audio_files
CREATE TABLE audio_files (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id TEXT,
  file_path TEXT,
  sample_rate INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

6.4 song_segments
CREATE TABLE song_segments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id TEXT,
  start_sec REAL,
  end_sec REAL,
  duration_sec REAL,
  confidence REAL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

6.5 songs
CREATE TABLE songs (
  song_id TEXT PRIMARY KEY,
  title TEXT,
  original_artist TEXT,
  language TEXT,
  title_aliases TEXT,
  artist_aliases TEXT
);

6.6 song_matches
CREATE TABLE song_matches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  segment_id INTEGER,
  song_id TEXT,
  match_score REAL,
  method TEXT,
  confirmed BOOLEAN DEFAULT FALSE
);

6.7 lyrics (선택)
CREATE TABLE lyrics (
  song_id TEXT PRIMARY KEY,
  lyrics TEXT
);

7. MVP 기술 스택
Backend / Orchestration

NestJS 또는 Cloudflare Workers

AI / Processing

Python (Batch Worker)

Frontend

React + Vite

Database

Postgres (권장)

D1 (경량)

8. 디렉토리 구조
project-root/
├─ api/
├─ worker/
│  ├─ crawler/
│  ├─ audio/
│  ├─ segment/
│  ├─ asr/
│  ├─ matching/
│  └─ pipeline.py
├─ frontend/
└─ docs/

9. 실행 방법
아래 명령은 repo 루트에서 실행한다.

1) 파이프라인 실행
```bash
python -m worker.pipeline
```
실행 후 프롬프트에서 유튜브 채널 URL과 파이프라인 단계(1. 크롤링 / 2. 분석)를 선택하면 JSON 결과가 출력된다.
1은 라이브 영상 오디오만 수집하며, 2는 전체 분석 파이프라인을 실행해 매칭 결과를 반환한다.

2) 파이프라인 설정 변경 (옵션)
`worker/pipeline.py`의 `PipelineConfig`에서 샘플레이트, 보컬 분리, 최소 구간 길이 등을 조정할 수 있다.

10. 사용 오픈소스 후보
단계	후보
채널 수집	yt-dlp, YouTube Data API
오디오	ffmpeg, librosa
구간 탐지	pyannote.audio, inaSpeechSegmenter
보컬 분리	Demucs, Spleeter
ASR	Whisper, faster-whisper
오디오 매칭	Chromaprint, OpenL3, CLAP
가사 매칭	RapidFuzz, Elasticsearch
11. PoC 최소 코드 흐름
def process_channel(channel_url):
    channel_id = fetch_channel_id(channel_url)
    videos = fetch_videos(channel_id)

    for video in videos:
        audio = extract_audio(video)
        segments = detect_song_segments(audio)

        for seg in segments:
            if seg.duration < 60:
                continue

            candidates = audio_match(seg)
            best = rerank_with_lyrics(seg, candidates)

            save_result(video, seg, best)

12. MVP 성공 기준

채널 단위 자동 수집

노래 구간 정확 탐지

Top-1 곡 정확도 체감 ≥ 70%

원곡자 자동 태깅 100%

13. 핵심 요약

본 시스템은 단일 모델이 아닌 파이프라인 시스템

가사보다 오디오 기반 매칭이 핵심

채널 단위 처리로 자동화 극대화

사용자 피드백 기반 재귀개선으로 장기 정확도 상승
