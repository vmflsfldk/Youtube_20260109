import {
  Column,
  CreateDateColumn,
  Entity,
  ManyToOne,
  PrimaryGeneratedColumn,
  UpdateDateColumn,
} from 'typeorm';
import { Video } from './video.entity';

@Entity({ name: 'analysis_jobs' })
export class AnalysisJob {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @ManyToOne(() => Video)
  video!: Video;

  @Column({ default: 'queued' })
  status!: string;

  @Column({ default: 0 })
  progress!: number;

  @Column({ name: 'error_message', type: 'text', nullable: true })
  errorMessage!: string | null;

  @CreateDateColumn({ name: 'created_at' })
  createdAt!: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt!: Date;
}
