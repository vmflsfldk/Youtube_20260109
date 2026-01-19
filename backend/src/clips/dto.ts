import { IsIn, IsNumber, IsOptional, IsString } from 'class-validator';

export class CreateClipDto {
  @IsString()
  videoId!: string;

  @IsOptional()
  @IsString()
  segmentId?: string;

  @IsOptional()
  @IsString()
  userId?: string;

  @IsNumber()
  startSec!: number;

  @IsNumber()
  endSec!: number;

  @IsString()
  title!: string;

  @IsIn(['public', 'unlisted', 'private'])
  visibility!: string;
}
