<template>
  <div class="customer-retargeting">
    <h2>智能回访跟踪</h2>
    
    <div class="section">
      <h3>回访计划管理</h3>
      <div class="plan-controls">
        <button @click="createNewPlan" class="btn btn-primary">新建回访计划</button>
        <input v-model="searchQuery" placeholder="搜索计划..." class="search-input" />
      </div>
      
      <div class="plans-list">
        <div v-for="plan in filteredPlans" :key="plan.id" class="plan-card">
          <div class="plan-header">
            <h4>{{ plan.name }}</h4>
            <span :class="['status-badge', plan.status]">{{ plan.status }}</span>
          </div>
          <div class="plan-details">
            <p><strong>目标客户:</strong> {{ plan.targetCustomers }} 人</p>
            <p><strong>执行频率:</strong> {{ plan.frequency }}</p>
            <p><strong>下次执行:</strong> {{ plan.nextExecution }}</p>
            <p><strong>成功率:</strong> {{ plan.successRate }}%</p>
          </div>
          <div class="plan-actions">
            <button @click="editPlan(plan)" class="btn btn-sm btn-info">编辑</button>
            <button @click="executePlan(plan)" class="btn btn-sm btn-success">立即执行</button>
          </div>
        </div>
      </div>
    </div>
    
    <div class="section">
      <h3>智能提醒系统</h3>
      <div class="reminders-list">
        <div v-for="reminder in reminders" :key="reminder.id" class="reminder-card">
          <div class="reminder-header">
            <h4>{{ reminder.title }}</h4>
            <span :class="['priority-badge', reminder.priority]">{{ reminder.priority }}</span>
          </div>
          <p>{{ reminder.description }}</p>
          <p><small>截止时间: {{ reminder.deadline }}</small></p>
        </div>
      </div>
    </div>
    
    <div class="section">
      <h3>回访记录分析</h3>
      <div class="analytics-charts">
        <div class="chart-container">
          <h4>回访成功率趋势</h4>
          <div class="chart-placeholder">图表显示区域</div>
        </div>
        <div class="chart-container">
          <h4>客户反馈分析</h4>
          <div class="chart-placeholder">图表显示区域</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const searchQuery = ref('')
const plans = ref([
  {
    id: 1,
    name: '新客户首周回访计划',
    status: 'active',
    targetCustomers: 120,
    frequency: '每日一次',
    nextExecution: '2026-02-16 10:00',
    successRate: 85
  },
  {
    id: 2,
    name: '沉睡客户唤醒计划',
    status: 'scheduled',
    targetCustomers: 85,
    frequency: '每周一次',
    nextExecution: '2026-02-17 14:00',
    successRate: 72
  },
  {
    id: 3,
    name: '高价值客户维护计划',
    status: 'paused',
    targetCustomers: 35,
    frequency: '每月两次',
    nextExecution: '-',
    successRate: 92
  }
])

const reminders = ref([
  {
    id: 1,
    title: '重要客户回访提醒',
    description: '客户张三已30天未联系，需要主动回访',
    priority: 'high',
    deadline: '2026-02-16 18:00'
  },
  {
    id: 2,
    title: '逾期回访预警',
    description: '有15个客户超过规定时间未回访',
    priority: 'medium',
    deadline: '2026-02-16 20:00'
  }
])

const filteredPlans = computed(() => {
  if (!searchQuery.value) {
    return plans.value
  }
  return plans.value.filter(plan => 
    plan.name.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

const createNewPlan = () => {
  alert('创建新回访计划')
}

const editPlan = (plan) => {
  alert(`编辑计划: ${plan.name}`)
}

const executePlan = (plan) => {
  alert(`立即执行计划: ${plan.name}`)
}
</script>

<style scoped>
.customer-retargeting {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.section {
  margin-bottom: 30px;
  padding: 20px;
  background-color: #fafafa;
  border-radius: 8px;
}

.plan-controls {
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

.plans-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.plan-card {
  background: white;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
  border-left: 4px solid #007bff;
}

.plan-header {
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

.status-badge.scheduled {
  background-color: #cce5ff;
  color: #004085;
}

.status-badge.paused {
  background-color: #fff3cd;
  color: #856404;
}

.plan-details p {
  margin: 5px 0;
  color: #666;
}

.plan-actions {
  margin-top: 15px;
  display: flex;
  gap: 10px;
}

.reminders-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 15px;
}

.reminder-card {
  background: white;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
  border-left: 4px solid #28a745;
}

.reminder-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.priority-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.8em;
  font-weight: bold;
}

.priority-badge.high {
  background-color: #f8d7da;
  color: #721c24;
}

.priority-badge.medium {
  background-color: #fff3cd;
  color: #856404;
}

.analytics-charts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
}

.chart-container {
  background: white;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.chart-placeholder {
  height: 200px;
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

.btn:hover {
  opacity: 0.9;
}
</style>
