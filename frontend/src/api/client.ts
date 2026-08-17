// frontend/src/api/client.ts
import axios from 'axios';
import { useAuthStore } from '@/stores/auth';
import { ElMessage } from 'element-plus';
import router from '@/router';

const client = axios.create({ baseURL: '/api', timeout: 30000 });

// 请求拦截器：自动附加 JWT
client.interceptors.request.use((config) => {
  const auth = useAuthStore();
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`;
  }
  return config;
});

// 响应拦截器：统一错误处理
client.interceptors.response.use(
  (res) => res.data,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore().logout();
      router.push('/login');
      ElMessage.error('登录已过期，请重新登录');
    } else {
      ElMessage.error(err.response?.data?.error || '请求失败');
    }
    return Promise.reject(err);
  },
);

export default client;
