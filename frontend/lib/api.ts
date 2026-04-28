/**
 * Base URL for the FastAPI backend (local dev or hosted).
 * Set in `frontend/.env.local`, e.g. NEXT_PUBLIC_API_BASE_URL=https://api.example.com
 */
export function getApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (typeof raw === 'string' && raw.trim().length > 0) {
    return raw.replace(/\/$/, '');
  }
  return 'http://127.0.0.1:8000';
}
