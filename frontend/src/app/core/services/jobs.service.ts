import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { JobItem } from '../interfaces/job.interface';

@Injectable({ providedIn: 'root' })
export class JobsService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/jobs`;

  runMock(jobId: string): Observable<JobItem> {
    return this.http.post<JobItem>(`${this.baseUrl}/${jobId}/run-mock`, {});
  }
}
