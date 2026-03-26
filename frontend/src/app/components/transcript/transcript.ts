import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Segment } from '../../services/api';

@Component({
  selector: 'app-transcript',
  imports: [CommonModule],
  templateUrl: './transcript.html',
  styleUrl: './transcript.scss',
})
export class Transcript {
  @Input() segments: Segment[] = [];
  @Input() status = '';
  @Input() progress: { stage: string; percent: number; message: string; elapsed_seconds?: number; remaining_seconds?: number } | null | undefined = null;
  @Input() filename = '';
  @Input() rawTranscript = '';

  private speakerColors: Record<string, string> = {};
  private palette = [
    '#003747', '#065465', '#046276', '#026a81', '#06768d',
  ];

  getSpeakerColor(speaker: string): string {
    if (!this.speakerColors[speaker]) {
      const index = Object.keys(this.speakerColors).length % this.palette.length;
      this.speakerColors[speaker] = this.palette[index];
    }
    return this.speakerColors[speaker];
  }

  formatTime(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  formatTimeRemaining(seconds: number): string {
    if (seconds < 60) {
      return `${Math.round(seconds)}s`;
    }
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}m ${secs}s`;
  }

  downloadTranscript() {
    if (!this.rawTranscript) return;
    const blob = new Blob([this.rawTranscript], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = this.filename || 'transcript.txt';
    a.click();
    URL.revokeObjectURL(url);
  }
}
