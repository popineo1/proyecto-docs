import { Injectable, computed, signal } from '@angular/core';
import { StorageService } from './storage.service';
import { MeResponse } from '../interfaces/auth.interface';

const TOKEN_KEY = 'docs_token';
const USER_KEY = 'docs_user';

@Injectable({ providedIn: 'root' })
export class AuthStateService {
  private readonly tokenSignal = signal<string | null>(null);
  private readonly userSignal = signal<MeResponse | null>(null);

  readonly token = computed(() => this.tokenSignal());
  readonly user = computed(() => this.userSignal());
  readonly isAuthenticated = computed(() => !!this.tokenSignal());

  constructor(private storage: StorageService) {
    const savedToken = this.storage.get<string>(TOKEN_KEY);
    const savedUser = this.storage.get<MeResponse>(USER_KEY);

    if (savedToken) this.tokenSignal.set(savedToken);
    if (savedUser) this.userSignal.set(savedUser);
  }

  setToken(token: string): void {
    this.tokenSignal.set(token);
    this.storage.set(TOKEN_KEY, token);
  }

  setUser(user: MeResponse | null): void {
    this.userSignal.set(user);
    if (user) this.storage.set(USER_KEY, user);
    else this.storage.remove(USER_KEY);
  }

  logout(): void {
    this.tokenSignal.set(null);
    this.userSignal.set(null);
    this.storage.remove(TOKEN_KEY);
    this.storage.remove(USER_KEY);
  }
}
