import 'dotenv/config';
import { Worker } from 'bullmq';
import { HttpAnalyzer } from './analyzers/HttpAnalyzer';
import { downloadAudio } from './audio/downloadAudio';
import { convertToWav } from './audio/ffmpeg';
import { insertSegments, listSongs, updateJobStatus, updateVideoStatus } from './db/client';

const connection = process.env.REDIS_URL ?? 'redis://localhost:6379';
const queueName = process.env.ANALYZE_QUEUE ?? 'analyze-video';
const concurrency = Number(process.env.WORKER_CONCURRENCY ?? '2');
const analyzerEndpoint = process.env.ANALYZER_ENDPOINT ?? 'http://localhost:7001';
const analyzerTimeoutMs = Number(process.env.ANALYZER_TIMEOUT_MS ?? '120000');

const worker = new Worker(
  queueName,
  async (job) => {
    const { videoId, youtubeVideoId, jobId } = job.data as {
      videoId: string;
      youtubeVideoId: string;
      jobId: string;
    };

    await updateJobStatus(jobId, 'running', 5);

    const songs = await listSongs();
    if (!songs.length) {
      await updateJobStatus(jobId, 'failed', 100, 'No songs seeded in database');
      await updateVideoStatus(videoId, 'failed');
      return;
    }

    const analyzer = new HttpAnalyzer(analyzerEndpoint, analyzerTimeoutMs);

    const downloadResult = await downloadAudio(youtubeVideoId);
    await updateJobStatus(jobId, 'running', 25);

    const wavPath = await convertToWav(downloadResult.audioPath);
    await updateJobStatus(jobId, 'running', 50);

    const segments = await analyzer.analyze(wavPath, songs);
    await updateJobStatus(jobId, 'running', 80);

    await insertSegments(videoId, segments);
    await updateJobStatus(jobId, 'done', 100);
    await updateVideoStatus(videoId, 'analyzed');

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
  const { jobId, videoId } = job.data as { jobId: string; videoId: string };
  await updateJobStatus(jobId, 'failed', 100, err.message);
  await updateVideoStatus(videoId, 'failed');
});

worker.on('ready', () => {
  console.log(`Worker ready on queue ${queueName}`);
});
