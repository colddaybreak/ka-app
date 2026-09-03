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
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>知识库配置</span>
              <el-button type="primary" size="small" @click="saveRetrievalConfig">
                保存检索配置
              </el-button>
            </div>
          </template>

          <!-- 检索配置表单 -->
          <el-form label-position="top" size="small">
            <el-form-item label="检索模式">
              <el-radio-group v-model="retrievalConfig.mode">
                <el-radio-button value="vector">向量</el-radio-button>
                <el-radio-button value="keyword">关键词</el-radio-button>
                <el-radio-button value="hybrid">混合</el-radio-button>
              </el-radio-group>
            </el-form-item>

            <template v-if="retrievalConfig.mode === 'hybrid'">
              <el-form-item label="融合方式">
                <el-radio-group v-model="retrievalConfig.fusionMethod">
                  <el-radio-button value="rrf">RRF</el-radio-button>
                  <el-radio-button value="weighted">加权</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="retrievalConfig.fusionMethod === 'weighted'" label="向量路权重">
                <el-slider
                  v-model="vectorWeight"
                  :min="0"
                  :max="1"
                  :step="0.1"
                  show-input
                />
              </el-form-item>
            </template>

            <template v-if="retrievalConfig.mode !== 'keyword'">
              <el-form-item label="相似度阈值">
                <el-slider
                  v-model="retrievalConfig.similarityThreshold"
                  :min="0"
                  :max="1"
                  :step="0.05"
                  show-input
                />
              </el-form-item>
            </template>

            <el-form-item label="召回数量 (topK)">
              <el-input-number v-model="retrievalConfig.topK" :min="1" :max="20" />
            </el-form-item>

            <el-form-item label="Rerank 重排序">
              <el-switch v-model="retrievalConfig.useRerank" />
            </el-form-item>
            <el-form-item v-if="retrievalConfig.useRerank" label="重排后保留条数">
              <el-input-number v-model="retrievalConfig.rerankTopN" :min="1" :max="20" />
            </el-form-item>
          </el-form>

          <el-descriptions :column="1" border style="margin-top: 12px">
            <el-descriptions-item label="Embedding 模型">
              {{ kb?.embeddingModel }}
            </el-descriptions-item>
            <el-descriptions-item label="分块策略">
              {{ formatJSON(kb?.chunkStrategy) }}
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
import { ref, reactive, computed, onMounted } from 'vue';
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

// 检索配置（与后端 retrieval_config 对应，缺省值与后端保持一致）
const DEFAULT_RETRIEVAL_CONFIG = {
  mode: 'vector',
  fusionMethod: 'rrf',
  weights: { vector: 0.5, keyword: 0.5 },
  topK: 5,
  similarityThreshold: 0.7,
  useRerank: false,
  rerankTopN: 5,
};
const retrievalConfig = reactive<any>({ ...DEFAULT_RETRIEVAL_CONFIG });

// 权重滑块只暴露向量路权重，关键词路权重取互补值
const vectorWeight = computed({
  get: () => retrievalConfig.weights?.vector ?? 0.5,
  set: (v: number) => {
    retrievalConfig.weights = { vector: v, keyword: +(1 - v).toFixed(1) };
  },
});

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
    // 用知识库已存配置覆盖默认值（旧数据缺失的键由默认值补齐）
    Object.assign(
      retrievalConfig,
      DEFAULT_RETRIEVAL_CONFIG,
      kb.value?.retrievalConfig || {},
    );
  } catch { /* handled */ }
}

async function saveRetrievalConfig() {
  try {
    await client.put(`/knowledge-bases/${kbId}`, {
      retrievalConfig: { ...retrievalConfig },
    });
    ElMessage.success('检索配置已保存');
    fetchDetail();
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
