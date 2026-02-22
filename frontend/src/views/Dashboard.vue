<template>
  <div class="dashboard">
    <h2>智能微信自动化系统 - 仪表盘</h2>
    
    <div class="stats-grid">
      <div class="stat-card">
        <h3>实时状态</h3>
        <div class="stat-item">
          <span class="label">微信连接</span>
          <span :class="['status', { active: systemStats.wechatConnected }]">
            {{ systemStats.wechatConnected ? '已连接' : '未连接' }}
          </span>
        </div>
        <div class="stat-item">
          <span class="label">SOP任务</span>
          <span class="value">{{ systemStats.runningSopTasks }}</span>
        </div>
        <div class="stat-item">
          <span class="label">今日回访</span>
          <span class="value">{{ systemStats.todayRetargeted }}</span>
        </div>
      </div>
      
      <div class="stat-card">
        <h3>AI效能</h3>
        <div class="stat-item">
          <span class="label">自动回复率</span>
          <span class="value">{{ systemStats.aiReplyRate }}%</span>
        </div>
        <div class="stat-item">
          <span class="label">意图识别准确率</span>
          <span class="value">{{ systemStats.intentAccuracy }}%</span>
        </div>
        <div class="stat-item">
          <span class="label">转化线索</span>
          <span class="value">{{ systemStats.convertedLeads }}</span>
        </div>
      </div>
      
      <div class="stat-card">
        <h3>系统健康度</h3>
        <div class="stat-item">
          <span class="label">C++驱动状态</span>
          <span :class="['status', { active: systemStats.cppDriverActive }]">
            {{ systemStats.cppDriverActive ? '正常' : '异常' }}
          </span>
        </div>
        <div class="stat-item">
          <span class="label">OCR引擎负载</span>
          <span class="value">{{ systemStats.ocrLoad }}%</span>
        </div>
        <div class="stat-item">
          <span class="label">内存占用</span>
          <span class="value">{{ systemStats.memoryUsage }}MB</span>
        </div>
      </div>
    </div>
    
    <div class="modules-grid">
      <div class="module-card" @click="$router.push('/customer-retargeting')">
        <div class="module-icon">👥</div>
        <h3>智能回访 Agent</h3>
        <p>基于AI的客户回访策略，提升客户留存和转化率</p>
        <div class="module-stats">
          <span>活跃计划: {{ moduleStats.retargeting.activePlans }}</span>
          <span>今日回访: {{ moduleStats.retargeting.todayRetargeted }}</span>
        </div>
      </div>
      
      <div class="module-card" @click="$router.push('/sop-management')">
        <div class="module-icon">⚙️</div>
        <h3>SOP流程引擎</h3>
        <p>可视化SOP编排，自动化业务流程管理</p>
        <div class="module-stats">
          <span>运行中SOP: {{ moduleStats.sop.runningCount }}</span>
          <span>今日执行: {{ moduleStats.sop.todayExecuted }}</span>
        </div>
      </div>
      
      <div class="module-card" @click="$router.push('/wechat-automation')">
        <div class="module-icon">📱</div>
        <h3>微信自动化管理</h3>
        <p>C++驱动的微信界面自动化，稳定可靠</p>
        <div class="module-stats">
          <span>激活实例: {{ moduleStats.wechat.activeInstances }}</span>
          <span>操作成功率: {{ moduleStats.wechat.successRate }}%</span>
        </div>
      </div>
      
      <div class="module-card" @click="$router.push('/ai-assistant')">
        <div class="module-icon">🤖</div>
        <h3>AI助手</h3>
        <p>智能意图识别与个性化回复生成</p>
        <div class="module-stats">
          <span>处理消息: {{ moduleStats.ai.processedMessages }}</span>
          <span>准确率: {{ moduleStats.ai.accuracy }}%</span>
        </div>
      </div>
      
      <div class="module-card" @click="$router.push('/customers')">
        <div class="module-icon">👤</div>
        <h3>客户与标签</h3>
        <p>客户画像管理与动态标签系统</p>
        <div class="module-stats">
          <span>客户总数: {{ moduleStats.customers.total }}</span>
          <span>已标签: {{ moduleStats.customers.tagged }}</span>
        </div>
      </div>
      
      <div class="module-card" @click="$router.push('/settings')">
        <div class="module-icon">🛠️</div>
        <h3>系统设置</h3>
        <p>引擎配置与AI模型管理</p>
        <div class="module-stats">
          <span>配置状态: 正常</span>
          <span>日志等级: {{ moduleStats.settings.logLevel }}</span>
        </div>
      </div>
    </div>
    
    <div class="quick-actions">
      <button @click="$router.push('/rpa-test')" class="btn btn-primary">RPA全局设置</button>
      <button @click="$router.push('/rpa-test')" class="btn btn-info">RPA功能测试</button>
      <button @click="refreshStats" class="btn btn-secondary">刷新状态</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const systemStats = ref({
  wechatConnected: true,
  runningSopTasks: 3,
  todayRetargeted: 42,
  aiReplyRate: 85,
  intentAccuracy: 92,
  convertedLeads: 18,
  cppDriverActive: true,
  ocrLoad: 45,
  memoryUsage: 128
})

const moduleStats = ref({
  retargeting: {
    activePlans: 5,
    todayRetargeted: 24
  },
  sop: {
    runningCount: 8,
    todayExecuted: 156
  },
  wechat: {
    activeInstances: 2,
    successRate: 98.5
  },
  ai: {
    processedMessages: 324,
    accuracy: 94.2
  },
  customers: {
    total: 1240,
    tagged: 892
  },
  settings: {
    logLevel: 'INFO'
  }
})

const refreshStats = () => {
  // 这里可以调用API更新统计数据
  console.log('刷新系统状态...')
}

onMounted(() => {
  // 页面加载时获取初始数据
  console.log('加载仪表盘数据...')
})
</script>

<style scoped>
.dashboard {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  background-color: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  border-left: 4px solid #007bff;
}

.stat-card h3 {
  margin-top: 0;
  color: #333;
  margin-bottom: 15px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #eee;
}

.stat-item:last-child {
  border-bottom: none;
}

.label {
  color: #666;
}

.value {
  font-weight: bold;
  color: #333;
}

.status {
  font-weight: bold;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.9em;
}

.status.active {
  background-color: #d4edda;
  color: #155724;
}

.status.inactive {
  background-color: #f8d7da;
  color: #721c24;
}

.modules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.module-card {
  background-color: white;
  border-radius: 8px;
  padding: 25px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  border: 1px solid #eee;
}

.module-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 5px 20px rgba(0,0,0,0.15);
}

.module-icon {
  font-size: 2.5em;
  margin-bottom: 15px;
}

.module-card h3 {
  margin: 0 0 10px 0;
  color: #333;
}

.module-card p {
  color: #666;
  margin-bottom: 15px;
  line-height: 1.5;
}

.module-stats {
  display: flex;
  justify-content: space-between;
  font-size: 0.9em;
  color: #888;
}

.quick-actions {
  display: flex;
  gap: 15px;
  justify-content: center;
  flex-wrap: wrap;
}

.btn {
  padding: 12px 24px;
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
</style>
