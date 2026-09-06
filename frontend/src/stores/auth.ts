// frontend/src/stores/auth.ts
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import client from '@/api/client';

function readSavedUser(): any {
  try {
    return JSON.parse(localStorage.getItem('user') || 'null');
  } catch {
    return null;
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '');
  const user = ref<any>(readSavedUser());

  const isLoggedIn = computed(() => !!token.value);
  const isAdmin = computed(() => user.value?.role === 'admin');

  function persistUser(u: any) {
    user.value = u;
    localStorage.setItem('user', JSON.stringify(u));
  }

  async function login(email: string, password: string) {
    const res: any = await client.post('/auth/login', { email, password });
    token.value = res.token;
    localStorage.setItem('token', res.token);
    persistUser(res.user);
  }

  async function register(email: string, password: string, name: string) {
    const res: any = await client.post('/auth/register', { email, password, name });
    token.value = res.token;
    localStorage.setItem('token', res.token);
    persistUser(res.user);
  }

  function logout() {
    token.value = '';
    user.value = null;
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  }

  /** 用服务端数据刷新用户信息（登录后刷新页面时恢复会话） */
  async function fetchMe() {
    const me: any = await client.get('/auth/me');
    persistUser(me);
    return me;
  }

  return { token, user, isLoggedIn, isAdmin, login, register, logout, fetchMe };
});