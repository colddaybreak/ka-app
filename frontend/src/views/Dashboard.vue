<!-- frontend/src/views/Dashboard.vue -->
<template>
  <div>
    <h2>仪表盘</h2>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="知识库数量" :value="stats.knowledgeBaseCount" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="文档数量" :value="stats.documentCount" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="对话数量" :value="stats.conversationCount" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="今日对话" :value="stats.todayConversationCount" />
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 20px">
      <template #header>对话趋势（近 30 天）</template>
      <div ref="chartRef" style="height: 300px">
        <el-empty v-if="!trends.length" description="暂无数据" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue';
import client from '@/api/client';

const stats = reactive({
  knowledgeBaseCount: 0,
  documentCount: 0,
  conversationCount: 0,
  todayConversationCount: 0,
});

const trends = ref<any[]>([]);
const chartRef = ref<HTMLDivElement>();

onMounted(async () => {
  try {
    const [statsRes, trendsRes] = await Promise.all([
      client.get('/dashboard/stats'),
      client.get('/dashboard/trends?days=30'),
    ]) as any[];

    Object.assign(stats, statsRes);
    trends.value = trendsRes?.conversations || [];
  } catch {
    // 错误已在 interceptor 中处理
  }
});
</script>
