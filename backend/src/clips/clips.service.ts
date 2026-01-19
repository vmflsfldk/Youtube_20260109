import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Clip } from '../entities/clip.entity';
import { Video } from '../entities/video.entity';
import { VideoSongSegment } from '../entities/video-song-segment.entity';
import { CreateClipDto } from './dto';

@Injectable()
export class ClipsService {
  constructor(
    @InjectRepository(Clip) private readonly clipRepo: Repository<Clip>,
    @InjectRepository(Video) private readonly videoRepo: Repository<Video>,
    @InjectRepository(VideoSongSegment) private readonly segmentRepo: Repository<VideoSongSegment>,
  ) {}

  async create(dto: CreateClipDto) {
    const video = await this.videoRepo.findOne({ where: { id: dto.videoId } });
    if (!video) {
      return { status: 'not_found', message: 'Video not found' };
    }

    const segment = dto.segmentId
      ? await this.segmentRepo.findOne({ where: { id: dto.segmentId } })
      : null;

    const clip = this.clipRepo.create({
      video,
      segment,
      userId: dto.userId ?? null,
      startSec: dto.startSec,
      endSec: dto.endSec,
      title: dto.title,
      visibility: dto.visibility,
    });

    await this.clipRepo.save(clip);

    return clip;
  }

  async list(videoId: string) {
    return this.clipRepo.find({
      where: { video: { id: videoId } },
      relations: ['segment', 'video'],
      order: { createdAt: 'DESC' },
    });
  }
}
