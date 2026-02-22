<!-- /home/neogh/wechat_copilot/frontend/src/views/Settings.vue -->
<template>
  <div class="settings">
    <h2>系统设置</h2>
    
    <div class="settings-tabs">
      <div 
        v-for="tab in tabs" 
        :key="tab.key" 
        :class="['tab', { active: activeTab === tab.key }]"
        @click="activeTab = tab.key"
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

const activeTab = ref('general')

const tabs = [
  { key: 'general', title: '通用配置' },
  { key: 'api-keys', title: 'API密钥' },
  { key: 'security', title: '安全设置' },
  { key: 'monitoring', title: '系统监控' }
]

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
</style>
