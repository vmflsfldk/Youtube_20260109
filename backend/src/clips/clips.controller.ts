import { Body, Controller, Get, Post, Query } from '@nestjs/common';
import { CreateClipDto } from './dto';
import { ClipsService } from './clips.service';

@Controller('clips')
export class ClipsController {
  constructor(private readonly clipsService: ClipsService) {}

  @Post()
  async create(@Body() dto: CreateClipDto) {
    return this.clipsService.create(dto);
  }

  @Get()
  async list(@Query('videoId') videoId: string) {
    return this.clipsService.list(videoId);
  }
}
