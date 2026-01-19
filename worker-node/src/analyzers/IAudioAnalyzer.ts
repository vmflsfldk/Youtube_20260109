export interface AnalyzerSegment {
  songId: string;
  startSec: number;
  endSec: number;
  confidence: number;
  evidence?: Record<string, unknown>;
}

export interface IAudioAnalyzer {
  analyze(wavPath: string): Promise<AnalyzerSegment[]>;
}
