import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap, catchError, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import { LoginResponse, User } from '../models/user.model';

@Injectable({ providedIn: 'root' })
export class AuthService {
  // JWT stored in-memory only (not localStorage — XSS risk)
  private _token: string | null = null;
  private _user = signal<User | null>(null);

  readonly currentUser = this._user.asReadonly();

  constructor(private http: HttpClient, private router: Router) {}

  login(email: string, password: string): Observable<LoginResponse> {
    return this.http
      .post<LoginResponse>(`${environment.apiUrl}/auth/login`, { email, password })
      .pipe(
        tap((res) => {
          this._token = res.access_token;
          this._user.set(res.user);
        }),
        catchError((err) => {
          const msg = err.error?.detail ?? 'Login failed';
          return throwError(() => new Error(msg));
        }),
      );
  }

  refreshMe(): Observable<User> {
    return this.http.get<User>(`${environment.apiUrl}/auth/me`).pipe(
      tap((user) => this._user.set(user)),
      catchError(() => {
        this.logout();
        return throwError(() => new Error('Session expired'));
      }),
    );
  }

  logout(): void {
    this._token = null;
    this._user.set(null);
    this.router.navigate(['/login']);
  }

  getToken(): string | null {
    return this._token;
  }

  isLoggedIn(): boolean {
    return this._token !== null;
  }

  get level(): number {
    return this._user()?.level ?? 0;
  }

  hasLevel(minLevel: number): boolean {
    return this.level >= minLevel;
  }
}
