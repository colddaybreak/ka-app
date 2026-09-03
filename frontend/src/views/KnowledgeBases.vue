<!-- frontend/src/views/KnowledgeBases.vue -->
<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center">
      <h2>知识库</h2>
      <el-button type="primary" @click="showCreateDialog = true">创建知识库</el-button>
    </div>

    <el-table :data="knowledgeBases" style="margin-top: 20px" v-loading="loading">
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="description" label="描述" />
      <el-table-column prop="embeddingModel" label="Embedding 模型" />
      <el-table-column prop="createdAt" label="创建时间">
        <template #default="{ row }">
          {{ new Date(row.createdAt).toLocaleDateString() }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button text type="primary" @click="router.push(`/knowledge-bases/${row.id}`)">
            详情
          </el-button>
          <el-popconfirm title="确定删除？" @confirm="deleteKB(row.id)">
            <template #reference>
              <el-button text type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 创建对话框 -->
    <el-dialog v-model="showCreateDialog" title="创建知识库" width="500px">
      <el-form :model="newKB">
        <el-form-item label="名称">
          <el-input v-model="newKB.name" placeholder="知识库名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newKB.description" type="textarea" placeholder="知识库描述（可选）" />
        </el-form-item>
        <el-form-item label="检索模式">
          <el-radio-group v-model="retrievalMode">
            <el-radio-button value="vector">向量</el-radio-button>
            <el-radio-button value="keyword">关键词</el-radio-button>
            <el-radio-button value="hybrid">混合</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createKB">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue';
import { useRouter } from 'vue-router';
import client from '@/api/client';
import { ElMessage } from 'element-plus';

const router = useRouter();
const loading = ref(false);
const knowledgeBases = ref<any[]>([]);
const showCreateDialog = ref(false);
const newKB = reactive({ name: '', description: '' });
const retrievalMode = ref('vector');

async function fetchList() {
  loading.value = true;
  try {
    knowledgeBases.value = (await client.get('/knowledge-bases')) as any;
  } catch { /* handled */ }
  loading.value = false;
}

async function createKB() {
  if (!newKB.name) {
    ElMessage.warning('请输入知识库名称');
    return;
  }
  try {
    await client.post('/knowledge-bases', {
      ...newKB,
      retrievalConfig: { mode: retrievalMode.value },
    });
    showCreateDialog.value = false;
    newKB.name = '';
    newKB.description = '';
    retrievalMode.value = 'vector';
    ElMessage.success('创建成功');
    fetchList();
  } catch { /* handled */ }
}

async function deleteKB(id: string) {
  try {
    await client.delete(`/knowledge-bases/${id}`);
    ElMessage.success('删除成功');
    fetchList();
  } catch { /* handled */ }
}

onMounted(fetchList);
</script>
