import { spawn } from 'node:child_process';
import { promises as fs } from 'node:fs';
import os from 'node:os';
import path from 'node:path';

export interface DownloadResult {
  audioPath: string;
  cleanup?: () => Promise<void>;
}

export async function downloadAudio(youtubeVideoId: string): Promise<DownloadResult> {
  const mode = process.env.AUDIO_DOWNLOAD_MODE ?? 'ytdlp';
  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'vtuber-audio-'));
  const cleanup = async () => {
    await fs.rm(tempDir, { recursive: true, force: true });
  };

  if (mode === 'local') {
    const sourcePath = process.env.AUDIO_SOURCE_PATH;
    if (!sourcePath) {
      throw new Error('AUDIO_SOURCE_PATH is required when AUDIO_DOWNLOAD_MODE=local');
    }
    const outputPath = path.join(tempDir, path.basename(sourcePath));
    await fs.copyFile(sourcePath, outputPath);
    return { audioPath: outputPath, cleanup };
  }

  const outputPath = path.join(tempDir, `${youtubeVideoId}.m4a`);
  const ytdlpPath = process.env.YTDLP_PATH ?? 'yt-dlp';

  await new Promise<void>((resolve, reject) => {
    const processHandle = spawn(ytdlpPath, [
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
    cleanup,
  };
}
