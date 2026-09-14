const TOKEN_KEY = 'movie_factory_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

const base = (import.meta.env.VITE_API_BASE || '').replace(/\/+$/, '')

export async function apiFetch(path, { method = 'GET', body, headers = {}, withAuth = true } = {}) {
  const token = getToken()
  const finalHeaders = { 'Content-Type': 'application/json', ...headers }
  if (withAuth && token) finalHeaders.Authorization = `Bearer ${token}`

  let res
  try {
    res = await fetch(`${base}${path}`, {
      method,
      headers: finalHeaders,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(0, 'Không kết nối được máy chủ. Kiểm tra backend đang chạy.')
  }

  if (res.status === 401 && withAuth) {
    clearToken()
    window.location.replace('/login')
    throw new ApiError(401, 'Phiên đăng nhập hết hạn.')
  }

  let data = null
  try {
    data = await res.json()
  } catch {
    data = null
  }
  if (!res.ok) {
    const detail = data && data.detail
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg).join('; ')
          : `Lỗi máy chủ (${res.status})`
    throw new ApiError(res.status, message)
  }
  return data
}