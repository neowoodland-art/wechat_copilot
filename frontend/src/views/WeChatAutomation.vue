<template>
  <div class="wechat-automation">
    <h2>微信自动化管理</h2>
    
    <div class="automation-section">
      <h3>实例管理</h3>
      <div class="instances-grid">
        <div v-for="instance in instances" :key="instance.id" class="instance-card">
          <div class="instance-header">
            <h4>{{ instance.name }}</h4>
            <span :class="['status-badge', instance.status]">{{ instance.status }}</span>
          </div>
          <div class="instance-info">
            <p><strong>微信版本:</strong> {{ instance.version }}</p>
            <p><strong>激活状态:</strong> {{ instance.active ? '已激活' : '未激活' }}</p>
            <p><strong>最后活动:</strong> {{ instance.lastActivity }}</p>
          </div>
          <div class="instance-actions">
            <button @click="activateInstance(instance)" class="btn btn-success">激活</button>
            <button @click="deactivateInstance(instance)" class="btn btn-warning">暂停</button>
            <button @click="viewDetails(instance)" class="btn btn-info">详情</button>
          </div>
        </div>
      </div>
    </div>
    
    <div class="automation-section">
      <h3>界面适配器管理</h3>
      <div class="adapter-section">
        <div class="adapter-controls">
          <button @click="calibrateCoordinates" class="btn btn-primary">校准控件坐标</button>
          <button @click="checkAccessibility" class="btn btn-info">检查AT-SPI状态</button>
        </div>
        
        <div class="coordinates-grid">
          <div v-for="coord in coordinates" :key="coord.id" class="coordinate-item">
            <div class="coord-header">
              <h4>{{ coord.name }}</h4>
              <span class="coord-status">{{ coord.status }}</span>
            </div>
            <div class="coord-values">
              <p>X: {{ coord.x }}, Y: {{ coord.y }}</p>
              <p>宽: {{ coord.width }}, 高: {{ coord.height }}</p>
            </div>
            <div class="coord-actions">
              <button @click="editCoordinate(coord)" class="btn btn-sm btn-info">编辑</button>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="automation-section">
      <h3>人性化参数设置</h3>
      <div class="humanization-settings">
        <div class="setting-group">
          <label>模拟打字速度 (字符/秒):</label>
          <input v-model.number="typingSpeed" type="range" min="1" max="20" class="slider" />
          <span>{{ typingSpeed }}</span>
        </div>
        
        <div class="setting-group">
          <label>点击偏移量 (像素):</label>
          <input v-model.number="clickOffset" type="range" min="0" max="10" class="slider" />
          <span>{{ clickOffset }}px</span>
        </div>
        
        <div class="setting-group">
          <label>操作间隔 (毫秒):</label>
          <input v-model.number="operationInterval" type="range" min="100" max="2000" step="100" class="slider" />
          <span>{{ operationInterval }}ms</span>
        </div>
        
        <button @click="saveSettings" class="btn btn-primary">保存设置</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const instances = ref([
  {
    id: 1,
    name: '微信主账号',
    status: 'active',
    version: '4.1.0',
    active: true,
    lastActivity: '刚刚'
  },
  {
    id: 2,
    name: '客服微信',
    status: 'idle',
    version: '4.1.0',
    active: false,
    lastActivity: '5分钟前'
  }
])

const coordinates = ref([
  {
    id: 1,
    name: '搜索栏',
    x: 120,
    y: 80,
    width: 200,
    height: 30,
    status: '校准'
  },
  {
    id: 2,
    name: '聊天区域',
    x: 300,
    y: 100,
    width: 500,
    height: 400,
    status: '校准'
  },
  {
    id: 3,
    name: '输入框',
    x: 300,
    y: 520,
    width: 500,
    height: 100,
    status: '校准'
  }
])

const typingSpeed = ref(8)
const clickOffset = ref(2)
const operationInterval = ref(500)

const activateInstance = (instance) => {
  alert(`激活实例: ${instance.name}`)
}

const deactivateInstance = (instance) => {
  alert(`暂停实例: ${instance.name}`)
}

const viewDetails = (instance) => {
  alert(`查看实例详情: ${instance.name}`)
}

const calibrateCoordinates = () => {
  alert('开始校准控件坐标...')
}

const checkAccessibility = () => {
  alert('检查AT-SPI状态...')
}

const editCoordinate = (coord) => {
  alert(`编辑坐标: ${coord.name}`)
}

const saveSettings = () => {
  alert('人性化参数已保存')
}
</script>

<style scoped>
.wechat-automation {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.automation-section {
  margin-bottom: 30px;
  padding: 20px;
  background-color: #fafafa;
  border-radius: 8px;
}

.instances-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.instance-card {
  background: white;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.instance-header {
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

.status-badge.idle {
  background-color: #fff3cd;
  color: #856404;
}

.instance-info p {
  margin: 5px 0;
  color: #666;
}

.instance-actions {
  margin-top: 15px;
  display: flex;
  gap: 8px;
}

.adapter-section {
  padding: 15px;
  background-color: white;
  border-radius: 8px;
}

.adapter-controls {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.coordinates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 15px;
}

.coordinate-item {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 12px;
  border-left: 4px solid #007bff;
}

.coord-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.coord-status {
  background-color: #d4edda;
  color: #155724;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.8em;
}

.coord-values p {
  margin: 5px 0;
  font-size: 0.9em;
  color: #555;
}

.coord-actions {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
}

.humanization-settings {
  padding: 15px;
  background-color: white;
  border-radius: 8px;
}

.setting-group {
  margin-bottom: 15px;
}

.setting-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 600;
  color: #555;
}

.slider {
  width: 100%;
  margin-bottom: 5px;
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

.btn-success {
  background-color: #28a745;
  color: white;
}

.btn-info {
  background-color: #17a2b8;
  color: white;
}

.btn-warning {
  background-color: #ffc107;
  color: #212529;
}

.btn:hover {
  opacity: 0.9;
}
</style>
