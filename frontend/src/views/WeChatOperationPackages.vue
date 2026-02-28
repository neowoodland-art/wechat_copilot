<template>
  <div class="op-packages-page">
    <h2>微信操作打包</h2>
    <p class="desc">支持流程步骤编辑、轻量拖拽排序、分支节点、控件库引用、YAML导入导出与一键执行验证。</p>

    <div class="layout-grid">
      <section class="panel">
        <div class="panel-header">
          <h3>动作包列表</h3>
          <div class="panel-actions">
            <button class="btn btn-sm" @click="loadPackages">刷新</button>
            <button class="btn btn-sm btn-primary" @click="createPackageDraft">新建</button>
          </div>
        </div>
        <div class="list-wrap">
          <div
            v-for="item in packages"
            :key="item.id"
            class="list-item"
            :class="{ active: selectedPackage && selectedPackage.id === item.id }"
            @click="selectPackage(item)"
          >
            <div class="name">{{ item.package_name || item.package_code }}</div>
            <div class="meta">{{ item.package_code }} · {{ item.scene_type }} · {{ item.enabled ? '启用' : '停用' }}</div>
          </div>
          <div v-if="!packages.length" class="empty">暂无动作包</div>
        </div>
      </section>

      <section class="panel" v-if="selectedPackage">
        <div class="panel-header">
          <h3>动作包配置</h3>
          <button class="btn btn-primary" @click="savePackage">保存动作包</button>
        </div>

        <div class="form-grid">
          <label>包编码</label>
          <input v-model="selectedPackage.package_code" placeholder="如 chat_send_text_v1" />
          <label>包名称</label>
          <input v-model="selectedPackage.package_name" placeholder="如 发送消息基础动作" />
          <label>场景</label>
          <input v-model="selectedPackage.scene_type" placeholder="chat" />
          <label>profile_id</label>
          <input type="number" v-model.number="selectedPackage.profile_id" min="1" placeholder="用于控件库加载" />
          <label>版本</label>
          <input v-model="selectedPackage.version" placeholder="v1" />
          <label>描述</label>
          <textarea v-model="selectedPackage.description" rows="2" />
          <label>启用</label>
          <input type="checkbox" v-model="selectedPackage.enabled" class="checkbox" />
          <label>扩展配置(JSON)</label>
          <textarea v-model="packageConfigText" rows="5" />
        </div>

        <div class="panel-header" style="margin-top: 12px;">
          <h3>动作步骤编辑器</h3>
          <div class="panel-actions">
            <button class="btn btn-sm" @click="loadControlLibrary">加载控件库</button>
            <button class="btn btn-sm" @click="fillFirstContactSendTemplate">预置: 第一联系人发消息</button>
            <button class="btn btn-sm" @click="fillFlowIfTemplate">新增分支模板</button>
            <button class="btn btn-sm" @click="addActionRow">新增步骤</button>
            <button class="btn btn-sm btn-primary" @click="saveActions">保存步骤</button>
          </div>
        </div>

        <div class="action-types" v-if="actionTypes.length">
          <strong>可用动作类型:</strong>
          <span v-for="item in actionTypes" :key="item.action_type" class="chip">{{ item.action_type }}</span>
        </div>
        <div class="action-types" v-if="controlLibrary.length">
          <strong>控件库:</strong>
          <span class="chip">共 {{ controlLibrary.length }} 项</span>
        </div>

        <div
          v-for="(action, idx) in actions"
          :key="action.local_id"
          class="action-card"
          draggable="true"
          @dragstart="onActionDragStart(idx)"
          @dragover.prevent
          @drop="onActionDrop(idx)"
        >
          <div class="action-head">
            <strong>步骤 {{ idx + 1 }} <span class="muted">(可拖拽)</span></strong>
            <div class="panel-actions">
              <button class="btn btn-sm" @click="moveAction(-1, idx)">上移</button>
              <button class="btn btn-sm" @click="moveAction(1, idx)">下移</button>
              <button class="btn btn-sm" @click="duplicateActionRow(idx)">复制</button>
              <button class="btn btn-sm btn-danger" @click="removeActionRow(idx)">删除</button>
            </div>
          </div>
          <div class="form-grid action-grid">
            <label>action_key</label>
            <input v-model="action.action_key" placeholder="send_message" />
            <label>action_name</label>
            <input v-model="action.action_name" placeholder="发送消息" />
            <label>action_type</label>
            <select v-model="action.action_type" class="input-select" :class="{ 'input-invalid': isActionTypeInvalid(action) }">
              <option value="">请选择动作类型</option>
              <option v-for="item in actionTypeOptions" :key="item" :value="item">{{ item }}</option>
            </select>
            <label>step_order</label>
            <input type="number" v-model.number="action.step_order" min="0" />
            <label>control_uid</label>
            <div>
              <select
                class="input-select"
                :class="{ 'input-invalid': isControlUidInvalid(action) }"
                :value="action.control_uid"
                @change="onControlSelect(idx, $event.target.value)"
              >
                <option value="">请选择控件</option>
                <option v-for="ctrl in controlLibrary" :key="ctrl.control_uid" :value="ctrl.control_uid">
                  {{ ctrl.control_uid }} | {{ ctrl.role || '-' }} | {{ ctrl.text || '-' }}
                </option>
              </select>
              <div v-if="isControlUidInvalid(action)" class="field-error">该动作需要选择控件</div>
              <div class="mini-actions">
                <button class="btn btn-sm" @click="injectBoundsFromControl(idx, 'bounds')">写入 bounds</button>
                <button class="btn btn-sm" @click="injectBoundsFromControl(idx, 'input_bounds')">写入 input_bounds</button>
                <button class="btn btn-sm" @click="injectBoundsFromControl(idx, 'send_bounds')">写入 send_bounds</button>
              </div>
            </div>
            <label>enabled</label>
            <input type="checkbox" v-model="action.enabled" class="checkbox" />
            <label>params(JSON)</label>
            <textarea v-model="action.params_text" rows="7" />
            <label>expected(JSON)</label>
            <textarea v-model="action.expected_text" rows="4" />
          </div>
        </div>

        <div class="panel-header" style="margin-top: 12px;">
          <h3>连线关系视图（轻量）</h3>
        </div>
        <div class="result" v-if="relationGraph.nodes.length">
          <svg :width="relationCanvasWidth" :height="relationGraph.canvasHeight" class="relation-canvas">
            <defs>
              <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill="#5c6bc0" />
              </marker>
            </defs>

            <g v-for="(edge, idx) in relationGraph.edges" :key="`edge_${idx}`">
              <line
                :x1="relationGraph.nodes[edge.fromIndex].x + relationNodeWidth / 2"
                :y1="relationGraph.nodes[edge.fromIndex].y + relationNodeHeight"
                :x2="relationGraph.nodes[edge.toIndex].x + relationNodeWidth / 2"
                :y2="relationGraph.nodes[edge.toIndex].y"
                :stroke="edge.color"
                stroke-width="2"
                marker-end="url(#arrowhead)"
              />
              <text
                v-if="edge.label"
                :x="(relationGraph.nodes[edge.fromIndex].x + relationNodeWidth / 2 + relationGraph.nodes[edge.toIndex].x + relationNodeWidth / 2) / 2 + 8"
                :y="(relationGraph.nodes[edge.fromIndex].y + relationNodeHeight + relationGraph.nodes[edge.toIndex].y) / 2 - 4"
                :fill="edge.color"
                font-size="11"
                font-weight="600"
              >{{ edge.label }}</text>
            </g>

            <g v-for="(node, idx) in relationGraph.nodes" :key="`node_${idx}`">
              <rect
                :x="node.x"
                :y="node.y"
                :width="relationNodeWidth"
                :height="relationNodeHeight"
                rx="8"
                ry="8"
                :fill="node.enabled ? '#eef3ff' : '#f5f5f5'"
                :stroke="node.enabled ? '#5c6bc0' : '#bdbdbd'"
                stroke-width="1.5"
              />
              <text :x="node.x + 10" :y="node.y + 20" font-size="12" fill="#1f2937" font-weight="600">
                {{ idx + 1 }}. {{ node.action_name || node.action_key }}
              </text>
              <text :x="node.x + 10" :y="node.y + 38" font-size="11" fill="#4b5563">
                {{ node.action_type || '-' }}
              </text>
            </g>
          </svg>
        </div>
        <div class="result" v-else>
          <pre>暂无步骤，先新增或套用预置模板后可查看连线关系。</pre>
        </div>

        <datalist id="actionTypeList">
          <option v-for="item in actionTypes" :key="item.action_type" :value="item.action_type">{{ item.label }}</option>
        </datalist>

        <div class="panel-header" style="margin-top: 12px;">
          <h3>YAML导入导出</h3>
          <div class="panel-actions">
            <button class="btn btn-sm" @click="exportYaml">导出YAML</button>
            <button class="btn btn-sm btn-primary" @click="importYaml">导入YAML</button>
          </div>
        </div>
        <div class="form-grid">
          <label>YAML内容</label>
          <textarea v-model="yamlText" rows="10" />
        </div>

        <div class="panel-header" style="margin-top: 12px;">
          <h3>执行验证</h3>
          <div class="panel-actions">
            <button class="btn btn-sm" @click="loadExecutionEnvironmentStatus">环境检查</button>
            <button class="btn btn-sm" @click="runPackage(true)">Dry Run</button>
            <button class="btn btn-sm btn-success" @click="runPackage(false)">真实执行</button>
          </div>
        </div>
        <div class="env-status" :class="{ bad: envCheck && !envCheck.can_real_execute, good: envCheck && envCheck.can_real_execute }" v-if="envCheck">
          <div><strong>执行环境:</strong> {{ envCheck.can_real_execute ? '可用' : '缺少依赖' }}</div>
          <div class="env-tools">
            xdotool: {{ envCheck.tools?.xdotool ? '✅' : '❌' }}
            · xclip: {{ envCheck.tools?.xclip ? '✅' : '❌' }}
            · wl-copy: {{ envCheck.tools?.wl_copy ? '✅' : '❌' }}
          </div>
          <div v-if="envWarningText" class="env-warning">{{ envWarningText }}</div>
        </div>
        <div class="form-grid">
          <label>输入变量(JSON)</label>
          <textarea v-model="runVariablesText" rows="6" />
        </div>

        <div class="result" v-if="runResultText">
          <h4>执行结果</h4>
          <pre>{{ runResultText }}</pre>
        </div>
        <div class="result" v-if="runLogsText">
          <h4>最近日志</h4>
          <pre>{{ runLogsText }}</pre>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import axios from 'axios'

const SHARED_PROFILE_ID_KEY = 'wechat_shared_profile_id_v1'
const ATOMIC_CONTROLS_UPDATED_AT_KEY = 'wechat_atomic_controls_updated_at_v1'

const packages = ref([])
const selectedPackage = ref(null)
const packageConfigText = ref('{}')
const actions = ref([])
const actionTypes = ref([])
const controlLibrary = ref([])
const dragFromIndex = ref(-1)
const yamlText = ref('')
const runVariablesText = ref('{\n  "message": "你好，这是一条自动发送测试消息"\n}')
const runResultText = ref('')
const runLogsText = ref('')
const lastAtomicControlsUpdatedAt = ref('')
const envCheck = ref(null)
const relationCanvasWidth = 960
const relationNodeWidth = 280
const relationNodeHeight = 54
const relationNodeGapY = 80
const DEFAULT_ACTION_TYPES = ['ui.click_bounds', 'ui.input_text', 'chat.send_text', 'flow.if', 'wait.ms']
const CONTROL_REQUIRED_ACTION_TYPES = new Set(['ui.click_bounds', 'click', 'ui.input_text', 'humanized.input'])

const parseJsonOrThrow = (text, fallback = {}) => {
  const raw = String(text || '').trim()
  if (!raw) return fallback
  return JSON.parse(raw)
}

const parseJsonSafe = (text, fallback = {}) => {
  try {
    return parseJsonOrThrow(text, fallback)
  } catch {
    return fallback
  }
}

const stringifyJson = (data) => JSON.stringify(data || {}, null, 2)

const actionTypeOptions = computed(() => {
  const merged = new Set(DEFAULT_ACTION_TYPES)
  for (const item of (actionTypes.value || [])) {
    const key = String(item?.action_type || '').trim()
    if (key) merged.add(key)
  }
  return Array.from(merged)
})

const isKnownActionType = (actionType) => actionTypeOptions.value.includes(String(actionType || '').trim())

const isActionTypeInvalid = (action) => {
  const value = String(action?.action_type || '').trim()
  if (!value) return true
  return !isKnownActionType(value)
}

const needsControlForAction = (actionType) => CONTROL_REQUIRED_ACTION_TYPES.has(String(actionType || '').trim().toLowerCase())

const isControlUidInvalid = (action) => {
  if (!needsControlForAction(action?.action_type)) return false
  return !String(action?.control_uid || '').trim()
}

const relationGraph = computed(() => {
  const rows = (actions.value || []).map((item, index) => ({
    index,
    action_key: String(item?.action_key || `step_${index + 1}`).trim(),
    action_name: String(item?.action_name || '').trim(),
    action_type: String(item?.action_type || '').trim(),
    enabled: !!item?.enabled,
    params: parseJsonSafe(item?.params_text, {}),
  }))

  const keyToIndex = new Map(rows.map((row, index) => [row.action_key, index]))
  const centerX = relationCanvasWidth / 2
  const nodes = rows.map((row, index) => ({
    ...row,
    x: centerX - relationNodeWidth / 2,
    y: 20 + index * relationNodeGapY,
  }))

  const edges = []
  for (let index = 0; index < rows.length; index++) {
    const row = rows[index]
    if (row.action_type === 'flow.if') {
      const thenKey = String(row.params?.then_action_key || '').trim()
      const elseKey = String(row.params?.else_action_key || '').trim()
      const thenIndex = keyToIndex.get(thenKey)
      const elseIndex = keyToIndex.get(elseKey)
      if (Number.isInteger(thenIndex) && thenIndex >= 0) {
        edges.push({ fromIndex: index, toIndex: thenIndex, label: 'YES', color: '#2e7d32' })
      }
      if (Number.isInteger(elseIndex) && elseIndex >= 0) {
        edges.push({ fromIndex: index, toIndex: elseIndex, label: 'NO', color: '#c62828' })
      }
      if (!Number.isInteger(thenIndex) && !Number.isInteger(elseIndex) && index + 1 < rows.length) {
        edges.push({ fromIndex: index, toIndex: index + 1, label: 'NEXT', color: '#5c6bc0' })
      }
      continue
    }
    if (index + 1 < rows.length) {
      edges.push({ fromIndex: index, toIndex: index + 1, label: '', color: '#5c6bc0' })
    }
  }

  return {
    nodes,
    edges,
    canvasHeight: Math.max(240, 60 + nodes.length * relationNodeGapY),
  }
})

const showError = (err, prefix) => {
  const detail = err?.response?.data?.detail || err?.message || '未知错误'
  alert(`${prefix}: ${detail}`)
}

const envWarningText = computed(() => {
  const status = envCheck.value
  if (!status) return ''
  const warnings = Array.isArray(status.warnings) ? status.warnings : []
  return warnings.join('；')
})

const getSharedProfileId = () => {
  try {
    const raw = localStorage.getItem(SHARED_PROFILE_ID_KEY)
    const parsed = Number(raw || 0)
    return parsed > 0 ? parsed : null
  } catch {
    return null
  }
}

const persistSharedProfileId = (profileId) => {
  try {
    const value = Number(profileId || 0)
    if (value > 0) {
      localStorage.setItem(SHARED_PROFILE_ID_KEY, String(value))
    }
  } catch {
  }
}

const syncPackageProfileFromShared = () => {
  if (!selectedPackage.value) return
  const current = Number(selectedPackage.value.profile_id || 0)
  if (current > 0) return
  const shared = getSharedProfileId()
  if (shared) {
    selectedPackage.value.profile_id = shared
  }
}

const loadPackages = async () => {
  const response = await axios.get('/api/v1/wechat/ops/packages')
  packages.value = response.data?.items || []
}

const loadActionTypes = async () => {
  const response = await axios.get('/api/v1/wechat/ops/action_types')
  actionTypes.value = response.data?.items || []
}

const selectPackage = async (item) => {
  selectedPackage.value = { ...item }
  syncPackageProfileFromShared()
  persistSharedProfileId(selectedPackage.value?.profile_id)
  packageConfigText.value = JSON.stringify(item.config || {}, null, 2)
  await loadActions(item.id)
  await loadRunLogs(item.id)
  yamlText.value = ''
  controlLibrary.value = []
  if (Number(selectedPackage.value?.profile_id || 0) > 0) {
    await loadControlLibrary()
  }
}

const createPackageDraft = () => {
  const sharedProfileId = getSharedProfileId()
  selectedPackage.value = {
    id: null,
    package_code: `op_${Date.now()}`,
    package_name: '新动作包',
    enabled: true,
    scene_type: 'chat',
    profile_id: sharedProfileId,
    description: '',
    version: 'v1',
    config: {},
  }
  packageConfigText.value = '{}'
  actions.value = []
  runResultText.value = ''
  runLogsText.value = ''
  yamlText.value = ''
  controlLibrary.value = []
  if (Number(sharedProfileId || 0) > 0) {
    loadControlLibrary()
  }
}

const loadActions = async (packageId) => {
  const response = await axios.get('/api/v1/wechat/ops/packages/actions', {
    params: { package_id: packageId },
  })
  actions.value = (response.data?.items || []).map((item, index) => ({
    ...item,
    local_id: item.id || `local_${Date.now()}_${index}`,
    params_text: JSON.stringify(item.params || {}, null, 2),
    expected_text: JSON.stringify(item.expected || {}, null, 2),
  }))
}

const reorderActions = () => {
  actions.value = actions.value.map((item, idx) => ({
    ...item,
    step_order: idx,
  }))
}

const addActionRow = () => {
  actions.value.push({
    local_id: `local_${Date.now()}_${actions.value.length}`,
    action_key: '',
    action_name: '',
    action_type: 'ui.click_bounds',
    enabled: true,
    step_order: actions.value.length,
    control_uid: '',
    params_text: '{\n  \n}',
    expected_text: '{\n  \n}',
  })
  if (!controlLibrary.value.length && Number(selectedPackage.value?.profile_id || 0) > 0) {
    loadControlLibrary()
  }
}

const duplicateActionRow = (index) => {
  const source = actions.value[index]
  if (!source) return
  const timestamp = Date.now()
  const nextIndex = index + 1
  const cloned = {
    ...source,
    local_id: `local_${timestamp}_${actions.value.length}`,
    action_key: `${String(source.action_key || `step_${nextIndex + 1}`)}_copy_${timestamp}`,
    action_name: `${String(source.action_name || '步骤')} 复制`,
  }
  actions.value.splice(nextIndex, 0, cloned)
  reorderActions()
}

const fillFlowIfTemplate = () => {
  actions.value.push({
    local_id: `local_${Date.now()}_${actions.value.length}`,
    action_key: `if_${actions.value.length + 1}`,
    action_name: '条件分支',
    action_type: 'flow.if',
    enabled: true,
    step_order: actions.value.length,
    control_uid: '',
    params_text: JSON.stringify({
      var: 'unread_count',
      op: '>',
      value: 0,
      then_action_key: '',
      else_action_key: '',
    }, null, 2),
    expected_text: '{\n  \n}',
  })
}

const resolveControlUidByKeywords = (keywords = [], fallbackUid = '') => {
  const normalized = (keywords || []).map((k) => String(k || '').trim().toLowerCase()).filter(Boolean)
  if (!normalized.length) return fallbackUid
  const hit = controlLibrary.value.find((item) => {
    const text = [item?.control_uid, item?.text, item?.role, item?.control_type, item?.region_key]
      .map((v) => String(v || '').toLowerCase())
      .join(' ')
    return normalized.some((k) => text.includes(k))
  })
  return hit?.control_uid || fallbackUid
}

const findControlByUid = (controlUid) => {
  const uid = String(controlUid || '').trim()
  if (!uid) return null
  return controlLibrary.value.find((item) => String(item?.control_uid || '').trim() === uid) || null
}

const getControlBounds = (control) => {
  if (!control) return null
  const width = Number(control?.width ?? control?.bounds?.width ?? 0)
  const height = Number(control?.height ?? control?.bounds?.height ?? 0)
  if (width <= 0 || height <= 0) return null
  return {
    x: Number(control?.x ?? control?.bounds?.x ?? 0),
    y: Number(control?.y ?? control?.bounds?.y ?? 0),
    width,
    height,
  }
}

const buildClickParams = (controlUid) => {
  const params = { control_uid: String(controlUid || '').trim() }
  const profileId = Number(selectedPackage.value?.profile_id || 0)
  if (profileId > 0) {
    params.profile_id = profileId
  }
  const bounds = getControlBounds(findControlByUid(controlUid))
  if (bounds) {
    params.bounds = bounds
  }
  return params
}

const fillFirstContactSendTemplate = () => {
  const now = Date.now()
  const firstContactUid = resolveControlUidByKeywords(['first_contact', '第一联系人', '联系人列表', 'contact_list', 'list item'], 'chat.first_contact')
  const inputUid = resolveControlUidByKeywords(['chat_input', '输入', 'entry', 'textbox', 'input'], 'chat.input')
  const sendUid = resolveControlUidByKeywords(['send_button', '发送', 'button'], 'chat.send_button')
  const firstContactClickParams = buildClickParams(firstContactUid)
  const focusInputParams = buildClickParams(inputUid)
  const clickSendParams = buildClickParams(sendUid)
  actions.value = [
    {
      local_id: `local_${now}_0`,
      action_key: 'click_first_contact',
      action_name: '点击第一联系人',
      action_type: 'ui.click_bounds',
      enabled: true,
      step_order: 0,
      control_uid: firstContactUid,
      params_text: stringifyJson(firstContactClickParams),
      expected_text: '{\n  \n}',
    },
    {
      local_id: `local_${now}_1`,
      action_key: 'focus_chat_input',
      action_name: '点击消息输入框',
      action_type: 'ui.click_bounds',
      enabled: true,
      step_order: 1,
      control_uid: inputUid,
      params_text: stringifyJson(focusInputParams),
      expected_text: '{\n  \n}',
    },
    {
      local_id: `local_${now}_2`,
      action_key: 'input_message',
      action_name: '输入消息',
      action_type: 'ui.input_text',
      enabled: true,
      step_order: 2,
      control_uid: inputUid,
      params_text: stringifyJson({
        text: '{{message}}',
        control_uid: inputUid,
        profile_id: Number(selectedPackage.value?.profile_id || 0) || undefined,
        focus_before_input: true,
      }),
      expected_text: '{\n  \n}',
    },
    {
      local_id: `local_${now}_3`,
      action_key: 'click_send_button',
      action_name: '点击发送按钮',
      action_type: 'ui.click_bounds',
      enabled: true,
      step_order: 3,
      control_uid: sendUid,
      params_text: stringifyJson(clickSendParams),
      expected_text: '{\n  \n}',
    },
  ]
}

const moveAction = (delta, index) => {
  const target = index + delta
  if (target < 0 || target >= actions.value.length) return
  const cloned = [...actions.value]
  const [moved] = cloned.splice(index, 1)
  cloned.splice(target, 0, moved)
  actions.value = cloned
  reorderActions()
}

const onActionDragStart = (index) => {
  dragFromIndex.value = index
}

const onActionDrop = (toIndex) => {
  const from = dragFromIndex.value
  dragFromIndex.value = -1
  if (from < 0 || from === toIndex) return
  const cloned = [...actions.value]
  const [moved] = cloned.splice(from, 1)
  cloned.splice(toIndex, 0, moved)
  actions.value = cloned
  reorderActions()
}

const removeActionRow = (index) => {
  actions.value.splice(index, 1)
  reorderActions()
}

const findControl = (controlUid) => {
  const uid = String(controlUid || '').trim()
  if (!uid) return null
  return controlLibrary.value.find((item) => String(item.control_uid || '').trim() === uid) || null
}

const onControlSelect = (index, controlUid) => {
  const row = actions.value[index]
  if (!row) return
  row.control_uid = String(controlUid || '').trim()
  const profileId = Number(selectedPackage.value?.profile_id || 0)
  const params = parseJsonSafe(row.params_text, {})
  if (row.control_uid) {
    params.control_uid = row.control_uid
  }
  if (profileId > 0) {
    params.profile_id = profileId
  }
  const actionType = String(row.action_type || '').trim().toLowerCase()
  if (actionType === 'ui.click_bounds' || actionType === 'click') {
    const bounds = getControlBounds(findControlByUid(row.control_uid))
    if (bounds) {
      params.bounds = bounds
    }
  }
  row.params_text = stringifyJson(params)
}

const injectBoundsFromControl = (index, fieldName = 'bounds') => {
  try {
    const row = actions.value[index]
    if (!row) return
    const control = findControl(row.control_uid)
    if (!control) {
      throw new Error('请先选择有效控件')
    }
    const params = parseJsonOrThrow(row.params_text, {})
    params[fieldName] = {
      x: Number(control.x || 0),
      y: Number(control.y || 0),
      width: Number(control.width || 0),
      height: Number(control.height || 0),
    }
    if (!params.control_uid) {
      params.control_uid = control.control_uid
    }
    row.params_text = JSON.stringify(params, null, 2)
  } catch (err) {
    showError(err, '写入控件边界失败')
  }
}

const loadControlLibrary = async () => {
  try {
    let profileId = Number(selectedPackage.value?.profile_id || 0)
    if (!profileId) {
      const shared = getSharedProfileId()
      if (shared) {
        profileId = Number(shared)
        if (selectedPackage.value) {
          selectedPackage.value.profile_id = profileId
        }
      }
    }
    if (!profileId) {
      throw new Error('请先填写 profile_id')
    }
    const response = await axios.get('/api/v1/wechat/ui/controls', {
      params: { profile_id: profileId, page: 1, page_size: 500 },
    })
    controlLibrary.value = (response.data?.items || []).map((item) => ({
      ...item,
      x: Number(item?.x ?? item?.bounds?.x ?? 0),
      y: Number(item?.y ?? item?.bounds?.y ?? 0),
      width: Number(item?.width ?? item?.bounds?.width ?? 0),
      height: Number(item?.height ?? item?.bounds?.height ?? 0),
    }))
    alert(`控件库已加载，共 ${controlLibrary.value.length} 条`)
  } catch (err) {
    showError(err, '加载控件库失败')
  }
}

const maybeReloadControlLibraryByAtomicStamp = async () => {
  const profileId = Number(selectedPackage.value?.profile_id || 0)
  if (!profileId) return
  let latestStamp = ''
  try {
    latestStamp = String(localStorage.getItem(ATOMIC_CONTROLS_UPDATED_AT_KEY) || '')
  } catch {
    latestStamp = ''
  }
  if (!latestStamp || latestStamp === String(lastAtomicControlsUpdatedAt.value || '')) return
  lastAtomicControlsUpdatedAt.value = latestStamp
  await loadControlLibrary()
}

const onStorageChange = (event) => {
  if (event.key === SHARED_PROFILE_ID_KEY) {
    syncPackageProfileFromShared()
    if (Number(selectedPackage.value?.profile_id || 0) > 0) {
      loadControlLibrary()
    }
    return
  }
  if (event.key === ATOMIC_CONTROLS_UPDATED_AT_KEY) {
    maybeReloadControlLibraryByAtomicStamp()
  }
}

const onVisibilityChange = () => {
  if (!document.hidden) {
    maybeReloadControlLibraryByAtomicStamp()
  }
}

const savePackage = async () => {
  try {
    const payload = {
      id: selectedPackage.value?.id || null,
      package_code: String(selectedPackage.value?.package_code || '').trim(),
      package_name: String(selectedPackage.value?.package_name || '').trim(),
      enabled: !!selectedPackage.value?.enabled,
      scene_type: String(selectedPackage.value?.scene_type || 'chat').trim() || 'chat',
      profile_id: selectedPackage.value?.profile_id || null,
      description: String(selectedPackage.value?.description || ''),
      version: String(selectedPackage.value?.version || 'v1'),
      config: parseJsonOrThrow(packageConfigText.value, {}),
    }
    const response = await axios.post('/api/v1/wechat/ops/packages/upsert', payload)
    if (!response.data?.success) {
      throw new Error(response.data?.detail || '保存动作包失败')
    }
    selectedPackage.value.id = response.data.package_id
    await loadPackages()
    alert('动作包保存成功')
  } catch (err) {
    showError(err, '保存动作包失败')
  }
}

const saveActions = async () => {
  try {
    if (!selectedPackage.value?.id) {
      throw new Error('请先保存动作包再保存步骤')
    }
    const invalidMessages = []
    actions.value.forEach((item, idx) => {
      const stepNo = idx + 1
      if (isActionTypeInvalid(item)) {
        invalidMessages.push(`步骤${stepNo} 动作类型无效`)
      }
      if (isControlUidInvalid(item)) {
        invalidMessages.push(`步骤${stepNo} 缺少控件选择`)
      }
    })
    if (invalidMessages.length) {
      throw new Error(`请先修正以下问题：${invalidMessages.join('；')}`)
    }

    const profileId = Number(selectedPackage.value?.profile_id || 0)
    const normalizedActions = actions.value.map((item, idx) => {
      const actionType = String(item.action_type || '').trim().toLowerCase()
      const controlUid = String(item.control_uid || '').trim()
      const params = parseJsonOrThrow(item.params_text, {})
      if (controlUid) {
        params.control_uid = controlUid
      }
      if (profileId > 0) {
        params.profile_id = profileId
      }
      if (actionType === 'ui.click_bounds' || actionType === 'click') {
        const hasBounds = Number(params?.bounds?.width || 0) > 0 && Number(params?.bounds?.height || 0) > 0
        if (!hasBounds) {
          const bounds = getControlBounds(findControlByUid(controlUid))
          if (bounds) {
            params.bounds = bounds
          }
        }
      }
      return {
        action_key: String(item.action_key || '').trim(),
        action_name: String(item.action_name || '').trim(),
        action_type: String(item.action_type || '').trim(),
        enabled: !!item.enabled,
        step_order: Number(item.step_order ?? idx),
        control_uid: controlUid,
        params,
        expected: parseJsonOrThrow(item.expected_text, {}),
      }
    })
    const payload = {
      package_id: selectedPackage.value.id,
      actions: normalizedActions,
    }
    const response = await axios.post('/api/v1/wechat/ops/packages/actions/upsert_batch', payload)
    if (!response.data?.success) {
      throw new Error(response.data?.detail || '保存步骤失败')
    }
    await loadActions(selectedPackage.value.id)
    alert('步骤保存成功')
  } catch (err) {
    showError(err, '保存步骤失败')
  }
}

const exportYaml = async () => {
  try {
    if (!selectedPackage.value?.id) {
      throw new Error('请先保存动作包')
    }
    const response = await axios.get('/api/v1/wechat/ops/packages/export_yaml', {
      params: { package_id: selectedPackage.value.id },
    })
    yamlText.value = String(response.data?.yaml_text || '')
  } catch (err) {
    showError(err, '导出YAML失败')
  }
}

const importYaml = async () => {
  try {
    const text = String(yamlText.value || '').trim()
    if (!text) {
      throw new Error('请先输入YAML内容')
    }
    const response = await axios.post('/api/v1/wechat/ops/packages/import_yaml', {
      yaml_text: text,
      upsert: true,
    })
    if (!response.data?.success) {
      throw new Error(response.data?.detail || '导入失败')
    }
    await loadPackages()
    const hit = packages.value.find((item) => item.id === response.data.package_id)
    if (hit) {
      await selectPackage(hit)
    }
    alert('YAML导入成功')
  } catch (err) {
    showError(err, '导入YAML失败')
  }
}

const runPackage = async (dryRun = true) => {
  try {
    if (!selectedPackage.value?.id) {
      throw new Error('请先保存动作包')
    }
    if (!dryRun) {
      await loadExecutionEnvironmentStatus()
      if (envCheck.value && !envCheck.value.can_real_execute) {
        throw new Error(envWarningText.value || '环境依赖不完整，无法真实执行')
      }
    }
    const variables = parseJsonOrThrow(runVariablesText.value, {})
    const response = await axios.post('/api/v1/wechat/ops/packages/execute', {
      package_id: selectedPackage.value.id,
      variables,
      dry_run: !!dryRun,
    })
    runResultText.value = JSON.stringify(response.data || {}, null, 2)
    await loadRunLogs(selectedPackage.value.id)
    if (!response.data?.success) {
      alert(`执行失败: ${response.data?.error_message || '未知错误'}`)
    }
  } catch (err) {
    showError(err, '执行动作包失败')
  }
}

const loadRunLogs = async (packageId) => {
  const response = await axios.get('/api/v1/wechat/ops/run_logs', {
    params: { package_id: packageId, limit: 20 },
  })
  runLogsText.value = JSON.stringify(response.data?.items || [], null, 2)
}

const loadExecutionEnvironmentStatus = async () => {
  try {
    const response = await axios.get('/api/v1/wechat/ops/env/check')
    envCheck.value = response.data || null
  } catch (err) {
    envCheck.value = {
      can_real_execute: false,
      tools: {},
      warnings: [err?.response?.data?.detail || err?.message || '环境检查失败'],
    }
  }
}

onMounted(async () => {
  try {
    try {
      lastAtomicControlsUpdatedAt.value = String(localStorage.getItem(ATOMIC_CONTROLS_UPDATED_AT_KEY) || '')
    } catch {
      lastAtomicControlsUpdatedAt.value = ''
    }
    await Promise.all([loadPackages(), loadActionTypes()])
    if (packages.value.length) {
      await selectPackage(packages.value[0])
    } else {
      createPackageDraft()
    }
    await loadExecutionEnvironmentStatus()
    window.addEventListener('storage', onStorageChange)
    document.addEventListener('visibilitychange', onVisibilityChange)
  } catch (err) {
    showError(err, '初始化失败')
  }
})

watch(
  () => selectedPackage.value?.profile_id,
  async (value, oldValue) => {
    const next = Number(value || 0)
    const prev = Number(oldValue || 0)
    if (next > 0) {
      persistSharedProfileId(next)
    }
    if (next > 0 && next !== prev) {
      await loadControlLibrary()
    }
    if (!next) {
      controlLibrary.value = []
    }
  }
)

onUnmounted(() => {
  window.removeEventListener('storage', onStorageChange)
  document.removeEventListener('visibilitychange', onVisibilityChange)
})
</script>

<style scoped>
.op-packages-page {
  max-width: 1360px;
  margin: 0 auto;
  padding: 16px;
}

.desc {
  color: #666;
  margin-bottom: 12px;
}

.layout-grid {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 12px;
}

.panel {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 12px;
  background: #fff;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.panel-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.list-wrap {
  max-height: 780px;
  overflow: auto;
}

.list-item {
  border: 1px solid #edf0f5;
  border-radius: 6px;
  padding: 8px;
  margin-bottom: 8px;
  cursor: pointer;
}

.list-item.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.name {
  font-weight: 600;
}

.meta {
  margin-top: 4px;
  color: #666;
  font-size: 12px;
}

.empty {
  color: #999;
}

.form-grid {
  display: grid;
  grid-template-columns: 130px 1fr;
  gap: 8px;
  align-items: center;
}

input,
textarea {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 13px;
}

.checkbox {
  width: 18px;
  height: 18px;
}

.action-types {
  margin: 8px 0;
}

.chip {
  display: inline-block;
  margin: 4px 6px 0 0;
  padding: 2px 6px;
  border-radius: 10px;
  background: #f2f6fc;
  color: #606266;
  font-size: 12px;
}

.action-card {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 8px;
  margin-bottom: 10px;
  cursor: grab;
}

.action-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.muted {
  color: #999;
  font-size: 12px;
  font-weight: 400;
}

.action-grid {
  grid-template-columns: 110px 1fr;
}

.input-select {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 13px;
}

.input-invalid {
  border-color: #f56c6c !important;
  background: #fff6f6;
}

.field-error {
  margin-top: 4px;
  color: #f56c6c;
  font-size: 12px;
}

.mini-actions {
  margin-top: 6px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.result {
  margin-top: 10px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 8px;
  background: #fafafa;
}

.env-status {
  margin-top: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 8px;
  background: #f9fafb;
  font-size: 13px;
}

.env-status.good {
  border-color: #67c23a;
  background: #f0f9eb;
}

.env-status.bad {
  border-color: #f56c6c;
  background: #fef0f0;
}

.env-tools {
  margin-top: 4px;
  color: #374151;
}

.env-warning {
  margin-top: 4px;
  color: #b91c1c;
}

.relation-canvas {
  max-width: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #ffffff;
}

pre {
  margin: 0;
  max-height: 280px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.btn {
  padding: 6px 10px;
  border-radius: 4px;
  border: 1px solid #dcdfe6;
  background: #fff;
  cursor: pointer;
}

.btn-sm {
  font-size: 12px;
}

.btn-primary {
  background: #409eff;
  border-color: #409eff;
  color: #fff;
}

.btn-success {
  background: #67c23a;
  border-color: #67c23a;
  color: #fff;
}

.btn-danger {
  background: #f56c6c;
  border-color: #f56c6c;
  color: #fff;
}

@media (max-width: 1000px) {
  .layout-grid {
    grid-template-columns: 1fr;
  }
}
</style>
