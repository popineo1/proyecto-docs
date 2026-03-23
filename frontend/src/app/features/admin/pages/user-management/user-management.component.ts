import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AdminService, AdminUser } from '../../../../core/services/admin.service';

@Component({
  selector: 'app-user-management',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './user-management.component.html',
  styles: [`
    .status-badge {
      @apply px-2 py-1 rounded-full text-xs font-semibold;
    }
  `]
})
export class UserManagementComponent implements OnInit {
  private adminService = inject(AdminService);
  
  users = signal<AdminUser[]>([]);
  loading = signal(false);
  error = signal<string | null>(null);

  ngOnInit() {
    this.loadUsers();
  }

  loadUsers() {
    this.loading.set(true);
    this.adminService.getUsers().subscribe({
      next: (users) => {
        this.users.set(users);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set('Error loading users. Please try again later.');
        this.loading.set(false);
      }
    });
  }

  toggleStatus(user: AdminUser) {
    if (confirm(`¿Estás seguro de que quieres ${user.is_active ? 'bloquear' : 'desbloquear'} a ${user.full_name}?`)) {
      this.adminService.toggleUserActive(user.id).subscribe({
        next: (updatedUser) => {
          this.users.update(users => 
            users.map(u => u.id === updatedUser.id ? updatedUser : u)
          );
        },
        error: (err) => alert('No se pudo cambiar el estado del usuario.')
      });
    }
  }

  deleteUser(user: AdminUser) {
    if (confirm(`⚠️ ALERTA: ¿Estás seguro de que quieres ELIMINAR permanentemente a ${user.full_name}? Esta acción no se puede deshacer.`)) {
      this.adminService.deleteUser(user.id).subscribe({
        next: () => {
          this.users.update(users => users.filter(u => u.id !== user.id));
        },
        error: (err) => alert('No se pudo eliminar al usuario.')
      });
    }
  }
}
