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
              <el-button type="primary" size="small" @click="openUploadDialog">
                上传文档
              </el-button>
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
            <el-table-column label="元数据" min-width="180">
              <template #default="{ row }">
                <span class="meta-summary">{{ metaSummary(row.metadata) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <el-button text type="primary" size="small" @click="openMetaEdit(row)">
                  元数据
                </el-button>
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

            <el-form-item label="元数据筛选">
              <el-switch v-model="metaFilterOn" :disabled="!metadataSchema.length" />
              <div v-if="metaFilterOn" class="meta-rows" style="width: 100%">
                <div v-for="s in metadataSchema" :key="s.key" class="meta-row">
                  <span class="meta-key">{{ s.key }}</span>
                  <el-input
                    v-if="inputType(s) === 'string'"
                    v-model="retrievalConfig.metadataFilter[s.key]"
                    size="small" placeholder="筛选值"
                  />
                  <el-input-number
                    v-else-if="inputType(s) === 'number'"
                    v-model="retrievalConfig.metadataFilter[s.key]"
                    size="small" :controls="false" placeholder="筛选值"
                  />
                  <el-switch
                    v-else-if="inputType(s) === 'boolean'"
                    v-model="retrievalConfig.metadataFilter[s.key]"
                  />
                  <el-date-picker
                    v-else-if="inputType(s) === 'date'"
                    v-model="retrievalConfig.metadataFilter[s.key]"
                    type="date" value-format="YYYY-MM-DD" size="small"
                    style="width: 130px" placeholder="筛选日期"
                  />
                  <el-select
                    v-else-if="inputType(s) === 'enum'"
                    v-model="retrievalConfig.metadataFilter[s.key]"
                    size="small" clearable placeholder="选择" style="width: 130px"
                  >
                    <el-option v-for="o in s.options || []" :key="o" :label="o" :value="o" />
                  </el-select>
                </div>
              </div>
            </el-form-item>

            <el-form-item label="元数据模板">
              <div style="display: flex; gap: 8px; align-items: center">
                <span class="meta-summary">{{ templateSummary }}</span>
                <el-button size="small" @click="openTemplateEditor">编辑模板</el-button>
              </div>
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

    <!-- 上传文档对话框 -->
    <el-dialog v-model="showUploadDialog" title="上传文档" width="560px">
      <el-form label-position="top" size="small">
        <el-form-item label="文件">
          <el-upload
            ref="uploadRef"
            :action="`/api/documents/upload/${kbId}`"
            :headers="uploadHeaders"
            :data="uploadData"
            :on-success="onUploadSuccess"
            :on-error="onUploadError"
            :on-change="onFileChange"
            :on-remove="onFileRemove"
            :auto-upload="false"
            :limit="1"
            accept=".pdf,.txt,.md,.docx,.html"
          >
            <el-button size="small">选择文件</el-button>
          </el-upload>
        </el-form-item>

        <el-form-item label="启用元数据">
          <el-switch v-model="enableMeta" />
          <span v-if="enableMeta && !metadataSchema.length" class="form-tip">
            该知识库尚未定义元数据模板，请先编辑模板
          </span>
        </el-form-item>

        <template v-if="enableMeta && metadataSchema.length">
          <el-form-item label="元数据值">
            <div class="meta-rows" style="width: 100%">
              <div v-for="s in metadataSchema" :key="s.key" class="meta-row">
                <span class="meta-key">{{ s.key }}</span>
                <span class="meta-desc">{{ s.description }}</span>
                <el-input
                  v-if="inputType(s) === 'string'"
                  v-model="metaValues[s.key]" size="small" placeholder="填写值"
                />
                <el-input-number
                  v-else-if="inputType(s) === 'number'"
                  v-model="metaValues[s.key]" size="small" :controls="false" placeholder="填写值"
                />
                <el-switch
                  v-else-if="inputType(s) === 'boolean'"
                  v-model="metaValues[s.key]"
                />
                <el-date-picker
                  v-else-if="inputType(s) === 'date'"
                  v-model="metaValues[s.key]" type="date" value-format="YYYY-MM-DD"
                  size="small" style="width: 150px" placeholder="选择日期"
                />
                <el-select
                  v-else-if="inputType(s) === 'enum'"
                  v-model="metaValues[s.key]" size="small" clearable
                  placeholder="选择" style="width: 150px"
                >
                  <el-option v-for="o in s.options || []" :key="o" :label="o" :value="o" />
                </el-select>
              </div>
            </div>
          </el-form-item>
          <el-form-item label="AI 按说明自动填写">
            <el-switch v-model="autoExtract" />
            <span class="form-tip">后台调用大模型根据文档内容与字段说明生成值，可稍后编辑</span>
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!hasFile" @click="confirmUpload">
          上传
        </el-button>
      </template>
    </el-dialog>

    <!-- 元数据模板编辑对话框 -->
    <el-dialog v-model="showTemplateDialog" title="编辑元数据模板" width="680px">
      <div v-for="(s, i) in schemaEdit" :key="i" class="schema-row">
        <el-input v-model="s.key" size="small" placeholder="字段键" style="width: 140px" />
        <el-select v-model="s.type" size="small" style="width: 105px">
          <el-option v-for="t in ['string', 'number', 'boolean', 'date', 'enum']" :key="t" :label="t" :value="t" />
        </el-select>
        <el-input
          v-model="s.description" size="small" placeholder="字段说明（供 AI 填值参考）" style="flex: 1"
        />
        <el-input
          v-if="s.type === 'enum'" v-model="s.optionsStr" size="small"
          placeholder="枚举值，逗号分隔" style="width: 190px"
        />
        <el-button text type="danger" size="small" @click="schemaEdit.splice(i, 1)">删</el-button>
      </div>
      <el-button size="small" @click="schemaEdit.push({ key: '', type: 'string', description: '', optionsStr: '' })">
        + 添加字段
      </el-button>
      <template #footer>
        <el-button @click="showTemplateDialog = false">取消</el-button>
        <el-button type="primary" @click="saveSchema">保存</el-button>
      </template>
    </el-dialog>

    <!-- 文档元数据编辑对话框 -->
    <el-dialog v-model="showMetaEditDialog" :title="`编辑元数据 - ${editDoc?.filename || ''}`" width="520px">
      <div v-if="!metadataSchema.length" class="form-tip">该知识库未定义元数据模板</div>
      <div v-for="s in metadataSchema" :key="s.key" class="meta-row">
        <span class="meta-key">{{ s.key }}</span>
        <el-input
          v-if="inputType(s) === 'string'"
          v-model="editMetaValues[s.key]" size="small" placeholder="填写值"
        />
        <el-input-number
          v-else-if="inputType(s) === 'number'"
          v-model="editMetaValues[s.key]" size="small" :controls="false" placeholder="填写值"
        />
        <el-switch v-else-if="inputType(s) === 'boolean'" v-model="editMetaValues[s.key]" />
        <el-date-picker
          v-else-if="inputType(s) === 'date'"
          v-model="editMetaValues[s.key]" type="date" value-format="YYYY-MM-DD"
          size="small" style="width: 150px" placeholder="选择日期"
        />
        <el-select
          v-else-if="inputType(s) === 'enum'"
          v-model="editMetaValues[s.key]" size="small" clearable
          placeholder="选择" style="width: 150px"
        >
          <el-option v-for="o in s.options || []" :key="o" :label="o" :value="o" />
        </el-select>
      </div>
      <template #footer>
        <el-button @click="showMetaEditDialog = false">取消</el-button>
        <el-button type="primary" @click="saveDocMeta">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue';
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
  metadataFilter: {},
};
const retrievalConfig = reactive<any>({ ...DEFAULT_RETRIEVAL_CONFIG });

// 元数据模板（kb.metadataSchema）：[{key, type, description, options}]
const metadataSchema = computed<any[]>(() => {
  const raw = kb.value?.metadataSchema;
  if (!raw) return [];
  if (typeof raw === 'string') {
    try { return JSON.parse(raw); } catch { return []; }
  }
  return Array.isArray(raw) ? raw : [];
});
const templateSummary = computed(() =>
  metadataSchema.value.length ? metadataSchema.value.map((s) => s.key).join(', ') : '未定义',
);
function inputType(s: any) {
  return s?.type || 'string';
}
function metaSummary(meta: any) {
  if (!meta || typeof meta !== 'object') return '-';
  const entries = Object.entries(meta).filter(([, v]) => v !== undefined && v !== null);
  if (!entries.length) return '-';
  return entries.map(([k, v]) => `${k}: ${v}`).join(' · ');
}

// ===== 上传对话框 =====
const showUploadDialog = ref(false);
const uploadRef = ref<any>(null);
const hasFile = ref(false);
const enableMeta = ref(false);
const autoExtract = ref(false);
const metaValues = reactive<Record<string, any>>({});

const uploadData = computed(() => {
  const metadata = enableMeta.value && metadataSchema.value.length ? { ...metaValues } : {};
  return {
    metadata: JSON.stringify(metadata),
    autoExtract: autoExtract.value ? 'true' : 'false',
  };
});

function resetMetaValues() {
  for (const k of Object.keys(metaValues)) delete metaValues[k];
  for (const s of metadataSchema.value) metaValues[s.key] = undefined;
}

function openUploadDialog() {
  enableMeta.value = false;
  autoExtract.value = false;
  hasFile.value = false;
  resetMetaValues();
  showUploadDialog.value = true;
}
function onFileChange() { hasFile.value = true; }
function onFileRemove() { hasFile.value = false; }
function confirmUpload() {
  if (!hasFile.value) {
    ElMessage.warning('请先选择文件');
    return;
  }
  uploadRef.value?.submit();
}
function onUploadError() {
  ElMessage.error('上传失败');
  showUploadDialog.value = false;
}

// ===== 元数据模板编辑 =====
const showTemplateDialog = ref(false);
const schemaEdit = ref<any[]>([]);

function openTemplateEditor() {
  schemaEdit.value = metadataSchema.value.map((s) => ({
    ...s,
    optionsStr: Array.isArray(s.options) ? s.options.join(',') : '',
  }));
  showTemplateDialog.value = true;
}
async function saveSchema() {
  const cleaned = schemaEdit.value
    .map((s) => ({
      key: (s.key || '').trim(),
      type: s.type,
      description: (s.description || '').trim(),
      options: s.type === 'enum'
        ? String(s.optionsStr || '').split(',').map((o: string) => o.trim()).filter(Boolean)
        : undefined,
    }))
    .filter((s) => s.key);
  const keys = cleaned.map((s) => s.key);
  if (new Set(keys).size !== keys.length) {
    ElMessage.warning('字段键不能重复');
    return;
  }
  try {
    await client.put(`/knowledge-bases/${kbId}`, { metadataSchema: cleaned });
    ElMessage.success('元数据模板已保存');
    showTemplateDialog.value = false;
    fetchDetail();
  } catch { /* handled */ }
}

// ===== 文档元数据编辑 =====
const showMetaEditDialog = ref(false);
const editDoc = ref<any>(null);
const editMetaValues = reactive<Record<string, any>>({});

function openMetaEdit(row: any) {
  editDoc.value = row;
  for (const k of Object.keys(editMetaValues)) delete editMetaValues[k];
  for (const s of metadataSchema.value) {
    editMetaValues[s.key] = row.metadata?.[s.key] ?? undefined;
  }
  showMetaEditDialog.value = true;
}
async function saveDocMeta() {
  try {
    await client.patch(`/documents/${editDoc.value.id}/metadata`, {
      metadata: { ...editMetaValues },
    });
    ElMessage.success('元数据已更新');
    showMetaEditDialog.value = false;
    fetchDocuments();
  } catch { /* handled */ }
}

// 元数据筛选开关（检索配置的一部分，入库为空对象时不生效）
const metaFilterOn = ref(false);

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
    // 数据过滤开关按已有配置恢复（metadataFilter 非空即开启）
    const mf = retrievalConfig.metadataFilter;
    metaFilterOn.value = !!mf && typeof mf === 'object' && Object.keys(mf).length > 0;
  } catch { /* handled */ }
}

async function saveRetrievalConfig() {
  try {
    await client.put(`/knowledge-bases/${kbId}`, {
      retrievalConfig: {
        ...retrievalConfig,
        // 开关关闭时重置为空对象（后端空过滤不生效）
        metadataFilter: metaFilterOn.value ? retrievalConfig.metadataFilter || {} : {},
      },
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
  showUploadDialog.value = false;
  resetMetaValues();
  fetchDocuments();
  // 轮询直至全部文档处理完成（pending/processing -> done/failed）
  startPolling();
}

let pollTimer: ReturnType<typeof setInterval> | null = null;

function startPolling() {
  stopPolling();
  pollTimer = setInterval(async () => {
    await fetchDocuments();
    const processing = documents.value.some(
      (d) => d.status === 'pending' || d.status === 'processing',
    );
    if (!processing) stopPolling();
  }, 3000);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

onBeforeUnmount(stopPolling);

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

<style scoped>
.meta-rows {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.meta-key {
  min-width: 90px;
  font-weight: 600;
  font-size: 13px;
}
.meta-desc {
  flex: 1;
  color: #999;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.meta-summary {
  color: #666;
  font-size: 12px;
}
.form-tip {
  margin-left: 8px;
  color: #999;
  font-size: 12px;
}
.schema-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}
</style>
