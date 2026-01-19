import 'dotenv/config';
import { Worker } from 'bullmq';
import { DummyAnalyzer } from './analyzers/DummyAnalyzer';
import { downloadAudio } from './audio/downloadAudio';
import { convertToWav } from './audio/ffmpeg';
import { getFallbackSongId, insertSegments, updateJobStatus } from './db/client';

const connection = process.env.REDIS_URL ?? 'redis://localhost:6379';
const queueName = process.env.ANALYZE_QUEUE ?? 'analyze-video';
const concurrency = Number(process.env.WORKER_CONCURRENCY ?? '2');

const worker = new Worker(
  queueName,
  async (job) => {
    const { videoId, youtubeVideoId, jobId } = job.data as {
      videoId: string;
      youtubeVideoId: string;
      jobId: string;
    };

    await updateJobStatus(jobId, 'running', 5);

    const fallbackSongId = await getFallbackSongId();
    if (!fallbackSongId) {
      await updateJobStatus(jobId, 'failed', 100, 'No songs seeded in database');
      return;
    }

    const analyzer = new DummyAnalyzer(fallbackSongId);

    const downloadResult = await downloadAudio(youtubeVideoId);
    await updateJobStatus(jobId, 'running', 25);

    const wavPath = await convertToWav(downloadResult.audioPath);
    await updateJobStatus(jobId, 'running', 50);

    const segments = await analyzer.analyze(wavPath);
    await updateJobStatus(jobId, 'running', 80);

    await insertSegments(videoId, segments);
    await updateJobStatus(jobId, 'done', 100);

    if (downloadResult.cleanup) {
      await downloadResult.cleanup();
    }
  },
  { connection, concurrency },
);

worker.on('failed', async (job, err) => {
  if (!job) {
    return;
  }
  const { jobId } = job.data as { jobId: string };
  await updateJobStatus(jobId, 'failed', 100, err.message);
});

worker.on('ready', () => {
  console.log(`Worker ready on queue ${queueName}`);
});
