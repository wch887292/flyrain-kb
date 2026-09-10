<template>
  <div>
    <div class="toolbar">
      <el-radio-group v-model="days" @change="onDaysChange">
        <el-radio-button :value="7">近 7 天</el-radio-button>
        <el-radio-button :value="30">近 30 天</el-radio-button>
        <el-radio-button :value="90">近 90 天</el-radio-button>
      </el-radio-group>
    </div>

    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <!-- 对话分析 -->
      <el-tab-pane label="对话命中率分析" name="chat">
        <el-row :gutter="16" class="stats-cards">
          <el-col :span="6">
            <el-card shadow="hover">
              <div class="card-label">总会话数</div>
              <div class="card-value">{{ chatStats.total_sessions }}</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover">
              <div class="card-label">助手回答数</div>
              <div class="card-value">{{ chatStats.total_assistant_messages }}</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover">
              <div class="card-label">点赞率</div>
              <div class="card-value like">{{ (chatStats.like_rate * 100).toFixed(1) }}%</div>
              <div class="card-sub">{{ chatStats.liked }} 次点赞</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover">
              <div class="card-label">点踩率</div>
              <div class="card-value dislike">{{ (chatStats.dislike_rate * 100).toFixed(1) }}%</div>
              <div class="card-sub">{{ chatStats.disliked }} 次点踩</div>
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="16" style="margin-top:16px">
          <el-col :span="14">
            <el-card shadow="hover">
              <template #header>每日回答与反馈趋势</template>
              <div class="chart">
                <div v-for="d in chatStats.daily" :key="d.day" class="chart-col">
                  <div class="chart-bar-wrap">
                    <div class="chart-bar total" :style="{ height: chatBarHeight(d.total) + '%' }"
                      :title="`回答 ${d.total}`"></div>
                    <div class="chart-bar like" :style="{ height: chatBarHeight(d.liked) + '%' }"
                      :title="`点赞 ${d.liked}`"></div>
                  </div>
                  <div class="chart-label">{{ d.day.slice(5) }}</div>
                </div>
                <el-empty v-if="!chatStats.daily?.length" description="暂无数据" :image-size="60" />
              </div>
              <div class="chart-legend">
                <span><i class="dot total"></i>回答数</span>
                <span><i class="dot like"></i>点赞数</span>
              </div>
            </el-card>
          </el-col>
          <el-col :span="10">
            <el-card shadow="hover">
              <template #header>按应用统计（Top 10）</template>
              <el-table :data="chatStats.by_app" size="small" v-loading="chatLoading">
                <el-table-column prop="app__name" label="应用" min-width="120" show-overflow-tooltip />
                <el-table-column prop="total" label="回答" width="70" align="center" />
                <el-table-column prop="liked" label="点赞" width="60" align="center" />
                <el-table-column prop="disliked" label="点踩" width="60" align="center" />
                <el-table-column label="点赞率" width="80" align="center">
                  <template #default="{ row }">
                    {{ row.total ? ((row.liked / row.total) * 100).toFixed(0) + '%' : '-' }}
                  </template>
                </el-table-column>
              </el-table>
              <el-empty v-if="!chatStats.by_app?.length" description="暂无数据" :image-size="60" />
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- 成本分析 -->
      <el-tab-pane label="模型调用成本分析" name="cost">
        <el-row :gutter="16" class="stats-cards">
          <el-col :span="6">
            <el-card shadow="hover">
              <div class="card-label">总调用次数</div>
              <div class="card-value">{{ costStats.total_calls }}</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover">
              <div class="card-label">总 Token 消耗</div>
              <div class="card-value">{{ formatTokens(costStats.total_tokens) }}</div>
              <div class="card-sub">输入 {{ formatTokens(costStats.total_prompt_tokens) }} / 输出 {{ formatTokens(costStats.total_completion_tokens) }}</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover">
              <div class="card-label">估算总成本</div>
              <div class="card-value cost">${{ costStats.total_estimated_cost?.toFixed(4) }}</div>
              <div class="card-sub">按模型单价计算</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover">
              <div class="card-label">平均响应耗时</div>
              <div class="card-value">{{ (costStats.avg_duration_ms / 1000).toFixed(2) }}s</div>
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="16" style="margin-top:16px">
          <el-col :span="14">
            <el-card shadow="hover">
              <template #header>每日 Token 消耗趋势</template>
              <div class="chart">
                <div v-for="d in costStats.daily" :key="d.day" class="chart-col">
                  <div class="chart-bar-wrap">
                    <div class="chart-bar prompt" :style="{ height: costBarHeight(d.prompt_tokens) + '%' }"
                      :title="`输入 ${d.prompt_tokens}`"></div>
                    <div class="chart-bar completion" :style="{ height: costBarHeight(d.completion_tokens) + '%' }"
                      :title="`输出 ${d.completion_tokens}`"></div>
                  </div>
                  <div class="chart-label">{{ d.day.slice(5) }}</div>
                </div>
                <el-empty v-if="!costStats.daily?.length" description="暂无数据" :image-size="60" />
              </div>
              <div class="chart-legend">
                <span><i class="dot prompt"></i>输入 Token</span>
                <span><i class="dot completion"></i>输出 Token</span>
              </div>
            </el-card>
          </el-col>
          <el-col :span="10">
            <el-card shadow="hover">
              <template #header>按模型统计（Top 10）</template>
              <el-table :data="costStats.by_model" size="small" v-loading="costLoading">
                <el-table-column prop="model_name" label="模型" min-width="120" show-overflow-tooltip />
                <el-table-column prop="calls" label="调用" width="60" align="center" />
                <el-table-column label="Token" width="100" align="center">
                  <template #default="{ row }">{{ formatTokens(row.total_tokens) }}</template>
                </el-table-column>
                <el-table-column label="估算成本" width="90" align="center">
                  <template #default="{ row }">${{ row.estimated_cost?.toFixed(4) }}</template>
                </el-table-column>
              </el-table>
              <el-empty v-if="!costStats.by_model?.length" description="暂无数据" :image-size="60" />
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="16" style="margin-top:16px">
          <el-col :span="24">
            <el-card shadow="hover">
              <template #header>按用户 Token 消耗（Top 10）</template>
              <el-table :data="costStats.by_user" size="small" v-loading="costLoading">
                <el-table-column prop="user__username" label="用户名" width="150" />
                <el-table-column prop="user__nickname" label="昵称" width="150" />
                <el-table-column prop="calls" label="调用次数" width="100" align="center" />
                <el-table-column label="Token 消耗" width="150" align="center">
                  <template #default="{ row }">{{ formatTokens(row.total_tokens) }}</template>
                </el-table-column>
              </el-table>
              <el-empty v-if="!costStats.by_user?.length" description="暂无数据" :image-size="60" />
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { getChatStats } from '@/api/chat'
import { getUsageStats } from '@/api/model'

const days = ref(7)
const activeTab = ref('chat')
const chatLoading = ref(false)
const costLoading = ref(false)

const chatStats = reactive<any>({
  total_sessions: 0, total_assistant_messages: 0, liked: 0, disliked: 0,
  like_rate: 0, dislike_rate: 0, daily: [], by_app: [],
})

const costStats = reactive<any>({
  total_calls: 0, total_prompt_tokens: 0, total_completion_tokens: 0,
  total_tokens: 0, avg_duration_ms: 0, total_estimated_cost: 0,
  daily: [], by_model: [], by_user: [],
})

async function loadChat() {
  chatLoading.value = true
  try {
    const data = await getChatStats({ days: days.value })
    Object.assign(chatStats, data)
  } finally {
    chatLoading.value = false
  }
}

async function loadCost() {
  costLoading.value = true
  try {
    const data = await getUsageStats({ days: days.value })
    Object.assign(costStats, data)
  } finally {
    costLoading.value = false
  }
}

function onDaysChange() {
  if (activeTab.value === 'chat') loadChat()
  else loadCost()
}

function onTabChange(tab: string) {
  if (tab === 'cost') loadCost()
}

function formatTokens(n: number): string {
  if (!n) return '0'
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(2) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}

function chatBarHeight(val: number) {
  const max = Math.max(...(chatStats.daily || []).map((d: any) => d.total), 1)
  return Math.max(2, (val / max) * 100)
}

function costBarHeight(val: number) {
  const max = Math.max(...(costStats.daily || []).map((d: any) => d.prompt_tokens + d.completion_tokens), 1)
  return Math.max(2, (val / max) * 100)
}

onMounted(loadChat)
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
.stats-cards .card-label { font-size: 13px; color: #6b7280; }
.stats-cards .card-value { font-size: 28px; font-weight: 700; margin-top: 8px; }
.stats-cards .card-value.like { color: #67c23a; }
.stats-cards .card-value.dislike { color: #f56c6c; }
.stats-cards .card-value.cost { color: #e6a23c; }
.stats-cards .card-sub { font-size: 12px; color: #9ca3af; margin-top: 4px; }
.chart { display: flex; align-items: flex-end; gap: 4px; height: 200px; padding: 0 8px; }
.chart-col { flex: 1; display: flex; flex-direction: column; align-items: center; height: 100%; }
.chart-bar-wrap { flex: 1; display: flex; align-items: flex-end; gap: 2px; width: 100%; justify-content: center; }
.chart-bar { width: 12px; border-radius: 2px 2px 0 0; min-height: 2px; transition: height 0.3s; }
.chart-bar.total { background: #409eff; }
.chart-bar.like { background: #67c23a; }
.chart-bar.prompt { background: #409eff; }
.chart-bar.completion { background: #e6a23c; }
.chart-label { font-size: 10px; color: #9ca3af; margin-top: 4px; }
.chart-legend { display: flex; gap: 16px; justify-content: center; margin-top: 12px; font-size: 12px; color: #6b7280; }
.chart-legend .dot { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 4px; vertical-align: middle; }
.chart-legend .dot.total { background: #409eff; }
.chart-legend .dot.like { background: #67c23a; }
.chart-legend .dot.prompt { background: #409eff; }
.chart-legend .dot.completion { background: #e6a23c; }
</style>
