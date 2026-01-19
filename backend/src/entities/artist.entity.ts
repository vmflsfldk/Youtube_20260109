import { Column, CreateDateColumn, Entity, OneToMany, PrimaryGeneratedColumn } from 'typeorm';
import { Video } from './video.entity';

@Entity({ name: 'artists' })
export class Artist {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ name: 'channel_id', unique: true })
  channelId!: string;

  @Column()
  name!: string;

  @Column({ type: 'jsonb', nullable: true })
  aliases!: string[] | null;

  @CreateDateColumn({ name: 'created_at' })
  createdAt!: Date;

  @OneToMany(() => Video, (video) => video.artist)
  videos!: Video[];
}
