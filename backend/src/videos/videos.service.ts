import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Artist } from '../entities/artist.entity';
import { Video } from '../entities/video.entity';
import { fetchYoutubeVideoDetails, parseYoutubeUrl } from '../common/youtube';

export interface IngestResult {
  video?: Video;
  artist?: Artist;
  status: 'ok' | 'invalid_url' | 'artist_not_found' | 'video_not_found' | 'youtube_api_error';
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

    let details;
    try {
      details = await fetchYoutubeVideoDetails(meta.videoId);
    } catch (error) {
      return {
        status: 'youtube_api_error',
        message: error instanceof Error ? error.message : 'YouTube API error',
      };
    }

    if (!details) {
      return { status: 'video_not_found', message: 'Video not found via YouTube API' };
    }

    const artist = await this.artistRepo.findOne({ where: { channelId: details.channelId } });
    if (!artist) {
      return { status: 'artist_not_found', message: 'Artist not registered' };
    }

    const existing = await this.videoRepo.findOne({ where: { youtubeVideoId: meta.videoId } });
    if (existing) {
      const needsUpdate =
        existing.title !== details.title ||
        existing.publishedAt?.toISOString() !== details.publishedAt?.toISOString() ||
        existing.durationSec !== details.durationSec;
      if (needsUpdate) {
        existing.title = details.title;
        existing.publishedAt = details.publishedAt;
        existing.durationSec = details.durationSec;
        await this.videoRepo.save(existing);
      }
      return { status: 'ok', video: existing, artist };
    }

    const video = this.videoRepo.create({
      youtubeVideoId: details.videoId,
      title: details.title,
      artist,
      publishedAt: details.publishedAt,
      durationSec: details.durationSec,
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
