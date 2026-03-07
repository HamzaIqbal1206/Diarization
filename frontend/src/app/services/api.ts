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
  status: 'running' | 'completed' | 'failed';
  pipeline: string;
  audioFile: string;
  transcript?: string;
  segments?: Segment[];
  error?: string;
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
    minSpeakers: number;
    maxSpeakers: number;
    hfToken: string;
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
}
