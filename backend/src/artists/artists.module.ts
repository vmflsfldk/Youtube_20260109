import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Artist } from '../entities/artist.entity';
import { Song } from '../entities/song.entity';
import { ArtistsController } from './artists.controller';
import { ArtistsService } from './artists.service';

@Module({
  imports: [TypeOrmModule.forFeature([Artist, Song])],
  controllers: [ArtistsController],
  providers: [ArtistsService],
})
export class ArtistsModule {}
