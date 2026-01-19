import { Body, Controller, Post } from '@nestjs/common';
import { SeedArtistDto, SeedSongDto } from './dto';
import { ArtistsService } from './artists.service';

@Controller()
export class ArtistsController {
  constructor(private readonly artistsService: ArtistsService) {}

  @Post('artists/seed')
  async seedArtists(@Body() payload: SeedArtistDto[]) {
    return this.artistsService.seedArtists(payload);
  }

  @Post('songs/seed')
  async seedSongs(@Body() payload: SeedSongDto[]) {
    return this.artistsService.seedSongs(payload);
  }
}
