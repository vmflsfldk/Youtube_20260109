import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Artist } from '../entities/artist.entity';
import { Song } from '../entities/song.entity';
import { SeedArtistDto, SeedSongDto } from './dto';

@Injectable()
export class ArtistsService {
  constructor(
    @InjectRepository(Artist) private readonly artistRepo: Repository<Artist>,
    @InjectRepository(Song) private readonly songRepo: Repository<Song>,
  ) {}

  async seedArtists(payload: SeedArtistDto[]) {
    const artists = payload.map((item) =>
      this.artistRepo.create({
        channelId: item.channelId,
        name: item.name,
        aliases: item.aliases ?? null,
      }),
    );
    return this.artistRepo.save(artists);
  }

  async seedSongs(payload: SeedSongDto[]) {
    const songs = payload.map((item) =>
      this.songRepo.create({
        title: item.title,
        originalArtist: item.originalArtist,
        lyricsText: item.lyricsText,
        language: item.language ?? null,
      }),
    );
    return this.songRepo.save(songs);
  }
}
