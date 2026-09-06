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
      <div v-if="trends.length" class="trend-chart">
        <div
          v-for="t in trends"
          :key="t.date"
          class="trend-bar-wrap"
          :title="`${t.date}: ${t.count} 次对话`"
        >
          <div class="trend-bar" :style="{ height: barHeight(t.count) + '%' }"></div>
          <span class="trend-date">{{ shortDate(t.date) }}</span>
        </div>
      </div>
      <el-empty v-else description="暂无数据" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue';
import client from '@/api/client';

const stats = reactive({
  knowledgeBaseCount: 0,
  documentCount: 0,
  conversationCount: 0,
  todayConversationCount: 0,
});

const trends = ref<any[]>([]);
const maxCount = computed(() =>
  Math.max(1, ...trends.value.map((t: any) => Number(t.count))),
);

function barHeight(count: number) {
  return Math.max(4, (Number(count) / maxCount.value) * 100);
}

function shortDate(d: string) {
  return d ? d.slice(5) : '';
}

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

<style scoped>
.trend-chart {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 280px;
  padding: 12px 4px 0;
}

.trend-bar-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  height: 100%;
  gap: 6px;
}

.trend-bar {
  width: 100%;
  max-width: 24px;
  background: #409eff;
  border-radius: 3px 3px 0 0;
  min-height: 4px;
}

.trend-date {
  font-size: 11px;
  color: #999;
  white-space: nowrap;
}
</style>
