export interface AnalyzerSegment {
  songId: string;
  startSec: number;
  endSec: number;
  confidence: number;
  evidence?: Record<string, unknown>;
}

export interface IAudioAnalyzer {
  analyze(
    wavPath: string,
    songs: Array<{
      id: string;
      title: string;
      originalArtist: string;
      lyricsText: string;
      language: string | null;
      metadata: Record<string, unknown> | null;
    }>,
  ): Promise<AnalyzerSegment[]>;
}
