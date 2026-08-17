// frontend/src/stores/auth.ts
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import client from '@/api/client';

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '');
  const user = ref<any>(null);

  const isLoggedIn = computed(() => !!token.value);
  const isAdmin = computed(() => user.value?.role === 'admin');

  async function login(email: string, password: string) {
    const res: any = await client.post('/auth/login', { email, password });
    token.value = res.token;
    user.value = res.user;
    localStorage.setItem('token', res.token);
  }

  async function register(email: string, password: string, name: string) {
    const res: any = await client.post('/auth/register', { email, password, name });
    token.value = res.token;
    user.value = res.user;
    localStorage.setItem('token', res.token);
  }

  function logout() {
    token.value = '';
    user.value = null;
    localStorage.removeItem('token');
  }

  return { token, user, isLoggedIn, isAdmin, login, register, logout };
});
