import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Artist } from '../entities/artist.entity';
import { Video } from '../entities/video.entity';
import { parseYoutubeUrl } from '../common/youtube';

export interface IngestResult {
  video?: Video;
  artist?: Artist;
  status: 'ok' | 'invalid_url' | 'artist_not_found';
  message?: string;
}

@Injectable()
export class VideosService {
  constructor(
    @InjectRepository(Video) private readonly videoRepo: Repository<Video>,
    @InjectRepository(Artist) private readonly artistRepo: Repository<Artist>,
  ) {}

  async ingest(youtubeUrl: string): Promise<IngestResult> {
    const meta = parseYoutubeUrl(youtubeUrl);
    if (!meta) {
      return { status: 'invalid_url', message: 'Invalid YouTube URL' };
    }

    if (!meta.channelId) {
      return { status: 'artist_not_found', message: 'ChannelId is required for MVP ingest' };
    }

    const artist = await this.artistRepo.findOne({ where: { channelId: meta.channelId } });
    if (!artist) {
      return { status: 'artist_not_found', message: 'Artist not registered' };
    }

    const existing = await this.videoRepo.findOne({ where: { youtubeVideoId: meta.videoId } });
    if (existing) {
      return { status: 'ok', video: existing, artist };
    }

    const video = this.videoRepo.create({
      youtubeVideoId: meta.videoId,
      title: meta.title ?? 'Unknown title',
      artist,
      status: 'pending',
    });
    await this.videoRepo.save(video);

    return { status: 'ok', video, artist };
  }

  async findSegments(videoId: string) {
    const video = await this.videoRepo.findOne({
      where: { id: videoId },
      relations: ['segments', 'segments.song'],
    });
    return video?.segments ?? [];
  }
}
