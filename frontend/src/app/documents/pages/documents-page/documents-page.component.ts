import { CommonModule, DatePipe, DecimalPipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { DocumentsService } from '../../../core/services/documents.service';
import { JobsService } from '../../../core/services/jobs.service';
import { DocumentItem } from '../../../core/interfaces/document.interface';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-documents-page',
  standalone: true,
  imports: [CommonModule, RouterLink, DatePipe, DecimalPipe],
  templateUrl: 'documents-page.component.html',
})
export class DocumentsPageComponent {
  private readonly documentsService = inject(DocumentsService);
  private readonly jobsService = inject(JobsService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);

  readonly documents = signal<DocumentItem[]>([]);
  readonly loading = signal(true);
  readonly uploading = signal(false);
  readonly error = signal<string | null>(null);
  readonly uploadError = signal<string | null>(null);
  readonly selectedFiles = signal<File[]>([]);
  readonly search = signal('');
  readonly analyzing = signal<string | null>(null);
  readonly previewData = signal<any | null>(null);
  readonly importing = signal<string | null>(null);
  readonly selectedIds = signal<Set<string>>(new Set());
  readonly isDeletingBulk = signal(false);

  readonly filteredDocuments = computed(() => {
    const term = this.search().trim().toLowerCase();
    if (!term) return this.documents();

    return this.documents().filter((doc) => {
      return [
        doc.filename_original,
        doc.mime_type,
        doc.processing_status,
        doc.upload_status,
      ].some((value) => (value || '').toLowerCase().includes(term));
    });
  });

  constructor() {
    this.loadDocuments();
  }

  loadDocuments(): void {
    this.loading.set(true);
    this.error.set(null);

    this.documentsService
      .list()
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (docs) => {
          this.documents.set(docs);
        },
        error: (err) => {
          this.error.set(err?.error?.detail || 'No se pudieron cargar los documentos.');
        },
      });
  }

  onFileChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = input.files ? Array.from(input.files) : [];
    this.selectedFiles.set(files);
    this.uploadError.set(null);
  }

  uploadSelectedFile(): void {
    const files = this.selectedFiles();

    if (files.length === 0) {
      this.uploadError.set('Selecciona al menos un archivo antes de subirlo.');
      return;
    }

    this.uploading.set(true);
    this.uploadError.set(null);

    // Upload files one by one to avoid Render timeouts with large batches
    let processedCount = 0;
    let errorCount = 0;

    const uploadFile = (index: number) => {
      if (index >= files.length) {
        this.uploading.set(false);
        this.selectedFiles.set([]);
        const fileInput = document.getElementById('document-upload-input') as HTMLInputElement | null;
        if (fileInput) fileInput.value = '';

        if (errorCount === 0) {
          this.toast.show('Todos los documentos subidos correctamente.', 'success');
        } else if (processedCount > 0) {
          this.toast.show(`Se subieron ${processedCount} documentos, pero ${errorCount} fallaron.`, 'info');
        } else {
          this.toast.show('No se pudo subir ningún documento.', 'error');
        }

        this.loadDocuments();
        return;
      }

      const file = files[index];
      this.documentsService.upload([file]).subscribe({
        next: () => {
          processedCount++;
          uploadFile(index + 1);
        },
        error: () => {
          errorCount++;
          uploadFile(index + 1);
        }
      });
    };

    uploadFile(0);
  }

  goToDetail(documentId: string): void {
    this.router.navigate(['/documents', documentId]);
  }

  toggleSelection(id: string): void {
    const current = new Set(this.selectedIds());
    if (current.has(id)) {
      current.delete(id);
    } else {
      current.add(id);
    }
    this.selectedIds.set(current);
  }

  isAllSelected(): boolean {
    const docs = this.filteredDocuments();
    if (docs.length === 0) return false;
    return docs.every((d) => this.selectedIds().has(d.id));
  }

  toggleSelectAll(): void {
    if (this.isAllSelected()) {
      this.selectedIds.set(new Set());
    } else {
      const allIds = this.filteredDocuments().map((d) => d.id);
      this.selectedIds.set(new Set(allIds));
    }
  }

  bulkDeleteSelected(): void {
    const ids = Array.from(this.selectedIds());
    if (ids.length === 0) return;

    if (!confirm(`¿Estás seguro de que deseas eliminar ${ids.length} documentos?`)) {
      return;
    }

    this.isDeletingBulk.set(true);
    this.documentsService.bulkDelete(ids).subscribe({
      next: () => {
        this.toast.show(`${ids.length} documentos eliminados correctamente.`, 'success');
        this.clearSelection();
        this.loadDocuments();
        this.isDeletingBulk.set(false);
      },
      error: (err) => {
        this.toast.show(err?.error?.detail || 'No se pudieron eliminar los documentos.', 'error');
        this.isDeletingBulk.set(false);
      }
    });
  }

  clearSelection(): void {
    this.selectedIds.set(new Set());
  }

  setSearch(value: string): void {
    this.search.set(value);
  }

  analyzeDocument(docId: string): void {
    this.analyzing.set(docId);
    this.previewData.set(null);

    this.documentsService
      .getAnalyzeExcel(docId)
      .pipe(finalize(() => this.analyzing.set(null)))
      .subscribe({
        next: (data) => {
          if (data.error) {
            this.toast.show(data.error, 'error');
          } else {
            this.previewData.set({ ...data, document_id: docId });
          }
        },
        error: (err) => {
          this.toast.show(err?.error?.detail || 'No se pudo analizar el documento.', 'error');
        },
      });
  }

  closePreview(): void {
    this.previewData.set(null);
  }

  confirmAndImport(docId: string): void {
    this.importing.set(docId);

    this.documentsService.getJobs(docId).subscribe({
      next: (jobs) => {
        const pendingJob = jobs.find((j) => j.status === 'pending');
        if (pendingJob) {
          this.jobsService
            .run(pendingJob.id)
            .pipe(finalize(() => this.importing.set(null)))
            .subscribe({
              next: () => {
                this.toast.show('Importación confirmada. El proceso ha comenzado.', 'success');
                this.closePreview();
                this.loadDocuments();
              },
              error: (err) => {
                this.toast.show(err?.error?.detail || 'No se pudo iniciar la importación.', 'error');
              },
            });
        } else {
          this.toast.show('No hay tareas pendientes para este documento.', 'info');
          this.importing.set(null);
        }
      },
      error: (err) => {
        this.toast.show('Error al recuperar las tareas del documento.', 'error');
        this.importing.set(null);
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

  formatBytes(bytes: number): string {
    if (!bytes && bytes !== 0) return '-';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }
}