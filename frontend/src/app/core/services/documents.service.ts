import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { DocumentItem, DocumentUploadResponse } from '../interfaces/document.interface';
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

  upload(files: File[]): Observable<DocumentUploadResponse[]> {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    return this.http.post<DocumentUploadResponse[]>(`${this.baseUrl}/upload`, formData);
  }

  delete(documentId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${documentId}`);
  }

  bulkDelete(documentIds: string[]): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}/bulk-delete`, documentIds);
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

  getAnalyzeExcel(documentId: string): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/${documentId}/preview`);
  }
}
