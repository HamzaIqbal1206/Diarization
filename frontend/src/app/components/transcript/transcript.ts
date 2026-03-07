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
}
