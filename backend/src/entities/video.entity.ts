import {
  Column,
  CreateDateColumn,
  Entity,
  ManyToOne,
  OneToMany,
  PrimaryGeneratedColumn,
} from 'typeorm';
import { Artist } from './artist.entity';
import { VideoSongSegment } from './video-song-segment.entity';
import { Clip } from './clip.entity';

@Entity({ name: 'videos' })
export class Video {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ name: 'youtube_video_id', unique: true })
  youtubeVideoId!: string;

  @ManyToOne(() => Artist, (artist) => artist.videos)
  artist!: Artist;

  @Column()
  title!: string;

  @Column({ name: 'published_at', type: 'timestamptz', nullable: true })
  publishedAt!: Date | null;

  @Column({ name: 'duration_sec', type: 'int', nullable: true })
  durationSec!: number | null;

  @Column({ default: 'pending' })
  status!: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt!: Date;

  @OneToMany(() => VideoSongSegment, (segment) => segment.video)
  segments!: VideoSongSegment[];

  @OneToMany(() => Clip, (clip) => clip.video)
  clips!: Clip[];
}
