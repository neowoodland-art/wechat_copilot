<template>
  <div class="llm-core-debug">
    <h2>LLM统一入口调试台</h2>

    <section class="panel">
      <h3>场景与配置</h3>
      <div class="row">
        <label>场景
          <select v-model="sceneType" @change="applySceneTemplate">
            <option value="interface_analysis">interface_analysis</option>
            <option value="sop_generation">sop_generation</option>
            <option value="multimodal_chat">multimodal_chat</option>
            <option value="system_evolution">system_evolution</option>
          </select>
        </label>
        <label>协议模式
          <select v-model="protocolMode">
            <option value="standard">standard_json</option>
            <option value="compact">compact_json</option>
          </select>
        </label>
        <label>用户ID
          <input v-model="userId" placeholder="user_001" />
        </label>
        <label>模型偏好
          <select v-model="modelPreference">
            <option value="auto">auto</option>
            <option value="local">local</option>
            <option value="doubao">doubao</option>
            <option value="alibaba">alibaba</option>
          </select>
        </label>
      </div>
      <div class="row">
        <label>max_history
          <input v-model.number="tokenConfig.max_history" type="number" min="0" max="100" />
        </label>
        <label>max_images
          <input v-model.number="tokenConfig.max_images" type="number" min="0" max="10" />
        </label>
        <label>max_text_chars
          <input v-model.number="tokenConfig.max_text_chars" type="number" min="100" max="20000" />
        </label>
      </div>
      <div class="row">
        <button class="btn btn-secondary" @click="loadSchema">加载标准Schema</button>
        <button class="btn btn-info" @click="loadTools">刷新工具列表</button>
        <button class="btn btn-primary" :disabled="loading" @click="runCore">调用 /api/v1/llm/core</button>
      </div>
      <p class="status">{{ statusText }}</p>
    </section>

    <section class="panel">
      <h3>输入</h3>
      <div class="row">
        <label class="full">文本输入
          <textarea v-model="inputText" rows="4" placeholder="输入本次请求文本"></textarea>
        </label>
      </div>
      <div class="row">
        <label class="full">结构化数据(JSON)
          <textarea v-model="structuredDataText" rows="8"></textarea>
        </label>
      </div>
      <div class="row">
        <label class="full">启用工具（逗号分隔）
          <input v-model="enabledToolsText" placeholder="ocr,atspi_parse,hotspot_fetch" />
        </label>
      </div>
    </section>

    <section class="panel">
      <h3>请求预览</h3>
      <pre>{{ requestPreview }}</pre>
    </section>

    <section class="panel" v-if="responseData">
      <h3>响应预览</h3>
      <pre>{{ responseData }}</pre>
    </section>

    <section class="panel">
      <h3>工具注册表</h3>
      <table>
        <thead>
          <tr>
            <th>tool_name</th>
            <th>description</th>
            <th>enabled</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="tool in tools" :key="tool.tool_name">
            <td>{{ tool.tool_name }}</td>
            <td>{{ tool.description }}</td>
            <td>{{ tool.enabled ? 'true' : 'false' }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="panel">
      <h3>调用日志</h3>
      <button class="btn btn-secondary" @click="loadLogs">刷新日志</button>
      <table>
        <thead>
          <tr>
            <th>request_id</th>
            <th>scene_type</th>
            <th>model_used</th>
            <th>耗时(ms)</th>
            <th>success</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in logs" :key="row.request_id">
            <td>{{ row.request_id }}</td>
            <td>{{ row.scene_type }}</td>
            <td>{{ row.model_used }}</td>
            <td>{{ row.execution_time_ms }}</td>
            <td>{{ row.success ? 'true' : 'false' }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { callLLMCore, fetchLLMLogs, fetchLLMSchema, fetchLLMTools } from '../api'

const sceneType = ref('interface_analysis')
const protocolMode = ref('standard')
const userId = ref('user_001')
const modelPreference = ref('auto')
const inputText = ref('请分析当前界面并返回结构化控件信息')
const structuredDataText = ref(JSON.stringify({
  window_info: { title: '微信', class: 'WeChatMainWndForPC', x: 100, y: 100, width: 900, height: 700 },
  atspi_tree: [
    { path: 'root/child[0]/child[1]', depth: 2, role: 'push_button', name: '发送', x: 700, y: 550, width: 60, height: 30 }
  ],
  analysis_type: 'full_scan'
}, null, 2))
const enabledToolsText = ref('ocr,atspi_parse')
const tokenConfig = ref({
  max_history: 10,
  max_images: 1,
  max_text_chars: 2000
})

const tools = ref([])
const logs = ref([])
const loading = ref(false)
const statusText = ref('就绪')
const responseData = ref('')

const parseStructured = () => {
  try {
    return JSON.parse(structuredDataText.value || '{}')
  } catch (error) {
    return {}
  }
}

const buildPayload = () => {
  const enabled = (enabledToolsText.value || '')
    .split(',')
    .map(item => item.trim())
    .filter(Boolean)

  const standardPayload = {
    request_id: `req_${Date.now()}`,
    scene_type: sceneType.value,
    user_id: userId.value,
    context: {
      history: [],
      session_id: `session_${Date.now()}`
    },
    input: {
      text: inputText.value,
      images: [],
      audio: null,
      files: [],
      structured_data: parseStructured()
    },
    tools: {
      enabled,
      force_call: null,
      custom_params: {}
    },
    config: {
      model_preference: modelPreference.value,
      response_format: protocolMode.value === 'compact' ? 'compact_json' : 'json',
      timeout: 30000,
      ext: {
        max_history: Number(tokenConfig.value.max_history || 10),
        max_images: Number(tokenConfig.value.max_images || 1),
        max_text_chars: Number(tokenConfig.value.max_text_chars || 2000)
      }
    }
  }

  if (protocolMode.value !== 'compact') {
    return standardPayload
  }

  return {
    scene: sceneType.value,
    hist: [],
    text: inputText.value,
    img: '',
    tools: enabled,
    model_route: modelPreference.value,
    need_struct_output: true,
    config: standardPayload.config
  }
}

const requestPreview = computed(() => JSON.stringify(buildPayload(), null, 2))

const applySceneTemplate = () => {
  if (sceneType.value === 'interface_analysis') {
    inputText.value = '请分析当前界面并返回结构化控件信息'
    enabledToolsText.value = 'ocr,atspi_parse'
    structuredDataText.value = JSON.stringify({
      window_info: { title: '微信', class: 'WeChatMainWndForPC', x: 100, y: 100, width: 900, height: 700 },
      atspi_tree: [{ path: 'root/child[0]/child[1]', depth: 2, role: 'push_button', name: '发送', x: 700, y: 550, width: 60, height: 30 }],
      analysis_type: 'full_scan'
    }, null, 2)
  } else if (sceneType.value === 'sop_generation') {
    inputText.value = '请根据最近聊天和热点生成客户维护SOP'
    enabledToolsText.value = 'hotspot_fetch,product_recommend,chat_analyze'
    structuredDataText.value = JSON.stringify({
      date_info: { date: '2026-02-22', weekday: 'Sunday' },
      customer_info: { id: 'cust_001', name: '张三', tags: ['VIP', '高价值'] },
      chat_history: [
        { role: 'user', content: '最近有什么新品？' },
        { role: 'assistant', content: '刚上了一款智能手表。' }
      ],
      hotspots: [{ topic: 'AI智能手表', heat: 98, trend: 'up' }],
      sop_type: 'customer_follow_up'
    }, null, 2)
  } else {
    if (sceneType.value === 'multimodal_chat') {
      inputText.value = '帮我看看这张截图里有几条未读消息，然后生成回复'
      enabledToolsText.value = 'ocr,chat_analyze,file_analyze,tts,mark_as_read'
      structuredDataText.value = JSON.stringify({
        chat_context: [
          { role: 'user', content: '在吗？' },
          { role: 'assistant', content: '在的，请问有什么可以帮您？' }
        ],
        message_ids: [1, 2, 3]
      }, null, 2)
    } else {
      inputText.value = '请基于日志与模块状态给出系统优化建议和演进路径'
      enabledToolsText.value = 'chat_analyze,hotspot_fetch'
      structuredDataText.value = JSON.stringify({
        analysis_scope: 'full_system',
        bottlenecks: [
          { module: 'llm_router', issue: '复杂请求耗时偏高' },
          { module: 'sop_scheduler', issue: '重复生成导致token浪费' }
        ],
        metrics: {
          avg_latency_ms: 1300,
          fallback_rate: 0.22,
          daily_requests: 420
        }
      }, null, 2)
    }
  }
}

const loadSchema = async () => {
  try {
    const data = await fetchLLMSchema()
    statusText.value = data.success ? 'Schema 加载成功' : 'Schema 加载失败'
  } catch (error) {
    statusText.value = `Schema 加载失败: ${error.message}`
  }
}

const loadTools = async () => {
  try {
    const data = await fetchLLMTools()
    tools.value = data.items || []
    statusText.value = `工具已加载: ${tools.value.length}`
  } catch (error) {
    statusText.value = `工具加载失败: ${error.message}`
  }
}

const loadLogs = async () => {
  try {
    const data = await fetchLLMLogs({ limit: 20 })
    logs.value = data.items || []
  } catch (error) {
    statusText.value = `日志加载失败: ${error.message}`
  }
}

const runCore = async () => {
  loading.value = true
  try {
    const payload = buildPayload()
    const data = await callLLMCore(payload)
    responseData.value = JSON.stringify(data, null, 2)
    const modelUsed = data.model_used || data?.meta?.model_used || '-'
    const elapsed = data.execution_time || data?.meta?.execution_time || 0
    statusText.value = `调用成功, model=${modelUsed}, 耗时=${elapsed}ms`
    await loadLogs()
  } catch (error) {
    responseData.value = JSON.stringify(error?.response?.data || { message: error.message }, null, 2)
    statusText.value = `调用失败: ${error.message}`
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadTools()
  await loadLogs()
})
</script>

<style scoped>
.llm-core-debug {
  max-width: 1300px;
  margin: 0 auto;
  padding: 20px;
}

.panel {
  background: #fafafa;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 180px;
}

label.full {
  width: 100%;
}

input,
select,
textarea {
  padding: 8px;
  border-radius: 4px;
  border: 1px solid #ddd;
}

pre {
  max-height: 360px;
  overflow: auto;
  background: #111;
  color: #d6f7d6;
  padding: 10px;
  border-radius: 6px;
  font-size: 12px;
}

table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

th,
td {
  border: 1px solid #eee;
  padding: 8px;
  text-align: left;
  font-size: 12px;
}

.status {
  color: #333;
}

.btn {
  padding: 8px 14px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-primary {
  background: #007bff;
  color: #fff;
}

.btn-secondary {
  background: #6c757d;
  color: #fff;
}

.btn-info {
  background: #17a2b8;
  color: #fff;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
