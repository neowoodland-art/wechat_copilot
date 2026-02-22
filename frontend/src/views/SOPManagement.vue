<template>
  <div class="sop-management">
    <h2>SOP管理</h2>
    
    <div class="sop-controls">
      <button @click="createNewSOP" class="btn btn-primary">新建SOP流程</button>
      <input v-model="searchSOPQuery" placeholder="搜索SOP..." class="search-input" />
    </div>
    
    <div class="sop-visual-editor">
      <h3>可视化SOP编辑器</h3>
      <div class="editor-actions">
        <button @click="openEditor" class="btn btn-info">打开完整编辑器</button>
      </div>
      <div class="editor-preview">
        <div class="preview-node">
          <div class="node-header delay-node">
            <div class="node-type">等待</div>
          </div>
          <div class="node-content">
            <div>等待: 60秒</div>
          </div>
        </div>
        <div class="preview-connector">→</div>
        <div class="preview-node">
          <div class="node-header message-node">
            <div class="node-type">消息</div>
          </div>
          <div class="node-content">
            <div>发送欢迎消息</div>
          </div>
        </div>
        <div class="preview-connector">→</div>
        <div class="preview-node">
          <div class="node-header condition-node">
            <div class="node-type">条件</div>
          </div>
          <div class="node-content">
            <div>判断客户回复</div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="sop-list-section">
      <h3>现有SOP流程</h3>
      <div class="sops-grid">
        <div v-for="sop in sops" :key="sop.id" class="sop-card">
          <div class="sop-header">
            <h4>{{ sop.name }}</h4>
            <span :class="['status-badge', sop.status]">{{ sop.status }}</span>
          </div>
          <div class="sop-meta">
            <p><strong>步骤数:</strong> {{ sop.stepsCount }}</p>
            <p><strong>最后更新:</strong> {{ sop.lastUpdated }}</p>
            <p><strong>执行次数:</strong> {{ sop.executionCount }}</p>
          </div>
          <div class="sop-actions">
            <button @click="editSOP(sop)" class="btn btn-sm btn-info">编辑</button>
            <button @click="runSOP(sop)" class="btn btn-sm btn-success">运行</button>
            <button @click="viewAnalytics(sop)" class="btn btn-sm btn-secondary">分析</button>
          </div>
        </div>
      </div>
    </div>
    
    <div class="execution-monitor">
      <h3>SOP执行监控</h3>
      <div class="monitor-grid">
        <div class="monitor-card">
          <h4>实时执行进度</h4>
          <div class="progress-placeholder">执行进度显示区域</div>
        </div>
        <div class="monitor-card">
          <h4>异常处理</h4>
          <div class="exception-placeholder">异常处理显示区域</div>
        </div>
        <div class="monitor-card">
          <h4>成功率统计</h4>
          <div class="stats-placeholder">成功率图表显示区域</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const searchSOPQuery = ref('')
const sops = ref([
  {
    id: 1,
    name: '新好友欢迎SOP',
    status: 'active',
    stepsCount: 5,
    lastUpdated: '2026-02-15',
    executionCount: 1240
  },
  {
    id: 2,
    name: '询价客户跟进SOP',
    status: 'active',
    stepsCount: 7,
    lastUpdated: '2026-02-14',
    executionCount: 892
  },
  {
    id: 3,
    name: '售后问题处理SOP',
    status: 'draft',
    stepsCount: 10,
    lastUpdated: '2026-02-10',
    executionCount: 0
  }
])

const createNewSOP = () => {
  router.push('/sop-editor')
}

const openEditor = () => {
  router.push('/sop-editor')
}

const editSOP = (sop) => {
  router.push(`/sop-editor?id=${sop.id}&name=${encodeURIComponent(sop.name)}`)
}

const runSOP = (sop) => {
  alert(`运行SOP: ${sop.name}`)
}

const viewAnalytics = (sop) => {
  alert(`查看SOP分析: ${sop.name}`)
}
</script>

<style scoped>
.sop-management {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.sop-controls {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.search-input {
  flex: 1;
  max-width: 300px;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.sop-visual-editor {
  margin-bottom: 30px;
  padding: 20px;
  background-color: #fafafa;
  border-radius: 8px;
}

.editor-canvas {
  margin-top: 15px;
}

.canvas-placeholder {
  background: white;
  padding: 40px;
  border-radius: 8px;
  text-align: center;
  border: 2px dashed #ccc;
  min-height: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.canvas-placeholder ul {
  text-align: left;
  margin: 15px 0;
}

.sop-list-section {
  margin-bottom: 30px;
}

.sops-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.sop-card {
  background: white;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
  border-left: 4px solid #ffc107;
}

.sop-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.8em;
  font-weight: bold;
}

.status-badge.active {
  background-color: #d4edda;
  color: #155724;
}

.status-badge.draft {
  background-color: #f8f9fa;
  color: #6c757d;
}

.sop-meta p {
  margin: 5px 0;
  color: #666;
}

.sop-actions {
  margin-top: 15px;
  display: flex;
  gap: 8px;
}

.execution-monitor {
  padding: 20px;
  background-color: #fafafa;
  border-radius: 8px;
}

.monitor-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-top: 15px;
}

.monitor-card {
  background: white;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.progress-placeholder,
.exception-placeholder,
.stats-placeholder {
  height: 150px;
  background-color: #f8f9fa;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed #ccc;
  border-radius: 4px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  text-decoration: none;
  display: inline-block;
  text-align: center;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 12px;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-info {
  background-color: #17a2b8;
  color: white;
}

.btn-success {
  background-color: #28a745;
  color: white;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn:hover {
  opacity: 0.9;
}
</style>