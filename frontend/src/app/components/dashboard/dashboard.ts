import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Upload } from '../upload/upload';
import { Transcript } from '../transcript/transcript';
import { ApiService, Segment, JobStatus } from '../../services/api';

@Component({
  selector: 'app-dashboard',
  imports: [CommonModule, FormsModule, Upload, Transcript],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class Dashboard implements OnInit {
  audioFiles: string[] = [];
  selectedFile = '';
  pipeline = 'fasterwhisper';
  language: string | null = null;
  minSpeakers: number | null = null;
  maxSpeakers: number | null = null;

  jobId = '';
  jobStatus = '';
  jobError = '';
  segments: Segment[] = [];
  jobProgress: JobStatus['progress'] | null = null;
  transcriptFilename = '';
  rawTranscript = '';

  existingTranscripts: { pipeline: string; filename: string }[] = [];
  pollInterval: ReturnType<typeof setInterval> | null = null;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.loadAudioFiles();
    this.loadTranscripts();
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

  onFileUploaded(filename: string) {
    this.loadAudioFiles();
    this.selectedFile = filename;
  }

  runPipeline() {
    if (!this.selectedFile) return;

    this.jobStatus = 'running';
    this.jobError = '';
    this.jobProgress = null;
    this.segments = [];
    this.transcriptFilename = '';
    this.rawTranscript = '';

    this.api
      .runPipeline({
        pipeline: this.pipeline,
        audioFile: this.selectedFile,
        language: this.language,
        minSpeakers: this.minSpeakers,
        maxSpeakers: this.maxSpeakers,
      })
      .subscribe({
        next: (res) => {
          this.jobId = res.jobId;
          this.startPolling();
        },
        error: (err) => {
          this.jobStatus = 'failed';
          this.jobError = err.error?.detail || 'Failed to start pipeline';
        },
      });
  }

  startPolling() {
    this.pollInterval = setInterval(() => {
      this.api.getJobStatus(this.jobId).subscribe({
        next: (job) => {
          this.jobStatus = job.status;
          this.jobProgress = job.progress || null;

          if (job.status === 'completed') {
            this.segments = job.segments || [];
            this.transcriptFilename = job.outputFilename || this.selectedFile;
            this.rawTranscript = job.transcript || '';
            this.jobProgress = null;
            this.stopPolling();
            this.loadTranscripts();
          } else if (job.status === 'failed') {
            this.jobError = job.error || 'Pipeline failed';
            this.jobProgress = null;
            this.stopPolling();
          }

          this.cdr.detectChanges();
        },
      });
    }, 2000);
  }

  stopPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }

  viewTranscript(pipeline: string, filename: string) {
    this.api.getTranscript(pipeline, filename).subscribe({
      next: (res) => {
        this.segments = res.segments;
        this.transcriptFilename = filename;
        this.rawTranscript = res.transcript || '';
        this.jobStatus = 'completed';
        this.jobProgress = null;
        this.jobError = '';
      },
    });
  }
}
