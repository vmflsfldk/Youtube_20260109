import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { AnalysisJob } from '../entities/analysis-job.entity';
import { Video } from '../entities/video.entity';
import { AnalysisController } from './analysis.controller';
import { AnalysisService } from './analysis.service';

@Module({
  imports: [TypeOrmModule.forFeature([AnalysisJob, Video])],
  controllers: [AnalysisController],
  providers: [AnalysisService],
})
export class AnalysisModule {}
