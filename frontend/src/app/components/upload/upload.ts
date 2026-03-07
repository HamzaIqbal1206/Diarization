import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../services/api';

@Component({
  selector: 'app-upload',
  imports: [CommonModule],
  templateUrl: './upload.html',
  styleUrl: './upload.scss',
})
export class Upload {
  @Output() fileUploaded = new EventEmitter<string>();

  uploading = false;
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
    const file = event.dataTransfer?.files[0];
    if (file) this.uploadFile(file);
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) this.uploadFile(file);
    input.value = '';
  }

  private uploadFile(file: File) {
    this.uploading = true;
    this.api.uploadAudio(file).subscribe({
      next: (res) => {
        this.uploading = false;
        this.fileUploaded.emit(res.filename);
      },
      error: () => {
        this.uploading = false;
      },
    });
  }
}
