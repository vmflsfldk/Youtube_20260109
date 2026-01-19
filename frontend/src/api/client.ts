export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:3000';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  });

  if (!res.ok) {
    throw new Error(`API error ${res.status}`);
  }

  return res.json() as Promise<T>;
}

export interface IngestResult {
  status: 'ok' | 'invalid_url' | 'artist_not_found' | 'video_not_found' | 'youtube_api_error';
  message?: string;
  video?: { id: string; youtubeVideoId: string; title: string };
  artist?: { id: string; name: string; channelId: string };
}

export interface AnalysisJob {
  id: string;
  status: string;
  progress: number;
  errorMessage?: string | null;
}

export interface Segment {
  id: string;
  startSec: number;
  endSec: number;
  confidence: number;
  song: { title: string; originalArtist: string };
}

export interface Clip {
  id: string;
  title: string;
  startSec: number;
  endSec: number;
  visibility: string;
}

export function ingestVideo(youtubeUrl: string) {
  return request<IngestResult>('/videos/ingest', {
    method: 'POST',
    body: JSON.stringify({ youtubeUrl }),
  });
}

export function createAnalysis(videoId: string) {
  return request<{ status: string; jobId: string }>('/videos/' + videoId + '/analyze', {
    method: 'POST',
  });
}

export function getJob(jobId: string) {
  return request<AnalysisJob>(`/analysis/jobs/${jobId}`);
}

export function getSegments(videoId: string) {
  return request<Segment[]>(`/videos/${videoId}/segments`);
}

export function createClip(payload: {
  videoId: string;
  segmentId?: string;
  userId?: string;
  startSec: number;
  endSec: number;
  title: string;
  visibility: string;
}) {
  return request<Clip>('/clips', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function listClips(videoId: string) {
  return request<Clip[]>(`/clips?videoId=${encodeURIComponent(videoId)}`);
}
