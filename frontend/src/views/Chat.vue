<!-- frontend/src/views/Chat.vue -->
<template>
  <div class="chat-container">
    <!-- 消息列表 -->
    <div class="messages" ref="messagesRef">
      <div
        v-for="msg in messages"
        :key="msg.id"
        :class="['message', msg.role]"
      >
        <div class="role-label">{{ msg.role === 'user' ? '你' : '助手' }}</div>
        <div class="content" v-html="renderMarkdown(msg.content)"></div>
        <!-- 引用来源 -->
        <div v-if="msg.citations?.length" class="citations">
          <el-collapse>
            <el-collapse-item :title="`参考来源 (${msg.citations.length})`">
              <div v-for="cite in msg.citations" :key="cite.chunk_id" class="citation-item">
                <strong>{{ cite.document_name }}</strong>
                <span class="similarity">相似度: {{ (cite.similarity * 100).toFixed(1) }}%</span>
                <p>{{ cite.content_snippet }}</p>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>

      <!-- 流式输出中的助手回复 -->
      <div v-if="isStreaming" class="message assistant">
        <div class="role-label">助手</div>
        <div class="content" v-html="renderMarkdown(streamingContent)"></div>
      </div>
    </div>

    <!-- 输入框 -->
    <div class="input-area">
      <el-input
        v-model="inputMessage"
        placeholder="输入消息..."
        @keyup.enter="sendMessage"
        :disabled="isStreaming"
      />
      <el-button type="primary" @click="sendMessage" :loading="isStreaming">
        发送
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue';
import { useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { streamChat } from '@/api/chatStream';
import client from '@/api/client';
import MarkdownIt from 'markdown-it';
import { ElMessage } from 'element-plus';

const md = new MarkdownIt({ html: false, linkify: true, breaks: true });

const route = useRoute();
const auth = useAuthStore();
const conversationId = route.params.id as string;

const messages = ref<any[]>([]);
const inputMessage = ref('');
const isStreaming = ref(false);
const streamingContent = ref('');
const messagesRef = ref<HTMLDivElement>();

function renderMarkdown(text: string) {
  return md.render(text || '');
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight;
    }
  });
}

async function fetchMessages() {
  try {
    const res: any = await client.get(`/conversations/${conversationId}`);
    messages.value = res.messages || [];
    scrollToBottom();
  } catch { /* handled */ }
}

async function sendMessage() {
  const text = inputMessage.value.trim();
  if (!text || isStreaming.value) return;

  // 添加用户消息到界面
  messages.value.push({
    id: Date.now().toString(),
    role: 'user',
    content: text,
  });
  inputMessage.value = '';
  isStreaming.value = true;
  streamingContent.value = '';
  scrollToBottom();

  try {
    await streamChat(
      {
        conversation_id: conversationId,
        message: text,
      },
      auth.token,
      {
        onToken(token: string) {
          streamingContent.value += token;
          scrollToBottom();
        },
        onCitations(_citations: any[]) {
          // 引用来源将在 done 事件中一起保存
        },
        onDone(fullContent: string) {
          messages.value.push({
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: fullContent,
          });
          streamingContent.value = '';
          isStreaming.value = false;
          scrollToBottom();
        },
        onError(error: string) {
          ElMessage.error(error);
          isStreaming.value = false;
        },
      },
    );
  } catch {
    isStreaming.value = false;
    ElMessage.error('发送失败');
  }
}

onMounted(fetchMessages);
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 100px);
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.message {
  margin-bottom: 20px;
  max-width: 80%;
}

.message.user {
  margin-left: auto;
  text-align: right;
}

.message.assistant {
  margin-right: auto;
}

.role-label {
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
}

.content {
  background: #f5f7fa;
  padding: 12px 16px;
  border-radius: 8px;
  text-align: left;
}

.message.user .content {
  background: #409eff;
  color: white;
}

.citations {
  margin-top: 8px;
  text-align: left;
}

.citation-item {
  padding: 8px;
  border-bottom: 1px solid #eee;
}

.citation-item .similarity {
  margin-left: 8px;
  color: #67c23a;
  font-size: 12px;
}

.citation-item p {
  margin: 4px 0 0;
  font-size: 13px;
  color: #666;
}

.input-area {
  display: flex;
  gap: 10px;
  padding: 16px;
  border-top: 1px solid #eee;
}

.input-area .el-input {
  flex: 1;
}
</style>
