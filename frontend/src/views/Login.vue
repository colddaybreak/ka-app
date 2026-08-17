<!-- frontend/src/views/Login.vue -->
<template>
  <div class="login-container">
    <el-card style="width: 400px; margin: 100px auto">
      <template #header>
        <h2 style="text-align: center; margin: 0">知识库助手管理平台</h2>
      </template>

      <el-form :model="form" @submit.prevent="handleSubmit">
        <el-form-item label="邮箱">
          <el-input v-model="form.email" type="email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" />
        </el-form-item>
        <el-form-item v-if="isRegister" label="姓名">
          <el-input v-model="form.name" placeholder="请输入姓名" />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            style="width: 100%"
            :loading="loading"
            @click="handleSubmit"
          >
            {{ isRegister ? '注册' : '登录' }}
          </el-button>
        </el-form-item>

        <div style="text-align: center">
          <el-button text @click="isRegister = !isRegister">
            {{ isRegister ? '已有账号？去登录' : '没有账号？去注册' }}
          </el-button>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { ElMessage } from 'element-plus';

const router = useRouter();
const auth = useAuthStore();
const loading = ref(false);
const isRegister = ref(false);

const form = reactive({
  email: '',
  password: '',
  name: '',
});

async function handleSubmit() {
  if (!form.email || !form.password) {
    ElMessage.warning('请填写邮箱和密码');
    return;
  }
  loading.value = true;
  try {
    if (isRegister.value) {
      await auth.register(form.email, form.password, form.name);
    } else {
      await auth.login(form.email, form.password);
    }
    router.push('/');
  } catch {
    // 错误已在 interceptor 中处理
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  background: #f5f7fa;
}
</style>
