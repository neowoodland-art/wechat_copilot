import axios from 'axios'

// 创建 axios 实例
const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 10000
})

// 获取用户列表
export const fetchUsers = async () => {
  const response = await api.get('/v1/users')
  return response.data
}

// 获取用户详情
export const fetchUserDetail = async (userId) => {
  const response = await api.get(`/v1/users/${userId}`)
  return response.data
}

// 更新用户信息
export const updateUser = async (userId, data) => {
  const response = await api.put(`/v1/users/${userId}`, data)
  return response.data
}

// 处理微信消息
export const handleMessage = async (data) => {
  const response = await api.post('/v1/rpa/handle-message', data)
  return response.data
}

// 获取微信界面元素
export const fetchUIElements = async () => {
  const response = await api.get('/v1/rpa/ui-elements')
  return response.data
}

// 分析控件树
export const analyzeUITree = async () => {
  const response = await api.get('/v1/rpa/ui-tree-analysis')
  return response.data
}

export const captureATSPI = async (data = {}) => {
  const response = await api.post('/v1/atspi/capture', data)
  return response.data
}

export const listATSPI = async (params = {}) => {
  const response = await api.get('/v1/atspi/list', { params })
  return response.data
}

export const updateATSPI = async (data) => {
  const response = await api.post('/v1/atspi/update', data)
  return response.data
}

export const deleteATSPI = async (ids = []) => {
  const response = await api.post('/v1/atspi/delete', { ids })
  return response.data
}

export const clearATSPI = async (confirm = false) => {
  const response = await api.post('/v1/atspi/clear', { confirm })
  return response.data
}

export const exportATSPI = async (params = {}) => {
  const response = await api.get('/v1/atspi/export', { params })
  return response.data
}

export const fetchLLMSchema = async () => {
  const response = await api.get('/v1/llm/schema')
  return response.data
}

export const fetchLLMTools = async () => {
  const response = await api.get('/v1/llm/tools')
  return response.data
}

export const callLLMCore = async (data) => {
  const response = await api.post('/v1/llm/core', data)
  return response.data
}

export const fetchLLMLogs = async (params = {}) => {
  const response = await api.get('/v1/llm/logs', { params })
  return response.data
}

export const fetchCRMProfiles = async (params = {}) => {
  const response = await api.get('/v1/crm/profile/list', { params })
  return response.data
}

export const fetchCRMOverview = async (customerId) => {
  const response = await api.get('/v1/crm/profile/overview', { params: { customer_id: customerId } })
  return response.data
}

export const importCRMWechatHistory = async (data) => {
  const response = await api.post('/v1/crm/chat/import/wechat', data)
  return response.data
}

export const generateCRMSummary = async (data) => {
  const response = await api.post('/v1/crm/summary/generate', data)
  return response.data
}

export const generateCRMPortrait = async (data) => {
  const response = await api.post('/v1/crm/portrait/generate', data)
  return response.data
}

export const generateCRMTags = async (data) => {
  const response = await api.post('/v1/crm/tags/generate', data)
  return response.data
}

export const runCRMScheduleNow = async (data) => {
  const response = await api.post('/v1/crm/schedule/run-now', data)
  return response.data
}

export default api