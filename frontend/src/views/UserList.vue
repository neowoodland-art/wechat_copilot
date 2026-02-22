<template>
  <div>
    <h2>客户列表</h2>
    <input v-model="searchTag" placeholder="按标签筛选" class="search-input" />
    <table class="user-table">
      <thead>
        <tr>
          <th>昵称</th>
          <th>微信ID</th>
          <th>标签</th>
          <th>最后联系</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="user in filteredUsers" :key="user.id">
          <td>{{ user.nickname }}</td>
          <td>{{ user.wechat_id }}</td>
          <td>
            <span v-for="(tag, index) in getTags(user)" :key="index" class="tag">
              {{ tag }}
            </span>
            <span v-if="getTags(user).length === 0" class="no-tags">无</span>
          </td>
          <td>{{ formatDate(user.last_contact) }}</td>
          <td>
            <router-link :to="`/user/${user.id}`" class="btn">查看</router-link>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-if="users.length === 0" class="empty">
      暂无用户数据
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const users = ref([])
const searchTag = ref('')

// 获取用户列表
const fetchUsers = async () => {
  try {
    const response = await axios.get('/api/v1/users')
    users.value = response.data
  } catch (error) {
    console.error('获取用户列表失败:', error)
  }
}

// 格式化日期
const formatDate = (dateString) => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

// 按标签筛选用户
const filteredUsers = computed(() => {
  if (!searchTag.value) return users.value
  return users.value.filter(u => 
    getTags(u).includes(searchTag.value)
  )
})

// 组件挂载时获取用户列表
onMounted(() => {
  fetchUsers()
})

// 获取用户标签数组
const getTags = (user) => {
  try {
    return user.tags ? JSON.parse(user.tags) : []
  } catch {
    return []
  }
}
</script>

<style scoped>
.search-input {
  width: 300px;
  padding: 10px;
  margin-bottom: 20px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.user-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}

.user-table th,
.user-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #eaeaea;
}

.user-table th {
  background-color: #f5f5f5;
  font-weight: 600;
}

.tag {
  display: inline-block;
  background-color: #e3f2fd;
  color: #1976d2;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  margin-right: 6px;
  margin-bottom: 6px;
}

.no-tags {
  color: #999;
  font-style: italic;
}

.btn {
  display: inline-block;
  padding: 6px 12px;
  background-color: #007bff;
  color: white;
  text-decoration: none;
  border-radius: 4px;
  font-size: 14px;
}

.btn:hover {
  background-color: #0069d9;
}

.empty {
  text-align: center;
  padding: 50px;
  color: #999;
  font-size: 16px;
}
</style>