<!-- frontend/src/views/Conversations.vue -->
<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center">
      <h2>对话</h2>
    </div>

    <el-table :data="conversations" style="margin-top: 20px" v-loading="loading">
      <el-table-column prop="title" label="标题" />
      <el-table-column label="知识库" width="150">
        <template #default="{ row }">
          {{ row.knowledgeBase?.name || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="更新时间" width="180">
        <template #default="{ row }">
          {{ new Date(row.updatedAt).toLocaleString() }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button text type="primary" @click="router.push(`/conversations/${row.id}`)">
            继续对话
          </el-button>
          <el-popconfirm title="确定删除？" @confirm="deleteConversation(row.id)">
            <template #reference>
              <el-button text type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import client from '@/api/client';
import { ElMessage } from 'element-plus';

const router = useRouter();
const loading = ref(false);
const conversations = ref<any[]>([]);

async function fetchList() {
  loading.value = true;
  try {
    conversations.value = (await client.get('/conversations')) as any;
  } catch { /* handled */ }
  loading.value = false;
}

async function deleteConversation(id: string) {
  try {
    await client.delete(`/conversations/${id}`);
    ElMessage.success('删除成功');
    fetchList();
  } catch { /* handled */ }
}

onMounted(fetchList);
</script>
