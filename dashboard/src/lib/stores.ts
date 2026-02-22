import { writable } from 'svelte/store';
import { browser } from '$app/environment';

interface AuthState {
	token: string | null;
	user: { username: string; email: string; id: string } | null;
}

function createAuth() {
	const initial: AuthState = {
		token: browser ? localStorage.getItem('cocobase_token') : null,
		user: browser ? JSON.parse(localStorage.getItem('cocobase_user') ?? 'null') : null
	};

	const { subscribe, set, update } = writable<AuthState>(initial);

	return {
		subscribe,
		login(token: string, user: AuthState['user']) {
			if (browser) {
				localStorage.setItem('cocobase_token', token);
				localStorage.setItem('cocobase_user', JSON.stringify(user));
			}
			set({ token, user });
		},
		logout() {
			if (browser) {
				localStorage.removeItem('cocobase_token');
				localStorage.removeItem('cocobase_user');
			}
			set({ token: null, user: null });
		}
	};
}

export const auth = createAuth();

export const toast = writable<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);

export function showToast(message: string, type: 'success' | 'error' | 'info' = 'info') {
	toast.set({ message, type });
	setTimeout(() => toast.set(null), 3500);
}
