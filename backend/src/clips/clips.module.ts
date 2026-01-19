import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Clip } from '../entities/clip.entity';
import { Video } from '../entities/video.entity';
import { VideoSongSegment } from '../entities/video-song-segment.entity';
import { ClipsController } from './clips.controller';
import { ClipsService } from './clips.service';

@Module({
  imports: [TypeOrmModule.forFeature([Clip, Video, VideoSongSegment])],
  controllers: [ClipsController],
  providers: [ClipsService],
})
export class ClipsModule {}
