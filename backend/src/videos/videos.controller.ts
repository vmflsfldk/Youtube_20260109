import { Body, Controller, Get, Param, Post } from '@nestjs/common';
import { IngestVideoDto } from './dto';
import { VideosService } from './videos.service';

@Controller('videos')
export class VideosController {
  constructor(private readonly videosService: VideosService) {}

  @Post('ingest')
  async ingest(@Body() dto: IngestVideoDto) {
    return this.videosService.ingest(dto.youtubeUrl);
  }

  @Get(':videoId/segments')
  async segments(@Param('videoId') videoId: string) {
    return this.videosService.findSegments(videoId);
  }
}
