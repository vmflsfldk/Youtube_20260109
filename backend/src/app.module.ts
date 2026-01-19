import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { AnalysisModule } from './analysis/analysis.module';
import { ArtistsModule } from './artists/artists.module';
import { ClipsModule } from './clips/clips.module';
import { Video } from './entities/video.entity';
import { Artist } from './entities/artist.entity';
import { Song } from './entities/song.entity';
import { AnalysisJob } from './entities/analysis-job.entity';
import { VideoSongSegment } from './entities/video-song-segment.entity';
import { Clip } from './entities/clip.entity';
import { VideosModule } from './videos/videos.module';

@Module({
  imports: [
    TypeOrmModule.forRoot({
      type: 'postgres',
      url: process.env.DATABASE_URL,
      entities: [Artist, Video, Song, AnalysisJob, VideoSongSegment, Clip],
      synchronize: false,
    }),
    VideosModule,
    AnalysisModule,
    ClipsModule,
    ArtistsModule,
  ],
})
export class AppModule {}
