import { IsArray, IsOptional, IsString } from 'class-validator';

export class SeedArtistDto {
  @IsString()
  channelId!: string;

  @IsString()
  name!: string;

  @IsOptional()
  @IsArray()
  aliases?: string[];
}

export class SeedSongDto {
  @IsString()
  title!: string;

  @IsString()
  originalArtist!: string;

  @IsString()
  lyricsText!: string;

  @IsOptional()
  @IsString()
  language?: string;
}
