import { spawn } from 'node:child_process';
import { promises as fs } from 'node:fs';
import path from 'node:path';

export interface DownloadResult {
  audioPath: string;
  cleanup?: () => Promise<void>;
}

export async function downloadAudio(youtubeVideoId: string): Promise<DownloadResult> {
  const mode = process.env.AUDIO_DOWNLOAD_MODE ?? 'mock';
  if (mode === 'mock') {
    const mockPath = process.env.MOCK_AUDIO_PATH ?? './assets/mock.wav';
    return { audioPath: mockPath };
  }

  const outputDir = path.resolve('tmp');
  await fs.mkdir(outputDir, { recursive: true });
  const outputPath = path.join(outputDir, `${youtubeVideoId}.m4a`);

  await new Promise<void>((resolve, reject) => {
    const processHandle = spawn('yt-dlp', [
      `https://www.youtube.com/watch?v=${youtubeVideoId}`,
      '-f',
      'bestaudio',
      '-o',
      outputPath,
    ]);

    processHandle.on('error', reject);
    processHandle.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`yt-dlp exited with code ${code}`));
      }
    });
  });

  return {
    audioPath: outputPath,
    cleanup: async () => {
      await fs.unlink(outputPath).catch(() => undefined);
    },
  };
}
