import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Upload } from '../upload/upload';
import { Transcript } from '../transcript/transcript';
import { JobQueue, QueueJob } from '../job-queue/job-queue';
import { ApiService, Segment, JobStatus } from '../../services/api';

@Component({
  selector: 'app-dashboard',
  imports: [CommonModule, FormsModule, Upload, Transcript, JobQueue],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class Dashboard implements OnInit, OnDestroy {
  audioFiles: string[] = [];
  pipeline = 'fasterwhisper';
  language: string | null = null;
  minSpeakers: number | null = null;
  maxSpeakers: number | null = null;

  jobs: QueueJob[] = [];
  jobProgress: Record<string, JobStatus['progress']> = {};

  // Currently viewing result
  segments: Segment[] = [];
  transcriptFilename = '';
  rawTranscript = '';
  viewStatus = '';

  existingTranscripts: { pipeline: string; filename: string }[] = [];
  pollInterval: ReturnType<typeof setInterval> | null = null;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.loadAudioFiles();
    this.loadTranscripts();
  }

  ngOnDestroy() {
    this.stopPolling();
  }

  loadAudioFiles() {
    this.api.getAudioFiles().subscribe({
      next: (res) => {
        this.audioFiles = res.files;
      },
    });
  }

  loadTranscripts() {
    this.api.getTranscripts().subscribe({
      next: (res) => (this.existingTranscripts = res.transcripts),
    });
  }

  onFilesUploaded(filenames: string[]) {
    this.loadAudioFiles();
    // Auto-add uploaded files to queue
    filenames.forEach(f => this.addFile(f));
  }

  isFileProcessing(filename: string): boolean {
    return this.jobs.some(j => j.audioFile === filename && (j.status === 'running' || j.status === 'queued'));
  }

  allFilesProcessing(): boolean {
    return this.audioFiles.every(f => this.isFileProcessing(f));
  }

  addFile(filename: string) {
    if (this.isFileProcessing(filename)) return;

    const jobId = this.generateJobId();
    const job: QueueJob = {
      jobId,
      status: 'queued',
      pipeline: this.pipeline,
      audioFile: filename,
    };

    this.jobs.unshift(job);
    this.processQueue();
  }

  addAllFiles() {
    this.audioFiles.forEach(f => {
      if (!this.isFileProcessing(f)) {
        this.addFile(f);
      }
    });
  }

  private generateJobId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  private processQueue() {
    const queuedJobs = this.jobs.filter(j => j.status === 'queued');
    queuedJobs.forEach(job => this.startJob(job));
  }

  private startJob(job: QueueJob) {
    job.status = 'running';

    this.api.runPipeline({
      pipeline: job.pipeline,
      audioFile: job.audioFile,
      language: this.language,
      minSpeakers: this.minSpeakers,
      maxSpeakers: this.maxSpeakers,
    }).subscribe({
      next: (res) => {
        job.jobId = res.jobId;
        this.startPolling();
      },
      error: (err) => {
        job.status = 'failed';
        job.error = err.error?.detail || 'Failed to start pipeline';
        this.cdr.detectChanges();
        this.processQueue();
      },
    });
  }

  startPolling() {
    if (this.pollInterval) return; // Already polling

    this.pollInterval = setInterval(() => {
      const runningJobs = this.jobs.filter(j => j.status === 'running');
      if (runningJobs.length === 0) {
        this.stopPolling();
        return;
      }

      runningJobs.forEach(job => {
        this.api.getJobStatus(job.jobId).subscribe({
          next: (status) => {
            job.status = status.status;
            job.progress = status.progress;
            job.segments = status.segments;
            job.transcript = status.transcript;
            job.outputFilename = status.outputFilename;
            job.error = status.error;

            if (status.status === 'completed' || status.status === 'failed') {
              if (status.status === 'completed') {
                this.loadTranscripts();
              }
              this.processQueue();
            }

            this.cdr.detectChanges();
          },
        });
      });
    }, 2000);
  }

  stopPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }

  viewJobResult(job: QueueJob) {
    this.segments = job.segments || [];
    this.transcriptFilename = job.outputFilename || job.audioFile;
    this.rawTranscript = job.transcript || '';
    this.viewStatus = 'completed';
  }

  retryJob(job: QueueJob) {
    job.status = 'queued';
    job.error = undefined;
    job.progress = undefined;
    this.processQueue();
  }

  viewTranscript(pipeline: string, filename: string) {
    this.api.getTranscript(pipeline, filename).subscribe({
      next: (res) => {
        this.segments = res.segments;
        this.transcriptFilename = filename;
        this.rawTranscript = res.transcript || '';
        this.viewStatus = 'completed';
      },
    });
  }
}
