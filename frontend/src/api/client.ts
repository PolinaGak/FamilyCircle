import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Перехватчик запросов 
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Перехватчик ответов 
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        // Запрашиваем новый access_token
        // refresh_token отправится автоматически в cookie
        const response = await axios.post(
          `${API_URL}/auth/refresh`, 
          {}, // пустое тело
          { 
            withCredentials: true,  // ← ВАЖНО: отправляем cookies
          }
        );
        
        const { access_token } = response.data;
        
        // Сохраняем новый токен
        localStorage.setItem('token', access_token);
        
        // Повторяем оригинальный запрос
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return apiClient(originalRequest);
        
      } catch (refreshError) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);