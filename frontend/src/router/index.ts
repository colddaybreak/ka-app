// frontend/src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const routes = [
  { path: '/login', name: 'Login', component: () => import('@/views/Login.vue') },
  {
    path: '/',
    component: () => import('@/components/layout/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'Dashboard', component: () => import('@/views/Dashboard.vue') },
      { path: 'knowledge-bases', name: 'KnowledgeBases', component: () => import('@/views/KnowledgeBases.vue') },
      { path: 'knowledge-bases/:id', name: 'KnowledgeBaseDetail', component: () => import('@/views/KnowledgeBaseDetail.vue') },
      { path: 'conversations', name: 'Conversations', component: () => import('@/views/Conversations.vue') },
      { path: 'conversations/:id', name: 'Chat', component: () => import('@/views/Chat.vue') },
    ],
  },
];

const router = createRouter({ history: createWebHistory(), routes });

router.beforeEach((to, _from, next) => {
  const auth = useAuthStore();
  if (to.meta.requiresAuth && !auth.token) {
    next('/login');
  } else {
    next();
  }
});

export default router;
