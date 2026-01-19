import React from 'react';
import { Segment } from '../api/client';

interface SegmentTableProps {
  segments: Segment[];
  onSelect: (segment: Segment) => void;
}

export default function SegmentTable({ segments, onSelect }: SegmentTableProps) {
  if (!segments.length) {
    return <p className="notice">분석된 세그먼트가 없습니다.</p>;
  }

  return (
    <table className="table">
      <thead>
        <tr>
          <th>곡</th>
          <th>원곡자</th>
          <th>구간</th>
          <th>신뢰도</th>
        </tr>
      </thead>
      <tbody>
        {segments.map((segment) => (
          <tr key={segment.id} onClick={() => onSelect(segment)}>
            <td>{segment.song?.title ?? '알 수 없음'}</td>
            <td>{segment.song?.originalArtist ?? '-'}</td>
            <td>
              {segment.startSec.toFixed(1)}s - {segment.endSec.toFixed(1)}s
            </td>
            <td>{Math.round(segment.confidence * 100)}%</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
