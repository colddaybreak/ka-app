<!-- frontend/src/views/KnowledgeBaseDetail.vue -->
<template>
  <div>
    <el-page-header @back="router.push('/knowledge-bases')" :title="kb?.name || '加载中...'" />

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>文档列表</span>
              <el-upload
                :action="`/api/documents/upload/${kbId}`"
                :headers="uploadHeaders"
                :on-success="onUploadSuccess"
                :show-file-list="false"
                accept=".pdf,.txt,.md,.docx,.html"
              >
                <el-button type="primary" size="small">上传文档</el-button>
              </el-upload>
            </div>
          </template>

          <el-table :data="documents" v-loading="loadingDocs">
            <el-table-column prop="filename" label="文件名" />
            <el-table-column prop="fileType" label="类型" width="80" />
            <el-table-column label="大小" width="100">
              <template #default="{ row }">
                {{ (row.fileSize / 1024).toFixed(1) }} KB
              </template>
            </el-table-column>
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag
                  :type="row.status === 'done' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'"
                >
                  {{ statusMap[row.status] || row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="chunkCount" label="分块数" width="80" />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-popconfirm title="确定删除？" @confirm="deleteDoc(row.id)">
                  <template #reference>
                    <el-button text type="danger" size="small">删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card>
          <template #header>知识库配置</template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="Embedding 模型">
              {{ kb?.embeddingModel }}
            </el-descriptions-item>
            <el-descriptions-item label="分块策略">
              {{ formatJSON(kb?.chunkStrategy) }}
            </el-descriptions-item>
            <el-descriptions-item label="检索配置">
              {{ formatJSON(kb?.retrievalConfig) }}
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">
              {{ kb ? new Date(kb.createdAt).toLocaleString() : '-' }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card style="margin-top: 20px">
          <template #header>开始对话</template>
          <el-button type="primary" style="width: 100%" @click="startConversation">
            创建新对话
          </el-button>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import client from '@/api/client';
import { ElMessage } from 'element-plus';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const kbId = route.params.id as string;

const kb = ref<any>(null);
const documents = ref<any[]>([]);
const loadingDocs = ref(false);

const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${auth.token}`,
}));

const statusMap: Record<string, string> = {
  pending: '待处理',
  processing: '处理中',
  done: '已完成',
  failed: '失败',
};

function formatJSON(val: any) {
  if (!val) return '-';
  if (typeof val === 'string') {
    try { val = JSON.parse(val); } catch { return val; }
  }
  return JSON.stringify(val, null, 2);
}

async function fetchDetail() {
  try {
    kb.value = await client.get(`/knowledge-bases/${kbId}`) as any;
  } catch { /* handled */ }
}

async function fetchDocuments() {
  loadingDocs.value = true;
  try {
    documents.value = (await client.get(`/documents/knowledge-base/${kbId}`)) as any;
  } catch { /* handled */ }
  loadingDocs.value = false;
}

function onUploadSuccess() {
  ElMessage.success('文档上传成功，正在处理...');
  fetchDocuments();
}

async function deleteDoc(id: string) {
  try {
    await client.delete(`/documents/${id}`);
    ElMessage.success('删除成功');
    fetchDocuments();
  } catch { /* handled */ }
}

async function startConversation() {
  try {
    const res: any = await client.post('/conversations', {
      knowledgeBaseId: kbId,
      title: `对话 - ${kb.value?.name}`,
    });
    router.push(`/conversations/${res.id}`);
  } catch { /* handled */ }
}

onMounted(() => {
  fetchDetail();
  fetchDocuments();
});
</script>
