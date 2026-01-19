import { AnalyzerSegment, IAudioAnalyzer } from './IAudioAnalyzer';

export class DummyAnalyzer implements IAudioAnalyzer {
  constructor(private readonly songId: string) {}

  async analyze(wavPath: string): Promise<AnalyzerSegment[]> {
    return [
      {
        songId: this.songId,
        startSec: 30,
        endSec: 120,
        confidence: 0.72,
        evidence: { note: 'Dummy segment', wavPath },
      },
      {
        songId: this.songId,
        startSec: 300,
        endSec: 420,
        confidence: 0.64,
        evidence: { note: 'Dummy segment 2', wavPath },
      },
    ];
  }
}
