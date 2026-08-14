export type ApiError = {
  error?: {
    message?: string
  }
}

export class ApiRequestError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message)
    this.name = 'ApiRequestError'
  }
}

export const ACCESS_TOKEN_STORAGE_KEY = 'interview-copilot-access-token'
export const AUTH_LOGOUT_EVENT = 'interview-copilot-auth-logout'

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)
}

export function setAccessToken(token: string): void {
  localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token)
}

export function clearAccessToken(): void {
  localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY)
}

function notifyAuthLogout(): void {
  window.dispatchEvent(new Event(AUTH_LOGOUT_EVENT))
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
  _userId?: string,
): Promise<T> {
  const headers = new Headers(options.headers)

  const token = getAccessToken()
  const hadToken = Boolean(token)

  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  if (
    options.body &&
    !(options.body instanceof FormData)
  ) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(path, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as ApiError

    if (response.status === 401 && hadToken) {
      clearAccessToken()
      notifyAuthLogout()
    }

    throw new ApiRequestError(
      body.error?.message ?? `请求失败 (${response.status})`,
      response.status,
    )
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}
