<template>
  <div class="customers">
    <h2>客户与标签管理</h2>
    
    <div class="customer-section">
      <div class="controls">
        <input v-model="searchQuery" placeholder="搜索客户..." class="search-input" />
        <button @click="addCustomer" class="btn btn-primary">添加客户</button>
        <select v-model="filterByTag" class="filter-select">
          <option value="">所有标签</option>
          <option v-for="tag in availableTags" :key="tag" :value="tag">{{ tag }}</option>
        </select>
      </div>
      
      <div class="customers-grid">
        <div v-for="customer in filteredCustomers" :key="customer.id" class="customer-card">
          <div class="customer-header">
            <div class="avatar">{{ customer.avatar }}</div>
            <div class="customer-info">
              <h4>{{ customer.name }}</h4>
              <p>{{ customer.nickname }}</p>
            </div>
          </div>
          
          <div class="customer-details">
            <p><strong>微信号:</strong> {{ customer.wechatId }}</p>
            <p><strong>备注:</strong> {{ customer.remark || '-' }}</p>
            <p><strong>标签:</strong> 
              <span v-for="tag in customer.tags" :key="tag" class="tag-badge">{{ tag }}</span>
            </p>
          </div>
          
          <div class="sop-history">
            <p><strong>SOP执行记录:</strong></p>
            <div class="history-list">
              <div v-for="record in customer.sopHistory" :key="record.id" class="history-item">
                <span class="sop-name">{{ record.sopName }}</span>
                <span class="executed-at">{{ record.executedAt }}</span>
                <span :class="['status', record.status]">{{ record.status }}</span>
              </div>
            </div>
          </div>
          
          <div class="customer-actions">
            <button @click="viewProfile(customer)" class="btn btn-sm btn-info">查看档案</button>
            <button @click="runCustomerPipeline(customer)" class="btn btn-sm btn-success">更新画像链路</button>
            <button @click="runCustomerSchedule(customer)" class="btn btn-sm btn-primary">一键调度</button>
            <button @click="toggleWhitelist(customer)" class="btn btn-sm btn-warning">
              {{ customer.whitelisted ? '取消白名单' : '加入白名单' }}
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <div class="tags-section">
      <h3>动态标签管理</h3>
      <div class="tag-manager">
        <div class="tag-form">
          <input v-model="newTag.name" placeholder="标签名称" class="form-control" />
          <input v-model="newTag.rule" placeholder="规则表达式" class="form-control" />
          <button @click="createTag" class="btn btn-primary">创建标签</button>
        </div>
        
        <div class="tags-list">
          <div v-for="tag in dynamicTags" :key="tag.id" class="tag-item">
            <div class="tag-header">
              <span class="tag-name">{{ tag.name }}</span>
              <span class="tag-rule">{{ tag.rule }}</span>
            </div>
            <div class="tag-stats">
              <span>应用到 {{ tag.appliedCount }} 位客户</span>
              <span>更新时间: {{ tag.updatedAt }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  fetchCRMProfiles,
  fetchCRMOverview,
  importCRMWechatHistory,
  generateCRMSummary,
  generateCRMPortrait,
  generateCRMTags,
  runCRMScheduleNow
} from '../api'

const searchQuery = ref('')
const filterByTag = ref('')
const newTag = ref({
  name: '',
  rule: ''
})

const customers = ref([
  {
    id: 0,
    avatar: '-',
    name: '加载中',
    nickname: '-',
    wechatId: '-',
    remark: '',
    tags: [],
    whitelisted: false,
    sopHistory: []
  }
])

const dynamicTags = ref([
  {
    id: 1,
    name: '高意向',
    rule: 'AI聊天内容包含购买意向关键词',
    appliedCount: 42,
    updatedAt: '2026-02-15'
  },
  {
    id: 2,
    name: '老客户',
    rule: '聊天记录超过30天',
    appliedCount: 120,
    updatedAt: '2026-02-14'
  }
])

const availableTags = computed(() => {
  const allTags = new Set()
  customers.value.forEach(customer => {
    customer.tags.forEach(tag => allTags.add(tag))
  })
  return Array.from(allTags)
})

const filteredCustomers = computed(() => {
  let result = customers.value
  
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(customer => 
      customer.name.toLowerCase().includes(query) ||
      customer.nickname.toLowerCase().includes(query) ||
      customer.wechatId.toLowerCase().includes(query)
    )
  }
  
  if (filterByTag.value) {
    result = result.filter(customer => customer.tags.includes(filterByTag.value))
  }
  
  return result
})

const addCustomer = () => {
  alert('添加新客户')
}

const viewProfile = async (customer) => {
  try {
    const data = await fetchCRMOverview(customer.id)
    const summary = data?.latest_summary?.content || '暂无摘要'
    const portrait = data?.latest_portrait?.json || {}
    alert(`客户: ${customer.name}\n摘要: ${summary}\n画像: ${JSON.stringify(portrait, null, 2)}`)
  } catch (error) {
    alert(`加载客户档案失败: ${error.message}`)
  }
}

const toggleWhitelist = (customer) => {
  customer.whitelisted = !customer.whitelisted
  alert(`${customer.whitelisted ? '已加入' : '已移除'}白名单: ${customer.name}`)
}

const createTag = () => {
  if (newTag.value.name && newTag.value.rule) {
    const tag = {
      id: dynamicTags.value.length + 1,
      ...newTag.value,
      appliedCount: 0,
      updatedAt: new Date().toISOString().split('T')[0]
    }
    dynamicTags.value.push(tag)
    newTag.value = { name: '', rule: '' }
    alert('动态标签已创建')
  }
}

const mapCustomer = (item) => {
  const name = item.name || item.nickname || `客户${item.id}`
  return {
    id: item.id,
    avatar: (name || '-').slice(0, 1),
    name,
    nickname: item.nickname || name,
    wechatId: item.wechatId || '',
    remark: item.summary || '',
    tags: Array.isArray(item.tags) ? item.tags : [],
    whitelisted: false,
    sopHistory: [
      { id: 1, sopName: '摘要更新时间', executedAt: item.lastContact || '-', status: '成功' },
      { id: 2, sopName: '画像更新时间', executedAt: item.portraitUpdatedAt || '-', status: '成功' }
    ]
  }
}

const loadCustomers = async () => {
  try {
    const data = await fetchCRMProfiles({ keyword: searchQuery.value || undefined })
    const items = data?.items || []
    customers.value = items.map(mapCustomer)
  } catch (error) {
    alert(`加载客户失败: ${error.message}`)
  }
}

const runCustomerPipeline = async (customer) => {
  try {
    await importCRMWechatHistory({ customer_id: customer.id })
    await generateCRMSummary({ customer_id: customer.id, summary_days: 3 })
    await generateCRMPortrait({ customer_id: customer.id })
    await generateCRMTags({ customer_id: customer.id })
    await loadCustomers()
    alert(`客户 ${customer.name} 已完成聊天沉淀 + 摘要 + 画像 + 标签更新`)
  } catch (error) {
    alert(`更新失败: ${error.message}`)
  }
}

const runCustomerSchedule = async (customer) => {
  try {
    await runCRMScheduleNow({ customer_id: customer.id, summary_days: 3 })
    await loadCustomers()
    alert(`客户 ${customer.name} 已执行一键调度`)
  } catch (error) {
    alert(`调度失败: ${error.message}`)
  }
}

onMounted(async () => {
  await loadCustomers()
})
</script>

<style scoped>
.customers {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.customer-section {
  margin-bottom: 30px;
}

.controls {
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

.filter-select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.customers-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
}

.customer-card {
  background: white;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.customer-header {
  display: flex;
  gap: 15px;
  align-items: center;
  margin-bottom: 15px;
}

.avatar {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background-color: #007bff;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}

.customer-info h4 {
  margin: 0;
  color: #333;
}

.customer-info p {
  margin: 2px 0;
  color: #666;
  font-size: 0.9em;
}

.customer-details p {
  margin: 5px 0;
  font-size: 0.9em;
  color: #555;
}

.tag-badge {
  display: inline-block;
  background-color: #e3f2fd;
  color: #1976d2;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.8em;
  margin-right: 4px;
}

.sop-history {
  margin: 15px 0;
  padding: 10px;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.history-list {
  margin-top: 8px;
}

.history-item {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 0.9em;
  border-bottom: 1px solid #eee;
}

.history-item:last-child {
  border-bottom: none;
}

.sop-name {
  color: #333;
}

.executed-at {
  color: #666;
}

.status {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.8em;
  font-weight: bold;
}

.status.success {
  background-color: #d4edda;
  color: #155724;
}

.customer-actions {
  margin-top: 15px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
</style>