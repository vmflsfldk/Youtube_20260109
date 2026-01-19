import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Queue } from 'bullmq';
import { Repository } from 'typeorm';
import { AnalysisJob } from '../entities/analysis-job.entity';
import { Video } from '../entities/video.entity';

@Injectable()
export class AnalysisService {
  private readonly queue: Queue;

  constructor(
    @InjectRepository(AnalysisJob) private readonly jobRepo: Repository<AnalysisJob>,
    @InjectRepository(Video) private readonly videoRepo: Repository<Video>,
  ) {
    const connection = process.env.REDIS_URL ?? 'redis://localhost:6379';
    const queueName = process.env.ANALYZE_QUEUE ?? 'analyze-video';
    this.queue = new Queue(queueName, { connection });
  }

  async createJob(videoId: string) {
    const video = await this.videoRepo.findOne({ where: { id: videoId } });
    if (!video) {
      return { status: 'not_found', message: 'Video not found' };
    }

    const job = this.jobRepo.create({
      video,
      status: 'queued',
      progress: 0,
    });
    await this.jobRepo.save(job);

    await this.queue.add('analyze', {
      jobId: job.id,
      videoId: video.id,
      youtubeVideoId: video.youtubeVideoId,
    });

    return { status: 'queued', jobId: job.id };
  }

  async getJob(jobId: string) {
    return this.jobRepo.findOne({
      where: { id: jobId },
      relations: ['video'],
    });
  }
}
