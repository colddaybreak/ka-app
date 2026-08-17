<!-- frontend/src/components/layout/AppLayout.vue -->
<template>
  <el-container style="height: 100vh">
    <el-aside width="220px" style="background: #1d1e1f">
      <div class="logo" style="color: white; padding: 20px; font-size: 18px; font-weight: bold">
        知识库助手
      </div>
      <el-menu
        :default-active="route.path"
        router
        background-color="#1d1e1f"
        text-color="#bfcbd9"
        active-text-color="#409eff"
      >
        <el-menu-item index="/">
          <el-icon><DataBoard /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/knowledge-bases">
          <el-icon><FolderOpened /></el-icon>
          <span>知识库</span>
        </el-menu-item>
        <el-menu-item index="/conversations">
          <el-icon><ChatDotRound /></el-icon>
          <span>对话</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header
        style="display: flex; align-items: center; justify-content: flex-end; border-bottom: 1px solid #eee"
      >
        <span>{{ auth.user?.name }}</span>
        <el-button text @click="auth.logout()">退出</el-button>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { DataBoard, FolderOpened, ChatDotRound } from '@element-plus/icons-vue';

const route = useRoute();
const auth = useAuthStore();
</script>
