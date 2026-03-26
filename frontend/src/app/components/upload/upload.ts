import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../services/api';
import { forkJoin } from 'rxjs';

@Component({
  selector: 'app-upload',
  imports: [CommonModule],
  templateUrl: './upload.html',
  styleUrl: './upload.scss',
})
export class Upload {
  @Output() filesUploaded = new EventEmitter<string[]>();

  uploading = false;
  uploadProgress = 0;
  totalFiles = 0;
  dragOver = false;

  constructor(private api: ApiService) {}

  onDragOver(event: DragEvent) {
    event.preventDefault();
    this.dragOver = true;
  }

  onDragLeave() {
    this.dragOver = false;
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    this.dragOver = false;
    const files = Array.from(event.dataTransfer?.files || []);
    if (files.length > 0) this.uploadFiles(files);
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files || []);
    if (files.length > 0) this.uploadFiles(files);
    input.value = '';
  }

  private uploadFiles(files: File[]) {
    this.uploading = true;
    this.totalFiles = files.length;
    this.uploadProgress = 0;

    const uploads = files.map((file) => this.api.uploadAudio(file));

    forkJoin(uploads).subscribe({
      next: (results) => {
        this.uploading = false;
        const filenames = results.map((r) => r.filename);
        this.filesUploaded.emit(filenames);
      },
      error: () => {
        this.uploading = false;
      },
    });

    // Track progress manually since forkJoin doesn't give per-file progress
    let completed = 0;
    files.forEach((file) => {
      this.api.uploadAudio(file).subscribe({
        next: () => {
          completed++;
          this.uploadProgress = completed;
        },
      });
    });
  }
}
