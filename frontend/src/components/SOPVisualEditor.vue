<!-- /home/neogh/wechat_copilot/frontend/src/components/SOPVisualEditor.vue -->
<template>
  <div class="sop-visual-editor">
    <div class="editor-toolbar">
      <div class="toolbar-section">
        <h4>节点类型</h4>
        <div class="node-palette">
          <div 
            class="node-item" 
            draggable="true" 
            @dragstart="onDragStart($event, 'delay')"
          >
            <div class="node-icon">⏱️</div>
            <div class="node-label">等待</div>
          </div>
          <div 
            class="node-item" 
            draggable="true" 
            @dragstart="onDragStart($event, 'message')"
          >
            <div class="node-icon">💬</div>
            <div class="node-label">发送消息</div>
          </div>
          <div 
            class="node-item" 
            draggable="true" 
            @dragstart="onDragStart($event, 'condition')"
          >
            <div class="node-icon">❓</div>
            <div class="node-label">条件判断</div>
          </div>
          <div 
            class="node-item" 
            draggable="true" 
            @dragstart="onDragStart($event, 'tagCustomer')"
          >
            <div class="node-icon">🏷️</div>
            <div class="node-label">客户标记</div>
          </div>
          <div 
            class="node-item" 
            draggable="true" 
            @dragstart="onDragStart($event, 'ocrVerify')"
          >
            <div class="node-icon">🔍</div>
            <div class="node-label">OCR验证</div>
          </div>
        </div>
      </div>
      
      <div class="toolbar-section">
        <h4>操作</h4>
        <div class="action-buttons">
          <button @click="saveSOP" class="btn btn-primary">保存SOP</button>
          <button @click="loadSOP" class="btn btn-info">加载SOP</button>
          <button @click="runSOP" class="btn btn-success">运行SOP</button>
          <button @click="clearCanvas" class="btn btn-warning">清空画布</button>
        </div>
      </div>
    </div>
    
    <div class="editor-canvas" @drop="onDrop" @dragover="allowDrop">
      <div 
        v-for="node in nodes" 
        :key="node.id" 
        class="node" 
        :style="{ left: node.position.x + 'px', top: node.position.y + 'px' }"
        @click="selectNode(node)"
        :class="{ selected: selectedNode?.id === node.id }"
      >
        <div class="node-header" :class="getNodeClass(node.type)">
          <div class="node-type">{{ getNodeTypeName(node.type) }}</div>
          <div class="node-actions">
            <button @click.stop="deleteNode(node.id)" class="node-btn">×</button>
          </div>
        </div>
        <div class="node-content">
          <div v-if="node.properties.name" class="node-name">{{ node.properties.name }}</div>
          <div v-if="node.type === 'delay'" class="node-property">
            等待: {{ node.properties.duration / 1000 }}秒
          </div>
          <div v-if="node.type === 'message'" class="node-property">
            内容: {{ node.properties.content.substring(0, 20) }}...
          </div>
          <div v-if="node.type === 'condition'" class="node-property">
            条件: {{ node.properties.conditions?.length || 0 }}个
          </div>
        </div>
        <div class="node-connector-out" @mousedown="startConnection(node.id, 'out')"></div>
      </div>
      
      <!-- 连接线 -->
      <svg class="connection-lines" ref="svgRef" :style="{ width: canvasWidth + 'px', height: canvasHeight + 'px' }">
        <path 
          v-for="edge in edges" 
          :key="`${edge.source}-${edge.target}`"
          :d="getPathDescription(edge)"
          stroke="#666"
          stroke-width="2"
          fill="none"
          marker-end="url(#arrowhead)"
        />
      </svg>
      
      <!-- SVG箭头标记定义 -->
      <svg style="position: absolute; left: 0; top: 0; width: 0; height: 0;">
        <defs>
          <marker 
            id="arrowhead" 
            markerWidth="10" 
            markerHeight="7" 
            refX="9" 
            refY="3.5" 
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#666" />
          </marker>
        </defs>
      </svg>
    </div>
    
    <div v-if="selectedNode" class="node-properties-panel">
      <h4>节点属性</h4>
      <div class="property-group">
        <label>节点名称:</label>
        <input v-model="selectedNode.properties.name" class="form-control" />
      </div>
      
      <div v-if="selectedNode.type === 'delay'" class="property-group">
        <label>等待时间 (毫秒):</label>
        <input 
          v-model.number="selectedNode.properties.duration" 
          type="number" 
          class="form-control" 
        />
      </div>
      
      <div v-if="selectedNode.type === 'message'" class="property-group">
        <label>消息内容:</label>
        <textarea 
          v-model="selectedNode.properties.content" 
          class="form-control" 
          rows="3"
        ></textarea>
        <label>消息类型:</label>
        <select v-model="selectedNode.properties.messageType" class="form-control">
          <option value="text">文本</option>
          <option value="image">图片</option>
          <option value="emoji">表情</option>
        </select>
      </div>
      
      <div v-if="selectedNode.type === 'condition'" class="property-group">
        <label>条件设置:</label>
        <div class="condition-editor">
          <div v-for="(condition, index) in selectedNode.properties.conditions" :key="index" class="condition-item">
            <select v-model="condition.operator" class="form-control">
              <option value="contains">包含</option>
              <option value="equals">等于</option>
              <option value="startsWith">开头是</option>
              <option value="endsWith">结尾是</option>
            </select>
            <input v-model="condition.field" placeholder="字段名" class="form-control" />
            <input v-model="condition.value" placeholder="匹配值" class="form-control" />
            <button @click="removeCondition(index)" class="btn btn-sm btn-danger">删除</button>
          </div>
          <button @click="addCondition" class="btn btn-sm btn-info">添加条件</button>
        </div>
      </div>
      
      <div v-if="selectedNode.type === 'tagCustomer'" class="property-group">
        <label>添加标签:</label>
        <input 
          v-model="selectedNode.properties.tagsToAddInput" 
          placeholder="输入标签，用逗号分隔" 
          class="form-control"
          @change="updateTagsToAdd"
        />
        <label>移除标签:</label>
        <input 
          v-model="selectedNode.properties.tagsToRemoveInput" 
          placeholder="输入标签，用逗号分隔" 
          class="form-control"
          @change="updateTagsToRemove"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'

// 编辑器状态
const nodes = ref([])
const edges = ref([])
const selectedNode = ref(null)
const draggingNode = ref(null)
const connecting = ref(false)
const connectionStart = ref(null)
const svgRef = ref(null)
const canvasWidth = ref(2000)
const canvasHeight = ref(1000)

// 节点类型映射
const nodeTypes = {
  delay: { icon: '⏱️', name: '等待', class: 'delay-node' },
  message: { icon: '💬', name: '消息', class: 'message-node' },
  condition: { icon: '❓', name: '条件', class: 'condition-node' },
  tagCustomer: { icon: '🏷️', name: '标记', class: 'tag-node' },
  ocrVerify: { icon: '🔍', name: 'OCR', class: 'ocr-node' }
}

// 初始化示例SOP
const initializeExampleSOP = () => {
  nodes.value = [
    {
      id: 'node_001',
      type: 'delay',
      properties: {
        name: '等待1分钟',
        duration: 60000
      },
      position: { x: 100, y: 100 }
    },
    {
      id: 'node_002',
      type: 'message',
      properties: {
        name: '发送欢迎消息',
        messageType: 'text',
        content: '您好，我是{{customerName}}的专属客服，很高兴认识您！'
      },
      position: { x: 300, y: 100 }
    },
    {
      id: 'node_003',
      type: 'condition',
      properties: {
        name: '判断客户是否回复',
        conditions: [
          {
            operator: 'contains',
            field: 'lastMessage.content',
            value: ['你好', '您好', '谢谢'],
            then: 'node_004'
          },
          {
            operator: 'contains',
            field: 'lastMessage.content',
            value: ['不需要', '算了', '再见'],
            then: 'node_006'
          }
        ]
      },
      position: { x: 500, y: 100 }
    }
  ]
  
  edges.value = [
    { source: 'node_001', target: 'node_002', type: 'direct' },
    { source: 'node_002', target: 'node_003', type: 'direct' }
  ]
}

// 拖拽事件处理
const onDragStart = (event, nodeType) => {
  event.dataTransfer.setData('nodeType', nodeType)
}

const allowDrop = (event) => {
  event.preventDefault()
}

const onDrop = async (event) => {
  event.preventDefault()
  const nodeType = event.dataTransfer.getData('nodeType')
  const rect = event.currentTarget.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top
  
  // 添加新节点
  const newNode = {
    id: `node_${Date.now()}`,
    type: nodeType,
    properties: getDefaultProperties(nodeType),
    position: { x, y }
  }
  
  nodes.value.push(newNode)
}

const getDefaultProperties = (type) => {
  switch (type) {
    case 'delay':
      return { name: '等待', duration: 5000 }
    case 'message':
      return { name: '发送消息', messageType: 'text', content: '' }
    case 'condition':
      return { name: '条件判断', conditions: [] }
    case 'tagCustomer':
      return { name: '客户标记', tagsToAdd: [], tagsToAddInput: '', tagsToRemove: [], tagsToRemoveInput: '' }
    case 'ocrVerify':
      return { name: 'OCR验证', targetElement: '', expectedText: '' }
    default:
      return { name: type }
  }
}

// 节点选择和操作
const selectNode = (node) => {
  selectedNode.value = node
}

const deleteNode = (nodeId) => {
  nodes.value = nodes.value.filter(node => node.id !== nodeId)
  edges.value = edges.value.filter(edge => edge.source !== nodeId && edge.target !== nodeId)
  if (selectedNode.value?.id === nodeId) {
    selectedNode.value = null
  }
}

const clearCanvas = () => {
  nodes.value = []
  edges.value = []
  selectedNode.value = null
}

// 工具函数
const getNodeClass = (type) => {
  return nodeTypes[type]?.class || 'default-node'
}

const getNodeTypeName = (type) => {
  return nodeTypes[type]?.name || type
}

// 属性面板操作
const addCondition = () => {
  if (selectedNode.value && selectedNode.value.type === 'condition') {
    selectedNode.value.properties.conditions.push({
      operator: 'contains',
      field: '',
      value: '',
      then: ''
    })
  }
}

const removeCondition = (index) => {
  if (selectedNode.value && selectedNode.value.type === 'condition') {
    selectedNode.value.properties.conditions.splice(index, 1)
  }
}

const updateTagsToAdd = () => {
  if (selectedNode.value) {
    selectedNode.value.properties.tagsToAdd = 
      selectedNode.value.properties.tagsToAddInput.split(',').map(tag => tag.trim()).filter(tag => tag)
  }
}

const updateTagsToRemove = () => {
  if (selectedNode.value) {
    selectedNode.value.properties.tagsToRemove = 
      selectedNode.value.properties.tagsToRemoveInput.split(',').map(tag => tag.trim()).filter(tag => tag)
  }
}

// 连接线相关
const startConnection = (nodeId, type) => {
  connecting.value = true
  connectionStart.value = nodeId
  // 在这里可以添加连接线起始逻辑
}

const getPathDescription = (edge) => {
  // 简单的直线路径计算
  const sourceNode = nodes.value.find(n => n.id === edge.source)
  const targetNode = nodes.value.find(n => n.id === edge.target)
  
  if (!sourceNode || !targetNode) return ''
  
  const sourceX = sourceNode.position.x + 100 // 假设节点宽度为100
  const sourceY = sourceNode.position.y + 30  // 假设节点高度的一半
  const targetX = targetNode.position.x
  const targetY = targetNode.position.y + 30
  
  return `M ${sourceX} ${sourceY} L ${targetX} ${targetY}`
}

// 保存和加载SOP
const saveSOP = () => {
  const sopData = {
    nodes: nodes.value,
    edges: edges.value,
    metadata: {
      name: '新SOP流程',
      description: '自动生成的SOP流程',
      createdAt: new Date().toISOString()
    }
  }
  
  // 这里可以调用API保存到后端
  console.log('保存SOP:', JSON.stringify(sopData, null, 2))
  alert('SOP已保存到控制台，实际项目中会保存到后端')
}

const loadSOP = () => {
  // 这里可以从后端加载SOP数据
  initializeExampleSOP()
  alert('已加载示例SOP')
}

const runSOP = () => {
  if (nodes.value.length === 0) {
    alert('请先添加节点')
    return
  }
  
  // 这里可以调用API执行SOP
  console.log('执行SOP:', nodes.value)
  alert('SOP执行请求已发送到后端')
}

// 初始化
onMounted(() => {
  initializeExampleSOP()
})
</script>

<style scoped>
.sop-visual-editor {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: #f5f5f5;
}

.editor-toolbar {
  display: flex;
  padding: 10px;
  background-color: #fff;
  border-bottom: 1px solid #ddd;
  gap: 20px;
}

.toolbar-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.node-palette {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.node-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background-color: #fff;
  cursor: grab;
  transition: all 0.2s;
}

.node-item:hover {
  background-color: #e9ecef;
  transform: translateY(-2px);
}

.node-icon {
  font-size: 24px;
  margin-bottom: 5px;
}

.node-label {
  font-size: 12px;
  text-align: center;
}

.action-buttons {
  display: flex;
  gap: 10px;
}

.editor-canvas {
  flex: 1;
  position: relative;
  overflow: auto;
  background-image: 
    radial-gradient(circle, #cbd5e0 1px, transparent 1px);
  background-size: 20px 20px;
  min-height: 600px;
}

.connection-lines {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
  z-index: 1;
}

.node {
  position: absolute;
  min-width: 120px;
  border-radius: 6px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  z-index: 10;
  background: white;
  cursor: move;
  transition: box-shadow 0.2s;
}

.node.selected {
  box-shadow: 0 0 0 3px #007bff;
}

.node-header {
  padding: 8px 12px;
  border-radius: 6px 6px 0 0;
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.node-header.delay-node {
  background-color: #6c757d;
}

.node-header.message-node {
  background-color: #28a745;
}

.node-header.condition-node {
  background-color: #ffc107;
  color: #212529;
}

.node-header.tag-node {
  background-color: #17a2b8;
}

.node-header.ocr-node {
  background-color: #6f42c1;
}

.node-actions {
  display: flex;
  gap: 4px;
}

.node-btn {
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  font-size: 16px;
  padding: 0;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.node-btn:hover {
  background-color: rgba(255, 255, 255, 0.2);
}

.node-content {
  padding: 10px;
  font-size: 13px;
}

.node-name {
  font-weight: bold;
  margin-bottom: 5px;
  color: #333;
}

.node-property {
  color: #666;
  font-size: 12px;
  word-break: break-word;
}

.node-connector-out {
  position: absolute;
  right: -8px;
  top: 50%;
  transform: translateY(-50%);
  width: 12px;
  height: 12px;
  background-color: #666;
  border-radius: 50%;
  cursor: crosshair;
  z-index: 20;
}

.node-properties-panel {
  position: fixed;
  right: 0;
  top: 0;
  width: 300px;
  height: 100vh;
  background-color: white;
  border-left: 1px solid #ddd;
  padding: 20px;
  overflow-y: auto;
  z-index: 100;
  box-shadow: -2px 0 10px rgba(0,0,0,0.1);
}

.property-group {
  margin-bottom: 15px;
}

.property-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
  color: #555;
}

.form-control {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
}

.condition-editor {
  border: 1px solid #eee;
  border-radius: 4px;
  padding: 10px;
}

.condition-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}

.condition-item:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.btn {
  padding: 6px 12px;
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

.btn-warning {
  background-color: #ffc107;
  color: #212529;
}

.btn-danger {
  background-color: #dc3545;
  color: white;
}

.btn:hover {
  opacity: 0.9;
}
</style>
