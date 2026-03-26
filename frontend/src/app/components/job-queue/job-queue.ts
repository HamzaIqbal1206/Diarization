import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { JobStatus } from '../../services/api';

export interface QueueJob extends JobStatus {
  jobId: string;
}

@Component({
  selector: 'app-job-queue',
  imports: [CommonModule],
  templateUrl: './job-queue.html',
  styleUrl: './job-queue.scss',
})
export class JobQueue {
  @Input() jobs: QueueJob[] = [];
  @Output() viewJob = new EventEmitter<QueueJob>();
  @Output() retryJob = new EventEmitter<QueueJob>();

  get runningJobs(): QueueJob[] {
    return this.jobs.filter(j => j.status === 'running');
  }

  get queuedJobs(): QueueJob[] {
    return this.jobs.filter(j => j.status === 'queued');
  }

  get completedJobs(): QueueJob[] {
    return this.jobs.filter(j => j.status === 'completed');
  }

  get failedJobs(): QueueJob[] {
    return this.jobs.filter(j => j.status === 'failed');
  }

  getStatusLabel(status: string): string {
    switch (status) {
      case 'running': return 'Processing';
      case 'queued': return 'Queued';
      case 'completed': return 'Done';
      case 'failed': return 'Failed';
      default: return status;
    }
  }

  formatTime(seconds: number): string {
    if (seconds < 60) {
      return `${Math.round(seconds)}s`;
    }
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}m ${secs}s`;
  }
}
