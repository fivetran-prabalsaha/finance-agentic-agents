import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';

/** Guard that requires user to be authenticated. */
export const authGuard: CanActivateFn = (_route, _state) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (auth.isLoggedIn()) return true;
  return router.createUrlTree(['/login']);
};

/** Guard factory that requires minimum authority level. */
export function levelGuard(minLevel: number): CanActivateFn {
  return (_route, _state) => {
    const auth = inject(AuthService);
    const router = inject(Router);
    if (!auth.isLoggedIn()) return router.createUrlTree(['/login']);
    if (auth.hasLevel(minLevel)) return true;
    return router.createUrlTree(['/dashboard']); // redirect down to dashboard
  };
}
