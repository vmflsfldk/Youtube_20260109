import { IsString, IsUrl } from 'class-validator';

export class IngestVideoDto {
  @IsString()
  @IsUrl()
  youtubeUrl!: string;
}

export class AnalyzeVideoDto {
  @IsString()
  videoId!: string;
}
