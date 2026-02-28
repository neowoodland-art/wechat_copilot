<template>
  <div class="atomic-container-settings">
    <h2>原子容器设置管理</h2>

    <section class="panel">
      <h3>配置管理</h3>
      <div class="row">
        <button class="btn btn-primary" :disabled="loading" @click="loadProfiles">刷新配置列表</button>
        <span v-if="loading">加载中...</span>
        <span v-else>共 {{ profiles.length }} 个配置</span>
      </div>
      <div class="row">
        <label>选择配置</label>
        <select v-model="selectedProfile" class="input">
          <option value="">请选择</option>
          <option v-for="name in profiles" :key="name" :value="name">{{ name }}</option>
        </select>
      </div>
    </section>

    <section class="panel">
      <h3>重建与发现</h3>
      <div class="row">
        <label>max_nodes</label>
        <input v-model.number="maxNodes" type="number" min="100" max="20000" class="input" />
        <label>max_depth</label>
        <input v-model.number="maxDepth" type="number" min="-1" max="64" class="input" />
      </div>
      <div class="row">
        <button class="btn" :disabled="loading || !selectedProfile" @click="refreshSuggestion">刷新重建建议</button>
        <button class="btn" :disabled="loading" @click="discoverChats">发现聊天容器</button>
        <button class="btn" :disabled="loading" @click="discoverPopup">发现弹窗控件</button>
      </div>
      <div class="result" v-if="suggestion">
        <h4>重建建议</h4>
        <pre>{{ formatJson(suggestion) }}</pre>
      </div>
      <div class="result" v-if="discoveryType">
        <h4>{{ discoveryType }}（{{ discoveryItems.length }}项）</h4>
        <pre>{{ formatJson(discoveryItems.slice(0, 30)) }}</pre>
      </div>
    </section>

    <section class="panel">
      <h3>全面查询定义（深度/名称/编码/位置/状态）</h3>
      <div class="row">
        <label>预设规则</label>
        <select v-model="selectedPreset" class="input">
          <option value="">请选择预设</option>
          <option v-for="preset in presets" :key="preset.name" :value="preset.name">
            {{ preset.label }}
          </option>
        </select>
        <button class="btn btn-secondary" :disabled="loading || !selectedPreset" @click="applyPreset">应用预设</button>
      </div>

      <div class="row">
        <label>role_contains</label>
        <input v-model="queryForm.role_contains" type="text" class="input" placeholder="list item / button" />
        <label>role_equals</label>
        <input v-model="queryForm.role_equals" type="text" class="input" placeholder="push button" />
      </div>

      <div class="row">
        <label>name_contains</label>
        <input v-model="queryForm.name_contains" type="text" class="input" placeholder="发送(S)" />
        <label>text_contains</label>
        <input v-model="queryForm.text_contains" type="text" class="input" placeholder="联系人名或文本" />
      </div>

      <div class="row">
        <label>expected_depth</label>
        <input v-model.number="queryForm.expected_depth" type="number" min="0" max="64" class="input tiny" />
        <label>min_depth</label>
        <input v-model.number="queryForm.min_depth" type="number" min="0" max="64" class="input tiny" />
        <label>max_depth</label>
        <input v-model.number="queryForm.max_depth" type="number" min="0" max="64" class="input tiny" />
      </div>

      <div class="row">
        <label>path_code_contains</label>
        <input v-model="queryForm.path_code_contains" type="text" class="input input-wide" placeholder="路径编码/路径片段" />
      </div>

      <div class="row">
        <label><input type="checkbox" v-model="queryForm.require_non_zero_rect" /> 有位置信息(宽高>0)</label>
        <label><input type="checkbox" v-model="queryForm.require_showing" /> showing</label>
        <label><input type="checkbox" v-model="queryForm.require_visible" /> visible</label>
        <label><input type="checkbox" v-model="queryForm.require_non_empty_name_or_text" /> 名称或内容非空</label>
      </div>

      <div class="row">
        <label><input type="checkbox" v-model="queryForm.parse_contact_unread" /> 解析联系人未读(N条未读)</label>
        <label><input type="checkbox" v-model="queryForm.include_chat_order" /> 聊天区按Y坐标生成顺序号</label>
      </div>

      <div class="row">
        <label>scan_max_nodes</label>
        <input v-model.number="queryForm.scan_max_nodes" type="number" min="100" max="20000" class="input tiny" />
        <label>scan_max_depth</label>
        <input v-model.number="queryForm.scan_max_depth" type="number" min="-1" max="64" class="input tiny" />
        <label>limit</label>
        <input v-model.number="queryForm.limit" type="number" min="1" max="5000" class="input tiny" />
      </div>

      <div class="row">
        <button class="btn btn-primary" :disabled="loading" @click="runAdvancedQuery">执行高级查询</button>
        <button class="btn" :disabled="loading" @click="exportFilterJson">导出当前规则</button>
        <button class="btn" :disabled="loading" @click="importFilterJson">导入规则</button>
      </div>

      <div class="row">
        <textarea v-model="filterJsonText" rows="6" class="input textarea-wide" placeholder="规则JSON导入导出区"></textarea>
      </div>

      <div class="result" v-if="queryResultSummary">
        <h4>查询结果摘要</h4>
        <pre>{{ queryResultSummary }}</pre>
      </div>
      <div class="result" v-if="queryItems.length">
        <h4>查询结果（{{ queryItems.length }}）</h4>
        <pre>{{ formatJson(queryItems.slice(0, 120)) }}</pre>
      </div>
    </section>

    <section class="panel">
      <h3>标准动作执行（C++）</h3>
      <div class="row">
        <label>动作</label>
        <select v-model="actionType" class="input">
          <option value="activate">activate</option>
          <option value="click">click</option>
          <option value="input_text">input_text</option>
        </select>
      </div>
      <div class="row" v-if="actionType === 'input_text'">
        <label>输入内容</label>
        <input v-model="actionText" type="text" class="input input-wide" placeholder="请输入文本" />
      </div>
      <div class="row">
        <button class="btn btn-success" :disabled="loading || !selectedProfile" @click="executeAction">执行动作</button>
      </div>
      <div class="result" v-if="execution">
        <h4>执行结果</h4>
        <pre>{{ formatJson(execution) }}</pre>
      </div>
    </section>

    <section class="panel">
      <h3>链路落地：生成配置文件并带入“生成原子控件”</h3>
      <div class="row">
        <label>目标 profile_id（第6步控件库）</label>
        <input v-model.number="targetProfileId" type="number" min="1" class="input tiny" placeholder="如 1" />
      </div>
      <div class="row">
        <button class="btn btn-primary" :disabled="loading" @click="generatePipelineConfig">生成配置文件</button>
        <button class="btn" :disabled="loading || !pipelineConfigText" @click="savePipelineConfig(false)">保存配置文件</button>
        <button class="btn btn-success" :disabled="loading || !pipelineConfigText" @click="savePipelineConfig(true)">保存并带入第6步</button>
      </div>
      <div class="row">
        <textarea
          v-model="pipelineConfigText"
          rows="8"
          class="input textarea-wide"
          placeholder="这里会生成可复用配置JSON（包含profile_id、查询filters、动作建议）"
        ></textarea>
      </div>
      <div class="result" v-if="pipelineConfigSummary">
        <h4>配置摘要</h4>
        <pre>{{ pipelineConfigSummary }}</pre>
      </div>
      <p class="hint">说明：先在本页执行“高级查询”并确认唯一控件，再点“保存并带入第6步”，然后在第6步点击“按配置直接生成控件”。</p>
    </section>

    <p class="status" v-if="message">{{ message }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import {
  listAtomicProfiles,
  refreshAtomicProfile,
  discoverChatAtomicGroups,
  discoverPopupAtomicControls,
  executeAtomicAction,
  queryAtomicControls,
  listAtomicQueryPresets
} from '../api'

const loading = ref(false)
const profiles = ref([])
const selectedProfile = ref('')
const maxNodes = ref(2200)
const maxDepth = ref(24)
const suggestion = ref(null)
const discoveryType = ref('')
const discoveryItems = ref([])
const actionType = ref('activate')
const actionText = ref('')
const execution = ref(null)
const message = ref('')
const presets = ref([])
const selectedPreset = ref('')
const queryItems = ref([])
const queryResultSummary = ref('')
const filterJsonText = ref('')
const pipelineConfigText = ref('')
const pipelineConfigSummary = ref('')
const targetProfileId = ref(null)

const SHARED_PROFILE_ID_KEY = 'wechat_shared_profile_id_v1'
const ATOMIC_QUERY_PIPELINE_CONFIG_KEY = 'rpa_atomic_pipeline_config_v1'

const buildDefaultQueryForm = () => ({
  role_equals: '',
  role_contains: '',
  name_contains: '',
  text_contains: '',
  parent_role_equals: '',
  path_contains: '',
  path_code_contains: '',
  expected_depth: null,
  min_depth: null,
  max_depth: null,
  require_visible: false,
  require_showing: false,
  require_non_zero_rect: true,
  require_non_empty_name_or_text: true,
  parse_contact_unread: true,
  include_chat_order: true,
  scan_max_nodes: 2400,
  scan_max_depth: 24,
  limit: 500,
  sort_by: 'position',
  sort_order: 'asc'
})

const queryForm = ref(buildDefaultQueryForm())

const formatJson = (value) => {
  try {
    return JSON.stringify(value ?? {}, null, 2)
  } catch {
    return String(value ?? '')
  }
}

const sanitizeFilters = (rawFilters = {}) => {
  const filters = { ...(rawFilters || {}) }
  Object.keys(filters).forEach((key) => {
    if (filters[key] === '' || filters[key] === null || filters[key] === undefined) {
      delete filters[key]
    }
  })
  return filters
}

const buildPipelineConfig = () => {
  const filters = sanitizeFilters(queryForm.value)
  const firstItem = (queryItems.value || [])[0] || null
  const profileId = Number(targetProfileId.value || 0)
  return {
    version: 'v1',
    created_at: new Date().toISOString(),
    source: 'atomic_container_settings',
    profile_name: String(selectedProfile.value || '').trim(),
    profile_id: profileId > 0 ? profileId : null,
    selected_preset: String(selectedPreset.value || '').trim() || null,
    query_count: Number(queryItems.value?.length || 0),
    recommended_source: 'query',
    filters,
    suggested_action: {
      action_type: actionType.value,
      text: actionType.value === 'input_text' ? String(actionText.value || '') : ''
    },
    picked_control_hint: firstItem
      ? {
        role: firstItem.role || '',
        name: firstItem.name || '',
        text: firstItem.text || '',
        path: firstItem.path || '',
        depth: firstItem.depth ?? null
      }
      : null
  }
}

const generatePipelineConfig = () => {
  const payload = buildPipelineConfig()
  pipelineConfigText.value = JSON.stringify(payload, null, 2)
  pipelineConfigSummary.value = `profile_id: ${payload.profile_id || '-'}\nquery_count: ${payload.query_count}\nrecommended_source: ${payload.recommended_source}`
  message.value = '已生成配置文件，可保存并带入第6步“生成原子控件”'
}

const savePipelineConfig = (jumpToAtomicControls = false) => {
  try {
    const raw = String(pipelineConfigText.value || '').trim()
    if (!raw) {
      throw new Error('请先生成或粘贴配置JSON')
    }
    const parsed = JSON.parse(raw)
    localStorage.setItem(ATOMIC_QUERY_PIPELINE_CONFIG_KEY, JSON.stringify(parsed))
    if (Number(parsed?.profile_id || 0) > 0) {
      localStorage.setItem(SHARED_PROFILE_ID_KEY, String(Number(parsed.profile_id)))
    }
    window.dispatchEvent(new CustomEvent('atomic-pipeline-config-ready', {
      detail: {
        jumpToAtomicControls: !!jumpToAtomicControls,
      }
    }))
    message.value = jumpToAtomicControls ? '配置已保存并通知第6步，可直接生成标准控件' : '配置文件已保存到本地'
  } catch (error) {
    message.value = `保存配置失败: ${error?.message || '未知错误'}`
  }
}

const loadPipelineConfigDraft = () => {
  try {
    const profileRaw = localStorage.getItem(SHARED_PROFILE_ID_KEY)
    const profileId = Number(profileRaw || 0)
    targetProfileId.value = profileId > 0 ? profileId : null
    const draft = localStorage.getItem(ATOMIC_QUERY_PIPELINE_CONFIG_KEY)
    if (!draft) return
    const parsed = JSON.parse(draft)
    pipelineConfigText.value = JSON.stringify(parsed, null, 2)
    pipelineConfigSummary.value = `profile_id: ${Number(parsed?.profile_id || 0) || '-'}\nquery_count: ${Number(parsed?.query_count || 0)}\nrecommended_source: ${parsed?.recommended_source || 'query'}`
  } catch {
    pipelineConfigText.value = ''
    pipelineConfigSummary.value = ''
  }
}

const loadProfiles = async () => {
  loading.value = true
  message.value = ''
  try {
    const data = await listAtomicProfiles()
    profiles.value = data?.profiles || []
    if (!selectedProfile.value && profiles.value.length) {
      selectedProfile.value = profiles.value[0]
    }
    message.value = `已加载 ${profiles.value.length} 个配置`
  } catch (error) {
    message.value = `加载失败: ${error?.response?.data?.detail || error.message}`
  } finally {
    loading.value = false
  }
}

const loadQueryPresets = async () => {
  try {
    const data = await listAtomicQueryPresets()
    presets.value = data?.presets || []
  } catch {
    presets.value = []
  }
}

const applyPreset = () => {
  const preset = presets.value.find((item) => item.name === selectedPreset.value)
  if (!preset) return
  queryForm.value = {
    ...buildDefaultQueryForm(),
    ...(preset.filters || {})
  }
  filterJsonText.value = JSON.stringify(queryForm.value, null, 2)
}

const runAdvancedQuery = async () => {
  loading.value = true
  message.value = ''
  try {
    const payload = { ...queryForm.value }
    Object.keys(payload).forEach((key) => {
      if (payload[key] === '' || payload[key] === null || payload[key] === undefined) {
        delete payload[key]
      }
    })
    const data = await queryAtomicControls(payload)
    queryItems.value = data?.items || []
    queryResultSummary.value = `返回 ${data?.count || 0} / 总 ${data?.total || 0}\n过滤参数: ${JSON.stringify(data?.filters || {}, null, 2)}`
    message.value = `高级查询完成：${data?.count || 0} 条`
  } catch (error) {
    message.value = `高级查询失败: ${error?.response?.data?.detail || error.message}`
  } finally {
    loading.value = false
  }
}

const exportFilterJson = () => {
  filterJsonText.value = JSON.stringify(queryForm.value, null, 2)
  message.value = '已导出当前规则到下方JSON区域'
}

const importFilterJson = () => {
  try {
    const parsed = JSON.parse(String(filterJsonText.value || '{}'))
    queryForm.value = {
      ...buildDefaultQueryForm(),
      ...(parsed || {})
    }
    message.value = '规则导入成功'
  } catch (error) {
    message.value = `规则导入失败: ${error.message}`
  }
}

const refreshSuggestion = async () => {
  loading.value = true
  message.value = ''
  try {
    const data = await refreshAtomicProfile({
      profile_name: selectedProfile.value,
      max_nodes: maxNodes.value,
      max_depth: maxDepth.value
    })
    suggestion.value = data?.suggestion || null
    message.value = data?.message || '已刷新建议'
  } catch (error) {
    message.value = `刷新建议失败: ${error?.response?.data?.detail || error.message}`
  } finally {
    loading.value = false
  }
}

const discoverChats = async () => {
  loading.value = true
  message.value = ''
  try {
    const data = await discoverChatAtomicGroups({
      max_nodes: maxNodes.value,
      max_depth: maxDepth.value
    })
    discoveryType.value = '聊天原子容器'
    discoveryItems.value = data?.items || []
    message.value = `发现 ${discoveryItems.value.length} 项`
  } catch (error) {
    message.value = `发现聊天容器失败: ${error?.response?.data?.detail || error.message}`
  } finally {
    loading.value = false
  }
}

const discoverPopup = async () => {
  loading.value = true
  message.value = ''
  try {
    const data = await discoverPopupAtomicControls({
      max_nodes: maxNodes.value,
      max_depth: maxDepth.value
    })
    discoveryType.value = '弹窗原子控件'
    discoveryItems.value = data?.items || []
    message.value = `发现 ${discoveryItems.value.length} 项`
  } catch (error) {
    message.value = `发现弹窗控件失败: ${error?.response?.data?.detail || error.message}`
  } finally {
    loading.value = false
  }
}

const executeAction = async () => {
  loading.value = true
  message.value = ''
  try {
    const data = await executeAtomicAction({
      action_type: actionType.value,
      profile_name: selectedProfile.value,
      text: actionType.value === 'input_text' ? actionText.value : '',
      max_nodes: maxNodes.value,
      max_depth: maxDepth.value
    })
    execution.value = data?.execution || data
    message.value = data?.message || '执行完成'
  } catch (error) {
    message.value = `执行失败: ${error?.response?.data?.detail || error.message}`
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadProfiles()
  loadQueryPresets()
  loadPipelineConfigDraft()
})
</script>

<style scoped>
.atomic-container-settings {
  padding: 20px;
}
.panel {
  margin-bottom: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
  background: #fff;
}
.row {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.input {
  min-width: 180px;
  padding: 8px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
}
.input-wide {
  min-width: 380px;
}
.tiny {
  min-width: 100px;
}
.textarea-wide {
  width: 100%;
  min-height: 120px;
}
.btn {
  padding: 8px 12px;
  border-radius: 6px;
  border: none;
  background: #6b7280;
  color: #fff;
  cursor: pointer;
}
.btn-primary {
  background: #2563eb;
}
.btn-success {
  background: #16a34a;
}
.result {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 10px;
  background: #f9fafb;
}
.result pre {
  margin: 0;
  font-size: 12px;
  max-height: 240px;
  overflow: auto;
}
.status {
  font-weight: 600;
}
.hint {
  margin: 0;
  color: #4b5563;
  font-size: 12px;
}
</style>
