# Frontend

Angular 17+ web interface for the Diarization application.

## Features

- **Upload Component**: Drag & drop or click to upload audio files
- **Dashboard Component**: Configure settings, manage job queue, view transcripts
- **Job Queue Component**: Real-time progress tracking with pause/resume
- **Transcript Component**: View speaker-segmented transcripts with download

## Tech Stack

- Angular 17+
- TypeScript
- RxJS
- Angular Forms

## Project Structure

```
frontend/src/app/
├── app.ts                 # Root component
├── app.config.ts          # App configuration
├── app.routes.ts          # Routing config
├── components/
│   ├── dashboard/         # Main dashboard (settings + job management)
│   │   ├── dashboard.ts
│   │   ├── dashboard.html
│   │   └── dashboard.scss
│   ├── upload/            # Audio file upload
│   │   ├── upload.ts
│   │   ├── upload.html
│   │   └── upload.scss
│   ├── job-queue/         # Job queue with progress tracking
│   │   ├── job-queue.ts
│   │   ├── job-queue.html
│   │   └── job-queue.scss
│   └── transcript/        # Transcript viewer
│       ├── transcript.ts
│       ├── transcript.html
│       └── transcript.scss
└── services/
    └── api.ts             # API service for backend communication
```

## Development Server

```bash
ng serve
```

Navigate to `http://localhost:4200/`. The app auto-reloads on file changes.

## Build

```bash
ng build
```

Build artifacts are stored in `dist/`.

## Running Tests

```bash
ng test        # Unit tests with Vitest
ng e2e         # End-to-end tests
```

## API Service

The `ApiService` (`services/api.ts`) provides methods for:

| Method | Description |
|--------|-------------|
| `getAudioFiles()` | List uploaded audio files |
| `uploadAudio(file)` | Upload an audio file |
| `runPipeline(config)` | Start a diarization job |
| `getJobStatus(jobId)` | Get job status and progress |
| `getTranscripts()` | List all completed transcripts |
| `getTranscript(pipeline, filename)` | Get specific transcript |
| `pauseAllJobs()` | Pause all running jobs |
| `resumeAllJobs()` | Resume paused jobs |

## Supported Audio Formats

- mp3
- wav
- m4a
- flac
- ogg
- aac
- aiff

## Proxy Configuration

The frontend proxies `/api` requests to the backend at `http://localhost:8000`.

Configured in `proxy.conf.json`:

```json
{
  "/api": {
    "target": "http://localhost:8000",
    "secure": false
  }
}
```

## Additional Resources

- [Angular CLI Overview](https://angular.dev/tools/cli)
- [Angular Documentation](https://angular.dev)
