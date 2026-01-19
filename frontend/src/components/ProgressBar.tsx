import React from 'react';

interface ProgressBarProps {
  progress: number;
}

export default function ProgressBar({ progress }: ProgressBarProps) {
  return (
    <div className="progress-bar" aria-label={`progress ${progress}%`}>
      <span style={{ width: `${progress}%` }} />
    </div>
  );
}
