import { spawn } from 'node:child_process';
import path from 'node:path';

export async function convertToWav(inputPath: string): Promise<string> {
  if (inputPath.endsWith('.wav')) {
    return inputPath;
  }

  const outputDir = path.dirname(inputPath);
  const outputPath = path.join(outputDir, `${path.basename(inputPath, path.extname(inputPath))}.wav`);

  const ffmpegPath = process.env.FFMPEG_PATH ?? 'ffmpeg';

  await new Promise<void>((resolve, reject) => {
    const processHandle = spawn(ffmpegPath, ['-i', inputPath, '-ar', '44100', '-ac', '2', outputPath]);
    processHandle.on('error', reject);
    processHandle.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`ffmpeg exited with code ${code}`));
      }
    });
  });

  return outputPath;
}
