import { Component, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive, Router } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { AuthService } from './core/auth/auth.service';

interface NavItem {
  path: string;
  label: string;
  icon: string;
  minLevel: number;
}

const NAV_ITEMS: NavItem[] = [
  { path: '/dashboard', label: 'Dashboard', icon: 'dashboard', minLevel: 3 },
  { path: '/violations', label: 'Violations', icon: 'warning', minLevel: 3 },
  { path: '/exceptions', label: 'Exceptions', icon: 'shield', minLevel: 3 },
  { path: '/sod-rules', label: 'SOD Rules', icon: 'rule', minLevel: 3 },
  { path: '/configuration/thresholds', label: 'Thresholds', icon: 'tune', minLevel: 4 },
  { path: '/configuration/feature-flags', label: 'Feature Flags', icon: 'flag', minLevel: 5 },
];

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule, RouterOutlet, RouterLink, RouterLinkActive,
    MatToolbarModule, MatSidenavModule, MatListModule, MatIconModule,
    MatButtonModule, MatMenuModule, MatDividerModule,
  ],
  template: `
    <!-- Login page — no shell -->
    <ng-container *ngIf="!auth.isLoggedIn()">
      <router-outlet></router-outlet>
    </ng-container>

    <!-- Authenticated shell -->
    <mat-sidenav-container *ngIf="auth.isLoggedIn()" class="sidenav-container">

      <!-- Side nav -->
      <mat-sidenav mode="side" opened class="sidenav">
        <div class="sidenav-header">
          <mat-icon class="logo-icon">security</mat-icon>
          <div>
            <div class="app-name">SOD Compliance</div>
            <div class="app-sub">Configuration Portal</div>
          </div>
        </div>
        <mat-divider></mat-divider>

        <mat-nav-list>
          <ng-container *ngFor="let item of visibleNavItems()">
            <a
              mat-list-item
              [routerLink]="item.path"
              routerLinkActive="active-link"
            >
              <mat-icon matListItemIcon>{{ item.icon }}</mat-icon>
              <span matListItemTitle>{{ item.label }}</span>
            </a>
          </ng-container>
        </mat-nav-list>

        <mat-divider></mat-divider>
        <div class="user-info">
          <mat-icon>person</mat-icon>
          <div>
            <div class="user-name">{{ auth.currentUser()?.name }}</div>
            <div class="user-level">{{ auth.currentUser()?.level_label }}</div>
          </div>
        </div>
      </mat-sidenav>

      <!-- Main content -->
      <mat-sidenav-content>
        <mat-toolbar color="primary">
          <span class="toolbar-spacer"></span>
          <button mat-icon-button [matMenuTriggerFor]="userMenu">
            <mat-icon>account_circle</mat-icon>
          </button>
          <mat-menu #userMenu>
            <button mat-menu-item disabled>
              <mat-icon>email</mat-icon>
              {{ auth.currentUser()?.email }}
            </button>
            <mat-divider></mat-divider>
            <button mat-menu-item (click)="auth.logout()">
              <mat-icon>logout</mat-icon> Sign Out
            </button>
          </mat-menu>
        </mat-toolbar>

        <router-outlet></router-outlet>
      </mat-sidenav-content>
    </mat-sidenav-container>
  `,
  styles: [`
    .sidenav-container { height: 100vh; }
    .sidenav { width: 240px; background: #1a237e; color: white; }
    .sidenav-header {
      display: flex; align-items: center; gap: 12px;
      padding: 20px 16px;
    }
    .logo-icon { font-size: 32px; width: 32px; height: 32px; color: #7986cb; }
    .app-name { font-size: 15px; font-weight: 700; color: white; }
    .app-sub { font-size: 11px; color: #7986cb; }

    ::ng-deep .sidenav .mat-mdc-list-item { color: rgba(255,255,255,0.8); }
    ::ng-deep .sidenav .mat-mdc-list-item:hover { background: rgba(255,255,255,0.1); color: white; }
    ::ng-deep .sidenav .active-link { background: rgba(255,255,255,0.15) !important; color: white !important; }
    ::ng-deep .sidenav .mat-icon { color: rgba(255,255,255,0.7); }

    .user-info {
      display: flex; align-items: center; gap: 10px;
      padding: 16px; color: rgba(255,255,255,0.7); font-size: 13px;
    }
    .user-name { font-weight: 600; color: white; }
    .user-level { font-size: 11px; color: #7986cb; }

    .toolbar-spacer { flex: 1; }
    mat-toolbar { position: sticky; top: 0; z-index: 10; }
  `],
})
export class AppComponent {
  visibleNavItems = computed(() =>
    NAV_ITEMS.filter((item) => this.auth.hasLevel(item.minLevel)),
  );

  constructor(public auth: AuthService) {}
}
