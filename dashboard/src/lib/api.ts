import { auth } from './stores';
import { get } from 'svelte/store';

// When served from FastAPI at same origin, use relative URLs
const BASE = typeof window !== 'undefined'
	? (localStorage.getItem('cocobase_api_url') || '')
	: '';

async function request<T>(
	method: string,
	path: string,
	body?: unknown,
	opts: { formData?: FormData } = {}
): Promise<T> {
	const token = get(auth).token;

	const headers: Record<string, string> = {};
	if (token) headers['Authorization'] = `Bearer ${token}`;
	if (body && !opts.formData) headers['Content-Type'] = 'application/json';

	const res = await fetch(`${BASE}${path}`, {
		method,
		headers,
		body: opts.formData ?? (body ? JSON.stringify(body) : undefined)
	});

	if (res.status === 401) {
		auth.logout();
		window.location.href = '/_/ui/login';
		throw new Error('Unauthorized');
	}

	if (!res.ok) {
		const err = await res.json().catch(() => ({ detail: res.statusText }));
		throw new Error(err.detail ?? err.message ?? 'Request failed');
	}

	if (res.status === 204) return undefined as T;
	return res.json();
}

const get_ = <T>(path: string) => request<T>('GET', path);
const post = <T>(path: string, body?: unknown) => request<T>('POST', path, body);
const patch = <T>(path: string, body?: unknown) => request<T>('PATCH', path, body);
const del = <T>(path: string) => request<T>('DELETE', path);

// ─── Auth ─────────────────────────────────────────────────────────────────
export const authApi = {
	login: (email: string, password: string) =>
		post<{ access_token: string; token_type: string }>('/auth/login', { email, password }),
	me: () => get_<User>('/auth/users/me')
};

// ─── Projects ─────────────────────────────────────────────────────────────
export const projectsApi = {
	list: () => get_<Project[]>('/project/'),
	get: (id: string) => get_<Project>(`/project/${id}`),
	create: (payload: { name: string; description?: string }) =>
		post<Project>('/project/', payload),
	update: (id: string, payload: Partial<Project>) =>
		patch<Project>(`/project/${id}`, payload),
	delete: (id: string) => del<void>(`/project/${id}`),
	collections: (id: string) => get_<Collection[]>(`/project/${id}/collections`)
};

// ─── Collections ──────────────────────────────────────────────────────────
export const collectionsApi = {
	documents: (collectionId: string, params?: { limit?: number; offset?: number; sort?: string }) => {
		const q = new URLSearchParams();
		if (params?.limit) q.set('limit', String(params.limit));
		if (params?.offset) q.set('offset', String(params.offset));
		if (params?.sort) q.set('sort', params.sort);
		return get_<DocumentsResponse>(`/collections/${collectionId}/documents?${q}`);
	},
	getDocument: (collectionId: string, docId: string) =>
		get_<Record<string, unknown>>(`/collections/${collectionId}/documents/${docId}`),
	createDocument: (collectionId: string, data: Record<string, unknown>) =>
		post<Record<string, unknown>>('/collections/documents', { collection_id: collectionId, ...data }),
	updateDocument: (collectionId: string, docId: string, data: Record<string, unknown>) =>
		patch<Record<string, unknown>>(`/collections/${collectionId}/documents/${docId}`, data),
	deleteDocument: (collectionId: string, docId: string) =>
		del<void>(`/collections/${collectionId}/documents/${docId}`),
	schema: (collectionId: string) =>
		get_<{ schema: Record<string, unknown> }>(`/collections/${collectionId}/query/schema`),
	count: (collectionId: string) =>
		get_<{ count: number }>(`/collections/${collectionId}/query/documents/count`),
	deleteCollection: (collectionId: string) => del<void>(`/collections/${collectionId}`)
};

// ─── Users ────────────────────────────────────────────────────────────────
export const usersApi = {
	list: (params?: { limit?: number; offset?: number }) => {
		const q = new URLSearchParams();
		if (params?.limit) q.set('limit', String(params.limit));
		if (params?.offset) q.set('offset', String(params.offset));
		return get_<AppUser[]>(`/auth-collections/users?${q}`);
	},
	get: (id: string) => get_<AppUser>(`/auth-collections/users/${id}`)
};

// ─── Storage ──────────────────────────────────────────────────────────────
export const storageApi = {
	list: (projectId: string) =>
		get_<StorageFile[]>(`/storage/files/${projectId}`),
	info: (projectId: string) =>
		get_<StorageInfo>(`/storage/storage-info/${projectId}`),
	upload: (projectId: string, formData: FormData) =>
		request<StorageFile>('POST', `/storage/files/${projectId}`, undefined, { formData }),
	delete: (projectId: string, fileId: string) =>
		del<void>(`/storage/files/${projectId}?file_id=${fileId}`)
};

// ─── Analytics ────────────────────────────────────────────────────────────
export const analyticsApi = {
	overview: () => get_<AnalyticsOverview>('/analytics/overview'),
	usersGrowth: () => get_<unknown>('/analytics/users/growth'),
	collectionsStats: () => get_<unknown>('/analytics/collections/stats')
};

// ─── Email Setup ──────────────────────────────────────────────────────────
export const emailApi = {
	getSmtp: (projectId: string) =>
		get_<SmtpConfig>(`/email-setup/smtp?project_id=${projectId}`),
	updateSmtp: (projectId: string, payload: Partial<SmtpConfig>) =>
		patch<SmtpConfig>(`/email-setup/smtp?project_id=${projectId}`, payload),
	testSmtp: (projectId: string) =>
		post<{ success: boolean; message: string }>(`/email-setup/smtp/test?project_id=${projectId}`),
	logs: (projectId: string) =>
		get_<EmailLog[]>(`/email-setup/logs?project_id=${projectId}`)
};

// ─── ORM Keys ─────────────────────────────────────────────────────────────
export const keysApi = {
	list: (projectId: string) =>
		get_<OrmKey[]>(`/project/${projectId}/orm-keys/`),
	create: (projectId: string, payload: { name: string; permissions?: string[] }) =>
		post<OrmKey>(`/project/${projectId}/orm-keys/`, payload),
	delete: (projectId: string, keyId: string) =>
		del<void>(`/project/${projectId}/orm-keys/${keyId}`)
};

// ─── Health ───────────────────────────────────────────────────────────────
export const healthApi = {
	full: () => get_<HealthStatus>('/health/full')
};

// ─── Types ────────────────────────────────────────────────────────────────
export interface User {
	id: string;
	username: string;
	email: string;
	confirmed_email: boolean;
	created_at: string;
}

export interface Project {
	id: string;
	name: string;
	description?: string;
	created_at: string;
	updated_at?: string;
}

export interface Collection {
	id: string;
	name: string;
	project_id: string;
	created_at: string;
	document_count?: number;
}

export interface DocumentsResponse {
	data: Record<string, unknown>[];
	total?: number;
	limit?: number;
	offset?: number;
}

export interface AppUser {
	id: string;
	email: string;
	username?: string;
	created_at: string;
	confirmed_email?: boolean;
}

export interface StorageFile {
	id: string;
	name: string;
	url: string;
	size: number;
	content_type: string;
	created_at: string;
}

export interface StorageInfo {
	used: number;
	limit: number;
	file_count: number;
}

export interface AnalyticsOverview {
	total_projects?: number;
	total_users?: number;
	total_documents?: number;
	total_storage_used?: number;
	api_requests_today?: number;
	[key: string]: unknown;
}

export interface SmtpConfig {
	host: string;
	port: number;
	username: string;
	password?: string;
	from_email: string;
	from_name?: string;
	use_tls: boolean;
}

export interface EmailLog {
	id: string;
	to: string;
	subject: string;
	status: string;
	created_at: string;
}

export interface OrmKey {
	id: string;
	name: string;
	key: string;
	permissions: string[];
	created_at: string;
}

export interface HealthStatus {
	status: string;
	database?: { status: string };
	redis?: { status: string };
	system?: { cpu_percent: number; memory_percent: number };
}
