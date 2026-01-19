import { Controller, Get, Param, Post } from '@nestjs/common';
import { AnalysisService } from './analysis.service';

@Controller()
export class AnalysisController {
  constructor(private readonly analysisService: AnalysisService) {}

  @Post('videos/:videoId/analyze')
  async analyze(@Param('videoId') videoId: string) {
    return this.analysisService.createJob(videoId);
  }

  @Get('analysis/jobs/:jobId')
  async status(@Param('jobId') jobId: string) {
    return this.analysisService.getJob(jobId);
  }
}
