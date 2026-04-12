import { Routes } from '@angular/router';
import { authGuard, levelGuard } from './core/auth/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },

  {
    path: 'login',
    loadComponent: () => import('./features/login/login.component').then((m) => m.LoginComponent),
  },

  // L3+ routes (Director and above)
  {
    path: 'dashboard',
    canActivate: [authGuard],
    loadComponent: () => import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
  },
  {
    path: 'violations',
    canActivate: [authGuard],
    loadComponent: () => import('./features/violations/violations.component').then((m) => m.ViolationsComponent),
  },
  {
    path: 'exceptions',
    canActivate: [authGuard],
    loadComponent: () => import('./features/exceptions/exceptions.component').then((m) => m.ExceptionsComponent),
  },
  {
    path: 'sod-rules',
    canActivate: [authGuard],
    loadComponent: () => import('./features/sod-rules/sod-rules.component').then((m) => m.SodRulesComponent),
  },

  // L4+ routes (Controller / VP Finance and above)
  {
    path: 'configuration/thresholds',
    canActivate: [levelGuard(4)],
    loadComponent: () => import('./features/configuration/thresholds/thresholds.component').then((m) => m.ThresholdsComponent),
  },

  // L5 routes (CFO / C-Suite only)
  {
    path: 'configuration/feature-flags',
    canActivate: [levelGuard(5)],
    loadComponent: () => import('./features/configuration/feature-flags/feature-flags.component').then((m) => m.FeatureFlagsComponent),
  },

  { path: '**', redirectTo: '/dashboard' },
];
