import { Column, Entity, OneToMany, PrimaryGeneratedColumn } from 'typeorm';
import { VideoSongSegment } from './video-song-segment.entity';

@Entity({ name: 'songs' })
export class Song {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column()
  title!: string;

  @Column({ name: 'original_artist' })
  originalArtist!: string;

  @Column({ name: 'lyrics_text', type: 'text' })
  lyricsText!: string;

  @Column({ nullable: true })
  language!: string | null;

  @Column({ type: 'jsonb', nullable: true })
  metadata!: Record<string, unknown> | null;

  @OneToMany(() => VideoSongSegment, (segment) => segment.song)
  segments!: VideoSongSegment[];
}
