export const authApi = {
  login: async (...args: any[]) => ({ token: 'mock' }),
  register: async (...args: any[]) => ({ token: 'mock' })
};

export const api = {
  get: async (url: string) => {
    const res = await fetch(`/api/v1${url}`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
      }
    });
    if (!res.ok) throw new Error('API Request Failed');
    return res.json();
  },
  post: async (url: string, data: any) => {
    const res = await fetch(`/api/v1${url}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
      },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error('API Request Failed');
    return res.json();
  },
  put: async (url: string, data: any) => {
    const res = await fetch(`/api/v1${url}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
      },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error('API Request Failed');
    return res.json();
  },
  delete: async (url: string) => {
    const res = await fetch(`/api/v1${url}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
      }
    });
    if (!res.ok) throw new Error('API Request Failed');
    return res.json();
  }
};
