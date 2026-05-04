import { CommonModule, DatePipe } from '@angular/common';
import { Component, DestroyRef, inject, OnDestroy, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize, interval, Subscription, switchMap, takeWhile } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DocumentsService } from '../../../core/services/documents.service';
import { JobsService } from '../../../core/services/jobs.service';
import { DocumentItem } from '../../../core/interfaces/document.interface';
import { JobItem } from '../../../core/interfaces/job.interface';
import { ToastService } from '../../../core/services/toast.service';
import { PopupContainerComponent } from '../../../components/popup-container/popup-container.component';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

@Component({
  selector: 'app-document-detail-page',
  standalone: true,
  imports: [CommonModule, DatePipe, RouterLink, PopupContainerComponent],
  templateUrl: './document-detail-page.component.html',
})
export class DocumentDetailPageComponent implements OnDestroy {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly documentsService = inject(DocumentsService);
  private readonly jobsService = inject(JobsService);
  private readonly toast = inject(ToastService);
  private readonly destroyRef = inject(DestroyRef);

  readonly document = signal<DocumentItem | null>(null);
  readonly jobs = signal<JobItem[]>([]);
  readonly loading = signal(true);
  readonly jobsLoading = signal(false);
  readonly runLoadingId = signal<string | null>(null);
  readonly deleting = signal(false);
  readonly showDeletePopup = signal(false);
  readonly error = signal<string | null>(null);
  readonly jobsError = signal<string | null>(null);
  readonly documentId = signal<string>('');

  readonly showViewer = signal(false);
  readonly viewerUrl = signal<string | null>(null);
  readonly viewerSafeUrl = signal<SafeResourceUrl | null>(null);
  readonly viewerMimeType = signal<string | null>(null);
  readonly previewLoading = signal(false);
  readonly downloadLoading = signal(false);
  readonly polling = signal(false);

  private readonly sanitizer = inject(DomSanitizer);
  private pollingSub: Subscription | null = null;

  ngOnDestroy(): void {
    this.revokeViewerUrl();
    this.stopPolling();
  }

  constructor() {
    this.route.paramMap
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((params) => {
        const id = params.get('id') ?? '';

        if (!id) {
          this.router.navigateByUrl('/documents');
          return;
        }

        this.documentId.set(id);
        this.loadDocumentAndJobs();
      });
  }

  loadDocumentAndJobs(): void {
    const id = this.documentId();
    if (!id) return;

    this.loading.set(true);
    this.error.set(null);
    this.jobs.set([]);
    this.jobsError.set(null);

    this.documentsService
      .getById(id)
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (doc) => {
          this.document.set(doc);
          this.loadJobs();
        },
        error: (err) => {
          this.error.set(err?.error?.detail || 'No se pudo cargar el documento.');
        },
      });
  }

  loadJobs(): void {
    const id = this.documentId();
    if (!id) return;

    this.jobsLoading.set(true);
    this.jobsError.set(null);

    this.documentsService
      .getJobs(id)
      .pipe(finalize(() => this.jobsLoading.set(false)))
      .subscribe({
        next: (jobs) => {
          this.jobs.set(jobs);
          this.maybeStartPolling(jobs);
        },
        error: (err) => {
          this.jobsError.set(err?.error?.detail || 'No se pudieron cargar los procesos.');
        },
      });
  }

  private maybeStartPolling(jobs: JobItem[]): void {
    const hasActiveJob = jobs.some(
      (j) => j.status === 'pending' || j.status === 'running'
    );

    if (hasActiveJob && !this.pollingSub) {
      this.polling.set(true);
      const id = this.documentId();
      this.pollingSub = interval(4000)
        .pipe(
          switchMap(() => this.documentsService.getJobs(id)),
          takeWhile((updatedJobs) => {
            const stillActive = updatedJobs.some(
              (j) => j.status === 'pending' || j.status === 'running'
            );
            return stillActive;
          }, true) // emit the final value that fails the predicate
        )
        .subscribe({
          next: (updatedJobs) => {
            this.jobs.set(updatedJobs);
            const done = updatedJobs.every(
              (j) => j.status !== 'pending' && j.status !== 'running'
            );
            if (done) {
              this.stopPolling();
              this.toast.show('Procesamiento completado.', 'success');
              // Reload document to get updated processing_status
              this.documentsService.getById(id).subscribe({
                next: (doc) => this.document.set(doc),
              });
            }
          },
          error: () => this.stopPolling(),
        });
    }
  }

  private stopPolling(): void {
    this.pollingSub?.unsubscribe();
    this.pollingSub = null;
    this.polling.set(false);
  }

  runProcessingJob(jobId: string): void {
    this.runLoadingId.set(jobId);

    this.jobsService
      .run(jobId)
      .pipe(finalize(() => this.runLoadingId.set(null)))
      .subscribe({
        next: () => {
          this.toast.show('Documento procesado correctamente.', 'success');
          this.loadDocumentAndJobs();
        },
        error: (err) => {
          this.jobsError.set(err?.error?.detail || 'No se pudo procesar el documento.');
        },
      });
  }

  visualizeDocument(): void {
    const doc = this.document();
    if (!doc) return;

    this.previewLoading.set(true);

    this.documentsService
      .previewFile(doc.id)
      .pipe(finalize(() => this.previewLoading.set(false)))
      .subscribe({
        next: (blob) => {
          this.revokeViewerUrl();

          const url = URL.createObjectURL(blob);
          this.viewerUrl.set(url);
          this.viewerSafeUrl.set(this.sanitizer.bypassSecurityTrustResourceUrl(url));
          this.viewerMimeType.set(doc.mime_type || blob.type || 'application/octet-stream');
          this.showViewer.set(true);
        },
        error: (err) => {
          this.toast.show(err?.error?.detail || 'No se pudo visualizar el archivo.', 'error');
        },
      });
  }

  downloadDocument(): void {
    const doc = this.document();
    if (!doc) return;

    this.downloadLoading.set(true);

    this.documentsService
      .downloadFile(doc.id)
      .pipe(finalize(() => this.downloadLoading.set(false)))
      .subscribe({
        next: (response) => {
          const blob = response.body;
          if (!blob) {
            this.toast.show('No se pudo descargar el archivo.', 'error');
            return;
          }

          const url = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = url;
          link.download = doc.filename_original;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          setTimeout(() => URL.revokeObjectURL(url), 100);
        },
        error: (err) => {
          this.toast.show(err?.error?.detail || 'No se pudo descargar el archivo.', 'error');
        },
      });
  }

  closeViewer(): void {
    this.showViewer.set(false);
    this.revokeViewerUrl();
    this.viewerMimeType.set(null);
    this.viewerSafeUrl.set(null);
  }

  private revokeViewerUrl(): void {
    const currentUrl = this.viewerUrl();
    if (currentUrl) {
      URL.revokeObjectURL(currentUrl);
      this.viewerUrl.set(null);
    }

    this.viewerSafeUrl.set(null);
  }

  openDeletePopup(): void {
    this.showDeletePopup.set(true);
  }

  closeDeletePopup(): void {
    if (this.deleting()) return;
    this.showDeletePopup.set(false);
  }

  confirmDeleteDocument(): void {
    const doc = this.document();
    if (!doc) return;

    this.deleting.set(true);

    this.documentsService
      .delete(doc.id)
      .pipe(finalize(() => this.deleting.set(false)))
      .subscribe({
        next: () => {
          this.showDeletePopup.set(false);
          this.toast.show('Documento eliminado correctamente.', 'success');
          this.router.navigateByUrl('/documents');
        },
        error: (err) => {
          this.toast.show(err?.error?.detail || 'No se pudo eliminar el documento.', 'error');
        },
      });
  }

  getStatusClasses(status: string): string {
    const value = (status || '').toLowerCase();

    if (['processed', 'completed'].includes(value)) {
      return 'bg-green-100 text-green-700 border-green-200';
    }

    if (['pending', 'running'].includes(value)) {
      return 'bg-yellow-100 text-yellow-700 border-yellow-200';
    }

    if (['error', 'failed'].includes(value)) {
      return 'bg-red-100 text-red-700 border-red-200';
    }

    if (['review'].includes(value)) {
      return 'bg-blue-100 text-blue-700 border-blue-200';
    }

    return 'bg-slate-100 text-slate-700 border-slate-200';
  }

  getStatusLabel(status: string | null | undefined): string {
    const value = (status || '').toLowerCase();

    switch (value) {
      case 'uploaded':
        return 'Subido';
      case 'pending':
        return 'Pendiente';
      case 'running':
        return 'Procesando';
      case 'processed':
      case 'completed':
        return 'Procesado';
      case 'error':
      case 'failed':
        return 'Error';
      case 'review':
        return 'En revisión';
      default:
        return status || '-';
    }
  }

  getJobTypeLabel(jobType: string | null | undefined): string {
    const value = (jobType || '').toLowerCase();

    switch (value) {
      case 'document_processing':
        return 'Procesamiento';
      default:
        return jobType || '-';
    }
  }

  formatConfidence(value: number | null): string {
    if (value === null || value === undefined) return '-';
    return `${(value * 100).toFixed(0)}%`;
  }
}