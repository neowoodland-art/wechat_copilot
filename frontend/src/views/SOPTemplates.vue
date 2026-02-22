<!-- /home/neogh/wechat_copilot/frontend/src/views/SOPTemplates.vue -->
<template>
  <div class="sop-templates">
    <h2>SOP模板库</h2>
    
    <div class="template-filters">
      <input v-model="searchQuery" placeholder="搜索模板..." class="search-input" />
      <select v-model="selectedCategory" class="category-select">
        <option value="">所有分类</option>
        <option value="welcome">欢迎系列</option>
        <option value="followup">跟进系列</option>
        <option value="sales">销售系列</option>
        <option value="support">支持系列</option>
      </select>
    </div>
    
    <div class="templates-grid">
      <div 
        v-for="template in filteredTemplates" 
        :key="template.id" 
        class="template-card"
        @click="selectTemplate(template)"
      >
        <div class="template-header">
          <h3>{{ template.name }}</h3>
          <span class="category-badge">{{ getCategoryName(template.category) }}</span>
        </div>
        <p class="template-description">{{ template.description }}</p>
        <div class="template-stats">
          <span class="stat"><strong>{{ template.nodesCount }}</strong> 个节点</span>
          <span class="stat"><strong>{{ template.averageDuration }}</strong> 分钟</span>
          <span class="stat"><strong>{{ template.successRate }}%</strong> 成功率</span>
        </div>
        <div class="template-preview">
          <div class="preview-step" v-for="(step, index) in template.stepsPreview" :key="index">
            <span class="step-number">{{ index + 1 }}</span>
            <span class="step-name">{{ step }}</span>
          </div>
        </div>
        <div class="template-actions">
          <button @click.stop="useTemplate(template)" class="btn btn-primary">使用模板</button>
          <button @click.stop="previewTemplate(template)" class="btn btn-info">预览</button>
        </div>
      </div>
    </div>
    
    <div v-if="selectedTemplate" class="template-detail-modal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ selectedTemplate.name }}</h3>
          <button @click="closeModal" class="close-btn">×</button>
        </div>
        <div class="modal-body">
          <p>{{ selectedTemplate.description }}</p>
          <h4>流程详情:</h4>
          <pre class="template-json">{{ JSON.stringify(selectedTemplate.definition, null, 2) }}</pre>
        </div>
        <div class="modal-footer">
          <button @click="closeModal" class="btn btn-secondary">关闭</button>
          <button @click="applyTemplate" class="btn btn-primary">应用模板</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const searchQuery = ref('')
const selectedCategory = ref('')
const selectedTemplate = ref(null)

const templates = ref([
  {
    id: 1,
    name: '新客户欢迎SOP',
    category: 'welcome',
    description: '针对新添加好友的客户执行的欢迎和初步沟通流程',
    nodesCount: 5,
    averageDuration: 10,
    successRate: 85,
    stepsPreview: ['等待1分钟', '发送欢迎消息', '判断客户回复', '积极回复处理', '标记客户'],
    definition: {
      "sopDefinition": {
        "id": "sop_001",
        "name": "新客户欢迎SOP",
        "description": "针对新添加好友的客户执行的欢迎和初步沟通流程",
        "version": "1.0.0",
        "nodes": [
          {
            "id": "node_001",
            "type": "delay",
            "name": "等待1分钟",
            "position": { "x": 100, "y": 100 },
            "properties": {
              "duration": 60000
            },
            "next": ["node_002"]
          },
          {
            "id": "node_002",
            "type": "message",
            "name": "发送欢迎消息",
            "position": { "x": 300, "y": 100 },
            "properties": {
              "messageType": "text",
              "content": "您好，我是{{customerName}}的专属客服，很高兴认识您！",
              "delayBeforeSend": 2000
            },
            "next": ["node_003"]
          }
        ]
      }
    }
  },
  {
    id: 2,
    name: '询价跟进SOP',
    category: 'followup',
    description: '对询价客户的后续跟进流程',
    nodesCount: 7,
    averageDuration: 15,
    successRate: 78,
    stepsPreview: ['检测询价消息', '分析需求', '提供方案', '预约演示', '跟进反馈', '促成成交', '售后服务'],
    definition: {
      "sopDefinition": {
        "id": "sop_002",
        "name": "询价跟进SOP",
        "description": "对询价客户的后续跟进流程",
        "version": "1.0.0",
        "nodes": [
          {
            "id": "node_001",
            "type": "condition",
            "name": "检测询价消息",
            "position": { "x": 100, "y": 100 },
            "properties": {
              "conditions": [
                {
                  "operator": "contains",
                  "field": "lastMessage.content",
                  "value": ["价格", "多少钱", "报价", "费用"]
                }
              ]
            },
            "next": ["node_002"]
          }
        ]
      }
    }
  },
  {
    id: 3,
    name: '客户挽回SOP',
    category: 'sales',
    description: '针对流失客户的挽回策略',
    nodesCount: 6,
    averageDuration: 20,
    successRate: 65,
    stepsPreview: ['检测沉默期', '发送关怀消息', '了解原因', '解决问题', '提供优惠', '持续跟进'],
    definition: {
      "sopDefinition": {
        "id": "sop_003",
        "name": "客户挽回SOP",
        "description": "针对流失客户的挽回策略",
        "version": "1.0.0",
        "nodes": [
          {
            "id": "node_001",
            "type": "condition",
            "name": "检测沉默期",
            "position": { "x": 100, "y": 100 },
            "properties": {
              "conditions": [
                {
                  "operator": ">",
                  "field": "lastContactDays",
                  "value": 30
                }
              ]
            },
            "next": ["node_002"]
          }
        ]
      }
    }
  }
])

const categories = {
  welcome: '欢迎系列',
  followup: '跟进系列',
  sales: '销售系列',
  support: '支持系列'
}

const filteredTemplates = computed(() => {
  return templates.value.filter(template => {
    const matchesSearch = template.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
                         template.description.toLowerCase().includes(searchQuery.value.toLowerCase())
    const matchesCategory = !selectedCategory.value || template.category === selectedCategory.value
    return matchesSearch && matchesCategory
  })
})

const getCategoryName = (category) => {
  return categories[category] || category
}

const selectTemplate = (template) => {
  selectedTemplate.value = template
}

const closeModal = () => {
  selectedTemplate.value = null
}

const useTemplate = (template) => {
  // 将模板应用到新的SOP编辑器
  router.push({
    path: '/sop-editor',
    query: { 
      templateId: template.id,
      templateName: encodeURIComponent(template.name)
    }
  })
}

const previewTemplate = (template) => {
  selectTemplate(template)
}

const applyTemplate = () => {
  if (selectedTemplate.value) {
    useTemplate(selectedTemplate.value)
  }
}
</script>

<style scoped>
.sop-templates {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.template-filters {
  display: flex;
  gap: 15px;
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

.category-select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
}

.template-card {
  background: white;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.template-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 5px 15px rgba(0,0,0,0.15);
}

.template-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.category-badge {
  background-color: #e3f2fd;
  color: #1976d2;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.8em;
  font-weight: bold;
}

.template-description {
  color: #666;
  margin-bottom: 15px;
  line-height: 1.4;
}

.template-stats {
  display: flex;
  gap: 15px;
  margin-bottom: 15px;
  font-size: 0.9em;
}

.stat {
  background-color: #f8f9fa;
  padding: 4px 8px;
  border-radius: 4px;
}

.template-preview {
  margin-bottom: 15px;
  padding: 10px;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.preview-step {
  display: flex;
  align-items: center;
  margin-bottom: 5px;
  font-size: 0.9em;
}

.step-number {
  display: inline-block;
  width: 20px;
  height: 20px;
  background-color: #007bff;
  color: white;
  border-radius: 50%;
  text-align: center;
  line-height: 20px;
  margin-right: 8px;
  font-size: 0.8em;
}

.template-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
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

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn:hover {
  opacity: 0.9;
}

.template-detail-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  width: 80%;
  max-width: 800px;
  max-height: 80vh;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  padding: 15px 20px;
  background-color: #f8f9fa;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #dee2e6;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #6c757d;
}

.modal-body {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
}

.template-json {
  background-color: #f8f9fa;
  padding: 10px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  max-height: 300px;
  overflow: auto;
  margin-top: 10px;
}

.modal-footer {
  padding: 15px 20px;
  background-color: #f8f9fa;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  border-top: 1px solid #dee2e6;
}
</style>
