import { fetch } from 'undici';
import { AnalyzerSegment, IAudioAnalyzer } from './IAudioAnalyzer';

export interface AnalyzerSongPayload {
  id: string;
  title: string;
  originalArtist: string;
  lyricsText: string;
  language: string | null;
  metadata: Record<string, unknown> | null;
}

export interface AnalyzerRequest {
  wavPath: string;
  songs: AnalyzerSongPayload[];
}

export interface AnalyzerResponse {
  segments: AnalyzerSegment[];
}

export class HttpAnalyzer implements IAudioAnalyzer {
  constructor(
    private readonly endpoint: string,
    private readonly timeoutMs: number,
  ) {}

  async analyze(wavPath: string, songs: AnalyzerSongPayload[]): Promise<AnalyzerSegment[]> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const response = await fetch(`${this.endpoint}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ wavPath, songs } satisfies AnalyzerRequest),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`Analyzer error ${response.status}`);
      }

      const data = (await response.json()) as AnalyzerResponse;
      return data.segments ?? [];
    } finally {
      clearTimeout(timeout);
    }
  }
}
