import axios from 'axios';

// API base URL - call backend directly
const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token refresh on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      const refreshToken = localStorage.getItem('refreshToken');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh/`, {
            refresh: refreshToken,
          });
          
          const { access } = response.data;
          localStorage.setItem('accessToken', access);
          
          originalRequest.headers.Authorization = `Bearer ${access}`;
          return api(originalRequest);
        } catch (refreshError) {
          // Refresh failed, clear tokens and retry without auth
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
          
          // Retry the request without the auth header for GET requests
          if (originalRequest.method === 'get') {
            delete originalRequest.headers.Authorization;
            originalRequest._retry = true;
            return api(originalRequest);
          }
        }
      } else {
        // No refresh token, clear access token and retry GET without auth
        localStorage.removeItem('accessToken');
        if (originalRequest.method === 'get') {
          delete originalRequest.headers.Authorization;
          return api(originalRequest);
        }
      }
    }
    
    return Promise.reject(error);
  }
);

/**
 * Fetch all posts with pagination
 */
export const fetchPosts = async (page = 1) => {
  const response = await api.get(`/posts/?page=${page}`);
  return response.data;
};

/**
 * Fetch a single post with its comment tree
 */
export const fetchPost = async (postId) => {
  const response = await api.get(`/posts/${postId}/`);
  return response.data;
};

/**
 * Create a new post
 */
export const createPost = async (body) => {
  const response = await api.post('/posts/', { body });
  return response.data;
};

/**
 * Create a comment on a post or reply to another comment
 */
export const createComment = async (postId, body, parentId = null) => {
  const data = { post: postId, body };
  if (parentId) {
    data.parent = parentId;
  }
  const response = await api.post('/comments/', data);
  return response.data;
};

/**
 * Like a post or comment
 * Returns 201 on success, 409 if already liked
 */
export const like = async (targetType, targetId) => {
  try {
    const data = targetType === 'post' 
      ? { post: targetId } 
      : { comment: targetId };
    const response = await api.post('/like/', data);
    return { success: true, data: response.data };
  } catch (error) {
    if (error.response?.status === 409) {
      return { success: false, alreadyLiked: true };
    }
    throw error;
  }
};

/**
 * Unlike a post or comment
 */
export const unlike = async (targetType, targetId) => {
  const data = targetType === 'post' 
    ? { post: targetId } 
    : { comment: targetId };
  await api.delete('/like/', { data });
  return { success: true };
};

/**
 * Fetch the karma leaderboard (top 5 users in last 24h)
 */
export const fetchLeaderboard = async () => {
  const response = await api.get('/leaderboard/');
  return response.data;
};

export default api;
