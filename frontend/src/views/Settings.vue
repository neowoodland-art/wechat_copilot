<!-- /home/neogh/wechat_copilot/frontend/src/views/Settings.vue -->
<template>
  <div class="settings">
    <h2>系统设置</h2>
    
    <div class="settings-tabs">
      <div 
        v-for="tab in tabs" 
        :key="tab.key" 
        :class="['tab', { active: activeTab === tab.key }]"
        @click="switchTab(tab.key)"
      >
        {{ tab.title }}
      </div>
    </div>
    
    <div class="settings-content">
      <!-- 通用配置 -->
      <div v-show="activeTab === 'general'" class="tab-content">
        <div class="setting-group">
          <h3>自动化频率设置</h3>
          <div class="setting-item">
            <label>消息检查间隔 (秒):</label>
            <input v-model.number="settings.general.messageCheckInterval" type="number" class="form-control" />
          </div>
          <div class="setting-item">
            <label>SOP执行间隔 (分钟):</label>
            <input v-model.number="settings.general.sopExecutionInterval" type="number" class="form-control" />
          </div>
        </div>
        
        <div class="setting-group">
          <h3>拟人化参数</h3>
          <div class="setting-item">
            <label>随机延迟范围 (毫秒):</label>
            <input v-model.number="settings.general.randomDelayMin" type="number" class="form-control" />
            <span>到</span>
            <input v-model.number="settings.general.randomDelayMax" type="number" class="form-control" />
          </div>
        </div>
        
        <div class="setting-group">
          <h3>界面主题</h3>
          <div class="setting-item">
            <label>主题颜色:</label>
            <select v-model="settings.general.themeColor" class="form-control">
              <option value="#007bff">蓝色</option>
              <option value="#28a745">绿色</option>
              <option value="#dc3545">红色</option>
              <option value="#ffc107">黄色</option>
            </select>
          </div>
        </div>
      </div>
      
      <!-- API密钥管理 -->
      <div v-show="activeTab === 'api-keys'" class="tab-content">
        <div class="setting-group">
          <h3>AI模型密钥</h3>
          <div class="setting-item" v-for="provider in aiProviders" :key="provider.key">
            <label>{{ provider.name }}:</label>
            <input 
              v-model="settings.apiKeys[provider.key]" 
              type="password" 
              :placeholder="`输入${provider.name} API密钥`" 
              class="form-control"
            />
          </div>
        </div>
        
        <div class="setting-group">
          <h3>第三方服务密钥</h3>
          <div class="setting-item">
            <label>微信API密钥:</label>
            <input 
              v-model="settings.apiKeys.wechatApiKey" 
              type="password" 
              placeholder="输入微信API密钥" 
              class="form-control"
            />
          </div>
        </div>
      </div>
      
      <!-- 安全设置 -->
      <div v-show="activeTab === 'security'" class="tab-content">
        <div class="setting-group">
          <h3>操作权限</h3>
          <div class="setting-item">
            <label>允许发送消息:</label>
            <input 
              type="checkbox" 
              v-model="settings.security.allowSendMessage"
              class="checkbox"
            />
          </div>
          <div class="setting-item">
            <label>允许执行SOP:</label>
            <input 
              type="checkbox" 
              v-model="settings.security.allowExecuteSOP"
              class="checkbox"
            />
          </div>
        </div>
        
        <div class="setting-group">
          <h3>敏感操作确认</h3>
          <div class="setting-item">
            <label>删除客户前确认:</label>
            <input 
              type="checkbox" 
              v-model="settings.security.confirmDeleteCustomer"
              class="checkbox"
            />
          </div>
          <div class="setting-item">
            <label>批量操作前确认:</label>
            <input 
              type="checkbox" 
              v-model="settings.security.confirmBulkOperations"
              class="checkbox"
            />
          </div>
        </div>
      </div>
      
      <!-- 系统监控 -->
      <div v-show="activeTab === 'monitoring'" class="tab-content">
        <div class="monitoring-grid">
          <div class="monitor-card">
            <h4>系统健康度</h4>
            <div class="health-status">
              <div class="status-item">
                <span>后端服务:</span>
                <span class="status success">正常</span>
              </div>
              <div class="status-item">
                <span>C++驱动:</span>
                <span class="status success">正常</span>
              </div>
              <div class="status-item">
                <span>OCR引擎:</span>
                <span class="status warning">负载较高</span>
              </div>
              <div class="status-item">
                <span>数据库:</span>
                <span class="status success">正常</span>
              </div>
            </div>
          </div>
          
          <div class="monitor-card">
            <h4>性能指标</h4>
            <div class="performance-metrics">
              <div class="metric-item">
                <span>CPU使用率:</span>
                <span>42%</span>
              </div>
              <div class="metric-item">
                <span>内存使用:</span>
                <span>1.2GB / 8GB</span>
              </div>
              <div class="metric-item">
                <span>磁盘空间:</span>
                <span>120GB / 500GB</span>
              </div>
            </div>
          </div>
          
          <div class="monitor-card">
            <h4>错误日志</h4>
            <div class="log-container">
              <div class="log-entry">[2026-02-16 10:30:15] OCR引擎响应缓慢</div>
              <div class="log-entry">[2026-02-16 10:25:30] 微信界面元素识别超时</div>
              <div class="log-entry">[2026-02-16 10:20:45] AI模型连接失败，已重试</div>
            </div>
          </div>
        </div>
      </div>

      <!-- RPA全局设置 -->
      <div v-show="activeTab === 'rpa-global'" class="tab-content">
        <div class="setting-group">
          <h3>原子控件配置管理</h3>
          <div class="setting-item">
            <button class="btn btn-primary" :disabled="atomic.loading" @click="loadAtomicProfiles">刷新配置列表</button>
            <span v-if="atomic.loading">加载中...</span>
            <span v-else>共 {{ atomic.profiles.length }} 个配置</span>
          </div>
          <div class="setting-item">
            <label>选择配置:</label>
            <select v-model="atomic.selectedProfile" class="form-control atomic-select">
              <option value="">请选择</option>
              <option v-for="name in atomic.profiles" :key="name" :value="name">{{ name }}</option>
            </select>
          </div>
        </div>

        <div class="setting-group">
          <h3>重建与发现</h3>
          <div class="setting-item">
            <label>max_nodes:</label>
            <input v-model.number="atomic.maxNodes" type="number" min="100" max="20000" class="form-control" />
            <label>max_depth:</label>
            <input v-model.number="atomic.maxDepth" type="number" min="-1" max="64" class="form-control" />
          </div>
          <div class="setting-item">
            <button class="btn btn-secondary" :disabled="atomic.loading || !atomic.selectedProfile" @click="refreshAtomicSuggestion">刷新重建建议</button>
            <button class="btn btn-secondary" :disabled="atomic.loading" @click="discoverAtomicChats">发现聊天容器</button>
            <button class="btn btn-secondary" :disabled="atomic.loading" @click="discoverAtomicPopup">发现弹窗控件</button>
          </div>
          <div class="result-box" v-if="atomic.suggestion">
            <h4>重建建议</h4>
            <pre>{{ formatJson(atomic.suggestion) }}</pre>
          </div>
          <div class="result-box" v-if="atomic.discoveryType">
            <h4>{{ atomic.discoveryType }}（{{ atomic.discoveryItems.length }}项）</h4>
            <pre>{{ formatJson(atomic.discoveryItems.slice(0, 20)) }}</pre>
          </div>
        </div>

        <div class="setting-group">
          <h3>统一动作执行（C++）</h3>
          <div class="setting-item">
            <label>动作类型:</label>
            <select v-model="atomic.actionType" class="form-control">
              <option value="click">click</option>
              <option value="activate">activate</option>
              <option value="input_text">input_text</option>
            </select>
          </div>
          <div class="setting-item" v-if="atomic.actionType === 'input_text'">
            <label>输入文本:</label>
            <input v-model="atomic.actionText" type="text" class="form-control atomic-input" placeholder="请输入要写入的文本" />
          </div>
          <div class="setting-item">
            <button class="btn btn-info" :disabled="atomic.loading || !atomic.selectedProfile" @click="executeAtomic">执行原子动作</button>
          </div>
          <div class="result-box" v-if="atomic.execution">
            <h4>执行结果</h4>
            <pre>{{ formatJson(atomic.execution) }}</pre>
          </div>
          <div class="setting-item" v-if="atomic.message">
            <strong>{{ atomic.message }}</strong>
          </div>
        </div>
      </div>
    </div>
    
    <div class="settings-actions">
      <button @click="saveSettings" class="btn btn-primary">保存设置</button>
      <button @click="resetSettings" class="btn btn-secondary">重置设置</button>
      <button @click="exportConfig" class="btn btn-info">导出配置</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import {
  listAtomicProfiles,
  refreshAtomicProfile,
  discoverChatAtomicGroups,
  discoverPopupAtomicControls,
  executeAtomicAction
} from '../api'

const activeTab = ref('general')

const tabs = [
  { key: 'general', title: '通用配置' },
  { key: 'api-keys', title: 'API密钥' },
  { key: 'security', title: '安全设置' },
  { key: 'monitoring', title: '系统监控' },
  { key: 'rpa-global', title: 'RPA全局设置' }
]

const atomic = ref({
  loading: false,
  profiles: [],
  selectedProfile: '',
  maxNodes: 2200,
  maxDepth: 24,
  suggestion: null,
  discoveryType: '',
  discoveryItems: [],
  actionType: 'click',
  actionText: '',
  execution: null,
  message: ''
})

const settings = ref({
  general: {
    messageCheckInterval: 30,
    sopExecutionInterval: 5,
    randomDelayMin: 500,
    randomDelayMax: 1500,
    themeColor: '#007bff'
  },
  apiKeys: {
    ollama: '',
    doubao: '',
    deepseek: '',
    wechatApiKey: ''
  },
  security: {
    allowSendMessage: true,
    allowExecuteSOP: true,
    confirmDeleteCustomer: true,
    confirmBulkOperations: true
  }
})

const aiProviders = [
  { key: 'ollama', name: 'Ollama本地模型' },
  { key: 'doubao', name: '豆包多模态' },
  { key: 'deepseek', name: 'DeepSeek' }
]

const saveSettings = () => {
  alert('设置已保存')
  console.log('保存设置:', settings.value)
}

const switchTab = async (tabKey) => {
  activeTab.value = tabKey
  if (tabKey === 'rpa-global' && !atomic.value.profiles.length) {
    await loadAtomicProfiles()
  }
}

const formatJson = (value) => {
  try {
    return JSON.stringify(value ?? {}, null, 2)
  } catch {
    return String(value ?? '')
  }
}

const loadAtomicProfiles = async () => {
  atomic.value.loading = true
  atomic.value.message = ''
  try {
    const data = await listAtomicProfiles()
    atomic.value.profiles = data?.profiles || []
    if (!atomic.value.selectedProfile && atomic.value.profiles.length) {
      atomic.value.selectedProfile = atomic.value.profiles[0]
    }
    atomic.value.message = `已加载 ${atomic.value.profiles.length} 个原子配置`
  } catch (error) {
    atomic.value.message = `加载失败: ${error?.response?.data?.detail || error.message}`
  } finally {
    atomic.value.loading = false
  }
}

const refreshAtomicSuggestion = async () => {
  if (!atomic.value.selectedProfile) {
    atomic.value.message = '请先选择配置'
    return
  }
  atomic.value.loading = true
  atomic.value.message = ''
  try {
    const data = await refreshAtomicProfile({
      profile_name: atomic.value.selectedProfile,
      max_nodes: atomic.value.maxNodes,
      max_depth: atomic.value.maxDepth
    })
    atomic.value.suggestion = data?.suggestion || null
    atomic.value.message = data?.message || '已刷新建议'
  } catch (error) {
    atomic.value.message = `刷新建议失败: ${error?.response?.data?.detail || error.message}`
  } finally {
    atomic.value.loading = false
  }
}

const discoverAtomicChats = async () => {
  atomic.value.loading = true
  atomic.value.message = ''
  try {
    const data = await discoverChatAtomicGroups({
      max_nodes: atomic.value.maxNodes,
      max_depth: atomic.value.maxDepth
    })
    atomic.value.discoveryType = '聊天原子容器'
    atomic.value.discoveryItems = data?.items || []
    atomic.value.message = `发现 ${atomic.value.discoveryItems.length} 个聊天原子项`
  } catch (error) {
    atomic.value.message = `发现聊天容器失败: ${error?.response?.data?.detail || error.message}`
  } finally {
    atomic.value.loading = false
  }
}

const discoverAtomicPopup = async () => {
  atomic.value.loading = true
  atomic.value.message = ''
  try {
    const data = await discoverPopupAtomicControls({
      max_nodes: atomic.value.maxNodes,
      max_depth: atomic.value.maxDepth
    })
    atomic.value.discoveryType = '弹窗原子控件'
    atomic.value.discoveryItems = data?.items || []
    atomic.value.message = `发现 ${atomic.value.discoveryItems.length} 个弹窗原子项`
  } catch (error) {
    atomic.value.message = `发现弹窗控件失败: ${error?.response?.data?.detail || error.message}`
  } finally {
    atomic.value.loading = false
  }
}

const executeAtomic = async () => {
  if (!atomic.value.selectedProfile) {
    atomic.value.message = '请先选择配置'
    return
  }
  atomic.value.loading = true
  atomic.value.message = ''
  try {
    const payload = {
      action_type: atomic.value.actionType,
      profile_name: atomic.value.selectedProfile,
      text: atomic.value.actionType === 'input_text' ? atomic.value.actionText : '',
      max_nodes: atomic.value.maxNodes,
      max_depth: atomic.value.maxDepth
    }
    const data = await executeAtomicAction(payload)
    atomic.value.execution = data?.execution || data
    atomic.value.message = data?.message || '动作执行完成'
  } catch (error) {
    atomic.value.message = `执行失败: ${error?.response?.data?.detail || error.message}`
  } finally {
    atomic.value.loading = false
  }
}

const resetSettings = () => {
  if (confirm('确定要重置所有设置吗？')) {
    settings.value = {
      general: {
        messageCheckInterval: 30,
        sopExecutionInterval: 5,
        randomDelayMin: 500,
        randomDelayMax: 1500,
        themeColor: '#007bff'
      },
      apiKeys: {
        ollama: '',
        doubao: '',
        deepseek: '',
        wechatApiKey: ''
      },
      security: {
        allowSendMessage: true,
        allowExecuteSOP: true,
        confirmDeleteCustomer: true,
        confirmBulkOperations: true
      }
    }
  }
}

const exportConfig = () => {
  alert('导出配置功能待实现')
}
</script>

<style scoped>
.settings {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.settings-tabs {
  display: flex;
  border-bottom: 1px solid #ddd;
  margin-bottom: 20px;
}

.tab {
  padding: 10px 20px;
  cursor: pointer;
  border: 1px solid transparent;
  border-bottom: none;
  border-radius: 4px 4px 0 0;
  background-color: #f8f9fa;
  margin-right: 5px;
}

.tab:hover {
  background-color: #e9ecef;
}

.tab.active {
  background-color: white;
  border-color: #ddd;
  border-bottom: 1px solid white;
  font-weight: bold;
}

.settings-content {
  min-height: 400px;
}

.tab-content {
  padding: 20px 0;
}

.setting-group {
  margin-bottom: 25px;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.setting-group h3 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #333;
}

.setting-item {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
  flex-wrap: wrap;
  gap: 10px;
}

.setting-item label {
  min-width: 150px;
  font-weight: 600;
  color: #555;
}

.form-control {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.checkbox {
  margin: 0 10px;
}

.monitoring-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.monitor-card {
  background: white;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.health-status,
.performance-metrics {
  margin-top: 10px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  padding: 5px 0;
  border-bottom: 1px solid #eee;
}

.status-item:last-child {
  border-bottom: none;
}

.status {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8em;
  font-weight: bold;
}

.status.success {
  background-color: #d4edda;
  color: #155724;
}

.status.warning {
  background-color: #fff3cd;
  color: #856404;
}

.status.error {
  background-color: #f8d7da;
  color: #721c24;
}

.metric-item {
  display: flex;
  justify-content: space-between;
  padding: 5px 0;
  border-bottom: 1px solid #eee;
}

.log-container {
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #eee;
  border-radius: 4px;
  padding: 10px;
  background-color: #f8f9fa;
}

.log-entry {
  padding: 5px 0;
  border-bottom: 1px solid #eee;
  font-size: 0.9em;
  color: #666;
}

.log-entry:last-child {
  border-bottom: none;
}

.settings-actions {
  margin-top: 30px;
  display: flex;
  gap: 15px;
  justify-content: center;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  text-decoration: none;
  display: inline-block;
  text-align: center;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn-info {
  background-color: #17a2b8;
  color: white;
}

.btn:hover {
  opacity: 0.9;
}

.atomic-select {
  min-width: 320px;
}

.atomic-input {
  min-width: 320px;
}

.result-box {
  margin-top: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 10px;
  background: #fafafa;
  width: 100%;
}

.result-box pre {
  margin: 0;
  max-height: 260px;
  overflow: auto;
  font-size: 12px;
}
</style>
