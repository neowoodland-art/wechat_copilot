import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Dashboard from './views/Dashboard.vue'
import UserList from './views/UserList.vue'
import UserDetail from './views/UserDetail.vue'
import RPATest from './views/RPATest.vue'
import CustomerRetargeting from './views/CustomerRetargeting.vue'
import SOPManagement from './views/SOPManagement.vue'
import SOPEditor from './views/SOPEditor.vue'
import AIAssistant from './views/AIAssistant.vue'
import WeChatAutomation from './views/WeChatAutomation.vue'
import Customers from './views/Customers.vue'
import Settings from './views/Settings.vue'
import ATSPIAnalysis from './views/ATSPIAnalysis.vue'
import LLMCoreDebug from './views/LLMCoreDebug.vue'

// 创建路由
const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Dashboard',
      component: Dashboard
    },
    {
      path: '/user/:id',
      name: 'UserDetail',
      component: UserDetail
    },
    {
      path: '/rpa-test',
      name: 'RPATest',
      component: RPATest
    },
    {
      path: '/customer-retargeting',
      name: 'CustomerRetargeting',
      component: CustomerRetargeting
    },
    {
      path: '/sop-management',
      name: 'SOPManagement',
      component: SOPManagement
    },
    {
      path: '/sop-editor',
      name: 'SOPEditor',
      component: SOPEditor
    },
    {
      path: '/ai-assistant',
      name: 'AIAssistant',
      component: AIAssistant
    },
    {
      path: '/wechat-automation',
      name: 'WeChatAutomation',
      component: WeChatAutomation
    },
    {
      path: '/customers',
      name: 'Customers',
      component: Customers
    },
    {
      path: '/settings',
      name: 'Settings',
      component: Settings
    },
    {
      path: '/atspi-analysis',
      name: 'ATSPIAnalysis',
      component: ATSPIAnalysis
    },
    {
      path: '/llm-core-debug',
      name: 'LLMCoreDebug',
      component: LLMCoreDebug
    }
  ]
})

// 创建应用
const app = createApp(App)
app.use(router)
app.mount('#app')