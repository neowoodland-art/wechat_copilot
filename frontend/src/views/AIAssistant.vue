<template>
  <div class="ai-assistant">
    <h2>AI助手</h2>
    
    <div class="ai-section">
      <h3>意图识别配置</h3>
      <div class="intent-config">
        <div class="intent-form">
          <div class="form-group">
            <label>意图类型:</label>
            <select v-model="newIntent.type" class="form-control">
              <option value="price_inquiry">询价</option>
              <option value="complaint">投诉</option>
              <option value="purchase_intention">购买意向</option>
              <option value="support">技术支持</option>
              <option value="other">其他</option>
            </select>
          </div>
          <div class="form-group">
            <label>关键词:</label>
            <input v-model="newIntent.keywords" placeholder="请输入关键词，用逗号分隔" class="form-control" />
          </div>
          <div class="form-group">
            <label>描述:</label>
            <textarea v-model="newIntent.description" placeholder="意图描述" class="form-control" rows="2"></textarea>
          </div>
          <button @click="saveIntent" class="btn btn-primary">保存意图</button>
        </div>
        
        <div class="intents-list">
          <div v-for="intent in intents" :key="intent.id" class="intent-item">
            <div class="intent-header">
              <span class="intent-type">{{ intent.type }}</span>
              <button @click="deleteIntent(intent.id)" class="btn btn-sm btn-danger">删除</button>
            </div>
            <p><strong>关键词:</strong> {{ intent.keywords }}</p>
            <p><strong>描述:</strong> {{ intent.description }}</p>
          </div>
        </div>
      </div>
    </div>
    
    <div class="ai-section">
      <h3>智能回复策略</h3>
      <div class="reply-strategy">
        <div class="strategy-option">
          <h4>知识库关联</h4>
          <p>上传业务文档(PDF/Doc)，基于RAG进行智能问答</p>
          <input type="file" accept=".pdf,.doc,.docx" @change="uploadKnowledgeBase" />
        </div>
        
        <div class="strategy-option">
          <h4>人工干预模式</h4>
          <p>AI生成草稿，人工一键确认发送</p>
          <div class="draft-area">
            <textarea v-model="aiDraft" placeholder="AI生成的回复草稿将显示在此处..." class="form-control" rows="4"></textarea>
            <div class="draft-actions">
              <button @click="approveDraft" class="btn btn-success">批准发送</button>
              <button @click="rejectDraft" class="btn btn-secondary">拒绝重写</button>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="ai-section">
      <h3>情感监控</h3>
      <div class="sentiment-monitor">
        <div class="sentiment-card" v-for="conversation in conversations" :key="conversation.id">
          <div class="conversation-header">
            <span :class="['sentiment-level', conversation.sentiment]">{{ conversation.sentiment }}</span>
            <span class="customer-name">{{ conversation.customer }}</span>
          </div>
          <div class="conversation-preview">
            <p>{{ conversation.preview }}</p>
          </div>
          <div class="conversation-actions">
            <button @click="escalateToHuman(conversation.id)" class="btn btn-warning">转人工</button>
            <button @click="viewFullConversation(conversation.id)" class="btn btn-info">查看详情</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const newIntent = ref({
  type: 'price_inquiry',
  keywords: '',
  description: ''
})

const intents = ref([
  {
    id: 1,
    type: 'price_inquiry',
    keywords: '价格,多少钱,报价,费用',
    description: '客户询问产品价格'
  },
  {
    id: 2,
    type: 'complaint',
    keywords: '投诉,问题,不好,差劲',
    description: '客户投诉产品质量或服务'
  }
])

const aiDraft = ref('')
const conversations = ref([
  {
    id: 1,
    customer: '张三',
    sentiment: 'positive',
    preview: '客户很满意我们的服务...'
  },
  {
    id: 2,
    customer: '李四',
    sentiment: 'negative',
    preview: '客户对产品提出了质疑...'
  },
  {
    id: 3,
    customer: '王五',
    sentiment: 'neutral',
    preview: '客户询问了产品的具体功能...'
  }
])

const saveIntent = () => {
  if (newIntent.value.type && newIntent.value.keywords) {
    const intent = {
      id: intents.value.length + 1,
      ...newIntent.value
    }
    intents.value.push(intent)
    newIntent.value = {
      type: 'price_inquiry',
      keywords: '',
      description: ''
    }
    alert('意图配置已保存')
  }
}

const deleteIntent = (id) => {
  intents.value = intents.value.filter(intent => intent.id !== id)
}

const uploadKnowledgeBase = (event) => {
  const file = event.target.files[0]
  if (file) {
    alert(`上传知识库文件: ${file.name}`)
  }
}

const approveDraft = () => {
  if (aiDraft.value.trim()) {
    alert('AI草稿已批准发送')
    aiDraft.value = ''
  } else {
    alert('没有AI草稿可发送')
  }
}

const rejectDraft = () => {
  aiDraft.value = ''
  alert('AI草稿已被拒绝，请重新生成')
}

const escalateToHuman = (id) => {
  alert(`将对话 ${id} 转交人工客服`)
}

const viewFullConversation = (id) => {
  alert(`查看对话 ${id} 详情`)
}
</script>

<style scoped>
.ai-assistant {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.ai-section {
  margin-bottom: 30px;
  padding: 20px;
  background-color: #fafafa;
  border-radius: 8px;
}

.intent-config {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.intent-form {
  flex: 1;
  min-width: 300px;
  background: white;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.intents-list {
  flex: 2;
  min-width: 300px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 600;
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

.intent-item {
  background: white;
  padding: 15px;
  margin-bottom: 10px;
  border-radius: 8px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
  border-left: 4px solid #17a2b8;
}

.intent-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.intent-type {
  background-color: #e3f2fd;
  color: #1976d2;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.9em;
  font-weight: bold;
}

.reply-strategy {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
}

.strategy-option {
  background: white;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.draft-area {
  margin-top: 10px;
}

.draft-actions {
  margin-top: 10px;
  display: flex;
  gap: 10px;
}

.sentiment-monitor {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 15px;
}

.sentiment-card {
  background: white;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.conversation-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.sentiment-level {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.8em;
  font-weight: bold;
}

.sentiment-level.positive {
  background-color: #d4edda;
  color: #155724;
}

.sentiment-level.negative {
  background-color: #f8d7da;
  color: #721c24;
}

.sentiment-level.neutral {
  background-color: #fff3cd;
  color: #856404;
}

.customer-name {
  font-weight: bold;
}

.conversation-preview {
  margin: 10px 0;
  padding: 10px;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.conversation-actions {
  display: flex;
  gap: 10px;
  margin-top: 10px;
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

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn-danger {
  background-color: #dc3545;
  color: white;
}

.btn:hover {
  opacity: 0.9;
}
</style>
