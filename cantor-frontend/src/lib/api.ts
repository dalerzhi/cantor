// 使用相对路径，通过 Nginx 代理到后端
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

// Helper to get access token from localStorage
const getAccessToken = () => {
  if (typeof window !== 'undefined') {
    const storage = localStorage.getItem('cantor-auth-storage');
    if (storage) {
      const parsed = JSON.parse(storage);
      return parsed.state?.accessToken;
    }
  }
  return null;
};

// Generic API request helper
const apiRequest = async (url: string, options: RequestInit = {}) => {
  const token = getAccessToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...((options.headers as Record<string, string>) || {}),
  };

  // 使用相对路径，通过 Nginx 代理
  const fullUrl = API_BASE_URL ? `${API_BASE_URL}${url}` : url;
  
  const response = await fetch(fullUrl, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '请求失败' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
};

// Auth API
export const authApi = {
  login: async (data: { email: string; password: string; org_slug?: string }) => {
    const result = await apiRequest('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return result;
  },
  register: async (data: { email: string; password: string; name: string; org_name: string; org_slug: string }) => {
    const result = await apiRequest('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return result;
  },
  refresh: async (refreshToken: string) => {
    const result = await apiRequest('/api/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    return result;
  },
  logout: async () => {
    return apiRequest('/api/auth/logout', { method: 'POST' });
  },
  me: async () => {
    return apiRequest('/api/auth/me');
  },
};

// Generic API client
export const api = {
  get: (url: string) => apiRequest(url, { method: 'GET' }),
  post: (url: string, data: any) => apiRequest(url, { method: 'POST', body: JSON.stringify(data) }),
  put: (url: string, data: any) => apiRequest(url, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (url: string) => apiRequest(url, { method: 'DELETE' }),
};
