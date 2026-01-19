import React, { useState } from 'react';
import { AnalysisJob, ingestVideo, createAnalysis, getJob } from '../api/client';
import ProgressBar from '../components/ProgressBar';

interface HomeProps {
  onVideoReady: (videoId: string, title: string) => void;
}

export default function Home({ onVideoReady }: HomeProps) {
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleIngest = async () => {
    setLoading(true);
    setStatusMessage(null);
    try {
      const result = await ingestVideo(youtubeUrl);
      if (result.status !== 'ok' || !result.video) {
        setStatusMessage(result.message ?? '아티스트가 등록되어 있지 않습니다.');
        return;
      }
      onVideoReady(result.video.id, result.video.title);
      const analysis = await createAnalysis(result.video.id);
      const jobState = await getJob(analysis.jobId);
      setJob(jobState);
    } catch (error) {
      setStatusMessage('요청 실패: URL 또는 서버 상태를 확인하세요.');
    } finally {
      setLoading(false);
    }
  };

  const refreshJob = async () => {
    if (!job) {
      return;
    }
    const data = await getJob(job.id);
    setJob(data);
  };

  return (
    <div className="card">
      <h2>유튜브 링크 입력</h2>
      <label>유튜브 URL (channelId 쿼리 포함 권장)</label>
      <input
        type="text"
        value={youtubeUrl}
        onChange={(event) => setYoutubeUrl(event.target.value)}
        placeholder="https://www.youtube.com/watch?v=...&channelId=UCxxxx"
      />
      <button onClick={handleIngest} disabled={loading}>
        분석 시작
      </button>
      {statusMessage && <p className="notice">{statusMessage}</p>}

      {job && (
        <div className="status">
          <ProgressBar progress={job.progress} />
          <span>{job.status}</span>
          <button className="secondary" onClick={refreshJob}>
            상태 새로고침
          </button>
        </div>
      )}
    </div>
  );
}
