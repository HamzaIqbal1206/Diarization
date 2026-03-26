import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Segment {
  start: number;
  end: number;
  speaker: string;
  text: string;
}

export interface TranscriptResult {
  pipeline: string;
  filename: string;
  transcript: string;
  segments: Segment[];
}

export interface JobStatus {
  status: 'running' | 'completed' | 'failed' | 'queued';
  pipeline: string;
  audioFile: string;
  batchId?: string;
  progress?: {
    stage: string;
    percent: number;
    message: string;
    elapsed_seconds?: number;
    remaining_seconds?: number;
  };
  error?: string;
  segments?: Segment[];
  transcript?: string;
  outputFilename?: string;
}

export interface BatchStatus {
  status: 'running' | 'completed' | 'partial_failure' | 'failed';
  pipeline: string;
  total: number;
  completed: number;
  failed: number;
  jobs: Record<string, string>;
  jobDetails: Record<string, JobStatus>;
}

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private baseUrl = '/api';

  constructor(private http: HttpClient) {}

  getAudioFiles(): Observable<{ files: string[] }> {
    return this.http.get<{ files: string[] }>(`${this.baseUrl}/audio-files`);
  }

  uploadAudio(file: File): Observable<{ filename: string }> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<{ filename: string }>(`${this.baseUrl}/upload`, formData);
  }

  runPipeline(config: {
    pipeline: string;
    audioFile: string;
    language: string | null;
    minSpeakers: number | null;
    maxSpeakers: number | null;
  }): Observable<{ jobId: string; status: string }> {
    return this.http.post<{ jobId: string; status: string }>(`${this.baseUrl}/run`, config);
  }

  getJobStatus(jobId: string): Observable<JobStatus> {
    return this.http.get<JobStatus>(`${this.baseUrl}/jobs/${jobId}`);
  }

  getTranscripts(): Observable<{ transcripts: { pipeline: string; filename: string }[] }> {
    return this.http.get<{ transcripts: { pipeline: string; filename: string }[] }>(`${this.baseUrl}/transcripts`);
  }

  getTranscript(pipeline: string, filename: string): Observable<TranscriptResult> {
    return this.http.get<TranscriptResult>(`${this.baseUrl}/transcripts/${pipeline}/${filename}`);
  }

  runBatch(config: {
    pipeline: string;
    audioFiles: string[];
    maxConcurrent?: number;
    language: string | null;
    minSpeakers: number | null;
    maxSpeakers: number | null;
  }): Observable<{ batchId: string; status: string; total: number; jobs: Record<string, string> }> {
    return this.http.post<{ batchId: string; status: string; total: number; jobs: Record<string, string> }>(
      `${this.baseUrl}/run-batch`,
      config
    );
  }

  getBatchStatus(batchId: string): Observable<BatchStatus> {
    return this.http.get<BatchStatus>(`${this.baseUrl}/batch/${batchId}`);
  }
}
