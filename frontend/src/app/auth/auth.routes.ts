import { Routes } from '@angular/router';
import { LoginPageComponent } from './pages/login-page/login-page.component';
import { RegisterPageComponent } from './pages/register-page/register-page.component';

const authRoutes: Routes = [
  { path: 'login', component: LoginPageComponent, title: 'Iniciar sesión | Proyecto Docs' },
  { path: 'register', component: RegisterPageComponent, title: 'Registro | Proyecto Docs' },
  { path: '', pathMatch: 'full', redirectTo: 'login' },
];

export default authRoutes;
