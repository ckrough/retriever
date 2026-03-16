import type {
	AskRequest,
	AskResponse,
	MessageHistoryResponse,
	ClearHistoryResponse,
	DocumentListResponse,
	DocumentUploadResponse,
	DocumentDeleteResponse
} from './types';

export class ApiError extends Error {
	constructor(
		public status: number,
		message: string
	) {
		super(message);
		this.name = 'ApiError';
	}
}

export class RetrieverApi {
	private baseUrl: string;
	private token: string;

	constructor(baseUrl: string, token: string) {
		this.baseUrl = baseUrl.replace(/\/$/, '');
		this.token = token;
	}

	private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
		const url = `${this.baseUrl}/api/v1${path}`;
		const headers: Record<string, string> = {
			Authorization: `Bearer ${this.token}`,
			...((options.headers as Record<string, string>) ?? {})
		};

		if (!(options.body instanceof FormData)) {
			headers['Content-Type'] = 'application/json';
		}

		const controller = new AbortController();
		const timeout = setTimeout(() => controller.abort(), 30_000);

		try {
			const response = await fetch(url, {
				...options,
				headers,
				signal: controller.signal
			});

			if (!response.ok) {
				const body = await response.text();
				throw new ApiError(response.status, body || response.statusText);
			}

			return (await response.json()) as T;
		} finally {
			clearTimeout(timeout);
		}
	}

	async ask(question: string): Promise<AskResponse> {
		const body: AskRequest = { question };
		return this.request<AskResponse>('/ask', {
			method: 'POST',
			body: JSON.stringify(body)
		});
	}

	async getHistory(): Promise<MessageHistoryResponse> {
		return this.request<MessageHistoryResponse>('/history');
	}

	async clearHistory(): Promise<ClearHistoryResponse> {
		return this.request<ClearHistoryResponse>('/history', { method: 'DELETE' });
	}

	async listDocuments(): Promise<DocumentListResponse> {
		return this.request<DocumentListResponse>('/documents');
	}

	async uploadDocument(file: File): Promise<DocumentUploadResponse> {
		const formData = new FormData();
		formData.append('file', file);
		return this.request<DocumentUploadResponse>('/documents/upload', {
			method: 'POST',
			body: formData
		});
	}

	async deleteDocument(id: string): Promise<DocumentDeleteResponse> {
		return this.request<DocumentDeleteResponse>(`/documents/${id}`, { method: 'DELETE' });
	}
}
