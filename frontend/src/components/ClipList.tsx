import React from 'react';
import { Clip } from '../api/client';

interface ClipListProps {
  clips: Clip[];
}

export default function ClipList({ clips }: ClipListProps) {
  if (!clips.length) {
    return <p className="notice">등록된 클립이 없습니다.</p>;
  }

  return (
    <div className="clip-list">
      {clips.map((clip) => (
        <div className="clip-card" key={clip.id}>
          <div className="flex">
            <strong>{clip.title}</strong>
            <span className="badge">{clip.visibility}</span>
          </div>
          <p className="notice">
            {clip.startSec.toFixed(1)}s - {clip.endSec.toFixed(1)}s
          </p>
        </div>
      ))}
    </div>
  );
}
