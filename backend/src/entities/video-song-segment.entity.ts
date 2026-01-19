import { Column, Entity, ManyToOne, PrimaryGeneratedColumn } from 'typeorm';
import { Video } from './video.entity';
import { Song } from './song.entity';

@Entity({ name: 'video_song_segments' })
export class VideoSongSegment {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @ManyToOne(() => Video, (video) => video.segments)
  video!: Video;

  @ManyToOne(() => Song, (song) => song.segments)
  song!: Song;

  @Column({ name: 'start_sec', type: 'float' })
  startSec!: number;

  @Column({ name: 'end_sec', type: 'float' })
  endSec!: number;

  @Column({ type: 'float' })
  confidence!: number;

  @Column({ type: 'jsonb', nullable: true })
  evidence!: Record<string, unknown> | null;
}
