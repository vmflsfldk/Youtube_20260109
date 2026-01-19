import React, { useState } from 'react';
import { Segment } from '../api/client';

interface ClipModalProps {
  segment: Segment;
  onClose: () => void;
  onSubmit: (payload: {
    title: string;
    visibility: string;
    startSec: number;
    endSec: number;
  }) => void;
}

export default function ClipModal({ segment, onClose, onSubmit }: ClipModalProps) {
  const [title, setTitle] = useState(segment.song?.title ?? 'New Clip');
  const [visibility, setVisibility] = useState('public');
  const [startSec, setStartSec] = useState(segment.startSec);
  const [endSec, setEndSec] = useState(segment.endSec);

  return (
    <div className="modal-backdrop">
      <div className="modal">
        <h3>클립 생성</h3>
        <label>클립 제목</label>
        <input value={title} onChange={(event) => setTitle(event.target.value)} />
        <label>공개 범위</label>
        <select value={visibility} onChange={(event) => setVisibility(event.target.value)}>
          <option value="public">Public</option>
          <option value="unlisted">Unlisted</option>
          <option value="private">Private</option>
        </select>
        <label>시작(초)</label>
        <input
          type="number"
          value={startSec}
          onChange={(event) => setStartSec(Number(event.target.value))}
        />
        <label>끝(초)</label>
        <input
          type="number"
          value={endSec}
          onChange={(event) => setEndSec(Number(event.target.value))}
        />
        <div className="flex">
          <button
            onClick={() =>
              onSubmit({
                title,
                visibility,
                startSec,
                endSec,
              })
            }
          >
            저장
          </button>
          <button className="secondary" onClick={onClose}>
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}
