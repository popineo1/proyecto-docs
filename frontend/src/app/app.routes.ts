import { Routes } from '@angular/router';
import authRoutes from './auth/auth.routes';
import { guestGuard } from './core/guards/guest.guard';
import { authGuard } from './core/guards/auth.guard';
import { AuthLayoutComponent } from './layouts/auth-layout/auth-layout.component';
import { AppLayoutComponent } from './layouts/app-layout/app-layout.component';
import { DashboardPageComponent } from './dashboard/pages/dashboard-page/dashboard-page.component';
import { SelectTenantPageComponent } from './tenants/pages/select-tenant-page/select-tenant-page.component';
import { DocumentsPageComponent } from './documents/pages/documents-page/documents-page.component';
import { DocumentDetailPageComponent } from './documents/pages/document-detail-page/document-detail-page.component';
import { FinancialEntriesPageComponent } from './financial-entries/financial-entries-page/financial-entries-page.component';
import { FinancialMovementsPageComponent } from './financial-movements/financial-movements-page.component';
import { ManualMovementsPageComponent } from './manual-movements/manual-movements-page.component';
import { ReviewInboxPageComponent } from './review-inbox/review-inbox-page.component';

export const routes: Routes = [
  {
    path: 'auth',
    component: AuthLayoutComponent,
    canMatch: [guestGuard],
    children: authRoutes,
  },
  {
    path: '',
    component: AppLayoutComponent,
    canMatch: [authGuard],
    children: [
      {
        path: 'dashboard',
        component: DashboardPageComponent,
        title: 'Dashboard | Proyecto Docs',
      },
      {
        path: 'financial-movements',
        component: FinancialMovementsPageComponent,
        title: 'Movimientos financieros | Proyecto Docs',
      },
      {
        path: 'review-inbox',
        component: ReviewInboxPageComponent,
        title: 'Bandeja de revisión | Proyecto Docs',
      },
      {
        path: 'manual-movements',
        component: ManualMovementsPageComponent,
        title: 'Movimientos sin factura | Proyecto Docs',
      },
      {
        path: 'documents',
        component: DocumentsPageComponent,
        title: 'Documentos | Proyecto Docs',
      },
      {
        path: 'documents/:id',
        component: DocumentDetailPageComponent,
        title: 'Detalle de documento | Proyecto Docs',
      },
      {
        path: 'financial-entries',
        component: FinancialEntriesPageComponent,
        title: 'Registros financieros | Proyecto Docs',
      },
      {
        path: 'select-tenant',
        component: SelectTenantPageComponent,
        title: 'Seleccionar empresa | Proyecto Docs',
      },
      {
        path: '',
        pathMatch: 'full',
        redirectTo: 'dashboard',
      },
    ],
  },
  {
    path: '**',
    redirectTo: '',
  },
];