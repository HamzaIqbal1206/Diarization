import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Upload } from '../upload/upload';
import { Transcript } from '../transcript/transcript';
import { ApiService, Segment } from '../../services/api';

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
  minSpeakers = 2;
  maxSpeakers = 2;
  hfToken = '';

  jobId = '';
  jobStatus = '';
  jobError = '';
  segments: Segment[] = [];

  existingTranscripts: { pipeline: string; filename: string }[] = [];
  pollInterval: ReturnType<typeof setInterval> | null = null;

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.loadAudioFiles();
    this.loadTranscripts();
  }

  loadAudioFiles() {
    this.api.getAudioFiles().subscribe({
      next: (res) => {
        this.audioFiles = res.files;
        if (res.files.length && !this.selectedFile) {
          this.selectedFile = res.files[0];
        }
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
    this.segments = [];

    this.api
      .runPipeline({
        pipeline: this.pipeline,
        audioFile: this.selectedFile,
        minSpeakers: this.minSpeakers,
        maxSpeakers: this.maxSpeakers,
        hfToken: this.hfToken,
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
          if (job.status === 'completed') {
            this.segments = job.segments || [];
            this.stopPolling();
            this.loadTranscripts();
          } else if (job.status === 'failed') {
            this.jobError = job.error || 'Pipeline failed';
            this.stopPolling();
          }
        },
      });
    }, 3000);
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
        this.jobStatus = 'completed';
      },
    });
  }
}
