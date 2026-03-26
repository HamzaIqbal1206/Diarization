import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { JobStatus } from '../../services/api';

export interface QueueJob extends JobStatus {
  jobId: string;
  progress?: {
    stage: string;
    percent: number;
    message: string;
    elapsed_seconds?: number;
    remaining_seconds?: number;
  };
}

@Component({
  selector: 'app-job-queue',
  imports: [CommonModule],
  templateUrl: './job-queue.html',
  styleUrl: './job-queue.scss',
})
export class JobQueue {
  @Input() jobs: QueueJob[] = [];
  @Input() isPaused: boolean = false;
  @Output() viewJob = new EventEmitter<QueueJob>();
  @Output() retryJob = new EventEmitter<QueueJob>();
  @Output() togglePause = new EventEmitter<void>();
  @Output() retryAllFailed = new EventEmitter<void>();

  get totalJobs(): number {
    return this.jobs.length;
  }

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

  get retryingJobs(): QueueJob[] {
    return this.jobs.filter(j => j.status === 'retrying');
  }

  get activeJobs(): number {
    return this.runningJobs.length + this.queuedJobs.length + this.retryingJobs.length;
  }

  get collectiveProgress(): number {
    const total = this.jobs.length;
    if (total === 0) return 0;

    // Calculate overall progress: completed = 100%, failed = 100%, running = actual %, queued = 0%
    let totalPercent = 0;

    for (const job of this.jobs) {
      if (job.status === 'completed') {
        totalPercent += 100;
      } else if (job.status === 'failed') {
        totalPercent += 100; // Count failed as "done"
      } else if (job.status === 'running' && job.progress) {
        totalPercent += job.progress.percent;
      }
      // queued = 0%
    }

    return Math.round((totalPercent / total) * 10) / 10; // 1 decimal place
  }

  get estimatedTimeRemaining(): number {
    const running = this.runningJobs;
    if (running.length === 0) return 0;

    // Use the max remaining time from any running job
    const maxRemaining = running.reduce((max, job) => {
      const remaining = job.progress?.remaining_seconds || 0;
      return Math.max(max, remaining);
    }, 0);

    return maxRemaining;
  }

  get isProcessing(): boolean {
    return this.activeJobs > 0;
  }

  getStatusLabel(status: string, retryCount?: number): string {
    switch (status) {
      case 'running': return 'Processing';
      case 'queued': return 'Queued';
      case 'completed': return 'Done';
      case 'failed': return 'Failed';
      case 'retrying': return `Retry #${retryCount || 1}`;
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
