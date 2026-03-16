import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { DocumentItem } from '../interfaces/document.interface';
import { JobItem } from '../interfaces/job.interface';

@Injectable({ providedIn: 'root' })
export class DocumentsService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/documents`;

  list(): Observable<DocumentItem[]> {
    return this.http.get<DocumentItem[]>(this.baseUrl);
  }

  getById(documentId: string): Observable<DocumentItem> {
    return this.http.get<DocumentItem>(`${this.baseUrl}/${documentId}`);
  }

  getJobs(documentId: string): Observable<JobItem[]> {
    return this.http.get<JobItem[]>(`${this.baseUrl}/${documentId}/jobs`);
  }

  upload(file: File): Observable<DocumentItem> {
    const formData = new FormData();
    formData.append('file', file);

    return this.http.post<DocumentItem>(`${this.baseUrl}/upload`, formData);
  }

  delete(documentId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${documentId}`);
  }

  getFileUrl(id: string, download = false): string {
    return `${this.baseUrl}/${id}/file${download ? '?download=true' : ''}`;
  }

  downloadFile(id: string) {
    return this.http.get(`${this.baseUrl}/${id}/file?download=true`, {
      responseType: 'blob',
      observe: 'response'
    });
  }

  previewFile(id: string) {
    return this.http.get(`${this.baseUrl}/${id}/file`, {
      responseType: 'blob'
    });
  }
}
