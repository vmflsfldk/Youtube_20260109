import { Column, CreateDateColumn, Entity, ManyToOne, PrimaryGeneratedColumn } from 'typeorm';
import { Video } from './video.entity';
import { VideoSongSegment } from './video-song-segment.entity';

@Entity({ name: 'clips' })
export class Clip {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @ManyToOne(() => Video, (video) => video.clips)
  video!: Video;

  @ManyToOne(() => VideoSongSegment, { nullable: true })
  segment!: VideoSongSegment | null;

  @Column({ name: 'user_id', nullable: true })
  userId!: string | null;

  @Column({ name: 'start_sec', type: 'float' })
  startSec!: number;

  @Column({ name: 'end_sec', type: 'float' })
  endSec!: number;

  @Column()
  title!: string;

  @Column({ default: 'public' })
  visibility!: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt!: Date;
}
