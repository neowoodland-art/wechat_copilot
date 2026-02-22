<template>
  <div>
    <h2>客户详情</h2>
    <div v-if="user" class="user-detail">
      <div class="form-group">
        <label>昵称</label>
        <input v-model="editForm.nickname" class="form-control" />
      </div>
      <div class="form-group">
        <label>微信ID</label>
        <input v-model="editForm.wechat_id" class="form-control" disabled />
      </div>
      <div class="form-group">
        <label>标签</label>
        <div class="tag-input">
          <input v-model="newTag" placeholder="添加标签" class="form-control" @keyup.enter="addTag" />
          <button @click="addTag" class="btn btn-sm">添加</button>
        </div>
        <div class="tags-container">
          <span v-for="(tag, index) in editForm.tags" :key="index" class="tag">
            {{ tag }}
            <button @click="removeTag(index)" class="tag-remove">×</button>
          </span>
        </div>
      </div>
      <div class="form-group">
        <label>总结</label>
        <textarea v-model="editForm.summary" class="form-control" rows="4"></textarea>
      </div>
      <div class="form-group">
        <label>最后联系</label>
        <input :value="formatDate(user.last_contact)" class="form-control" disabled />
      </div>
      <div class="action-buttons">
        <button @click="saveChanges" class="btn btn-primary">保存修改</button>
        <router-link to="/" class="btn btn-secondary">返回列表</router-link>
      </div>
    </div>
    <div v-else class="loading">
      加载中...
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const user = ref(null)
const editForm = ref({
  nickname: '',
  wechat_id: '',
  tags: [],
  summary: ''
})
const newTag = ref('')

// 获取用户详情
const fetchUserDetail = async () => {
  try {
    const response = await axios.get(`/api/v1/users/${route.params.id}`)
    user.value = response.data
    // 初始化编辑表单
    editForm.value = {
      nickname: user.value.nickname,
      wechat_id: user.value.wechat_id,
      tags: user.value.tags ? JSON.parse(user.value.tags) : [],
      summary: user.value.summary
    }
  } catch (error) {
    console.error('获取用户详情失败:', error)
  }
}

// 保存修改
const saveChanges = async () => {
  try {
    await axios.put(`/api/v1/users/${route.params.id}`, {
      nickname: editForm.value.nickname,
      tags: editForm.value.tags,
      summary: editForm.value.summary
    })
    // 重新获取用户信息
    await fetchUserDetail()
    alert('保存成功！')
  } catch (error) {
    console.error('保存失败:', error)
    alert('保存失败，请重试')
  }
}

// 添加标签
const addTag = () => {
  if (newTag.value && !editForm.value.tags.includes(newTag.value)) {
    editForm.value.tags.push(newTag.value)
    newTag.value = ''
  }
}

// 移除标签
const removeTag = (index) => {
  editForm.value.tags.splice(index, 1)
}

// 格式化日期
const formatDate = (dateString) => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

// 组件挂载时获取用户详情
onMounted(() => {
  fetchUserDetail()
})
</script>

<style scoped>
.user-detail {
  max-width: 600px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #333;
}

.form-control {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.tag-input {
  display: flex;
  margin-bottom: 10px;
}

.tag-input .form-control {
  flex: 1;
  margin-right: 10px;
}

.tags-container {
  margin-top: 10px;
}

.tag {
  display: inline-block;
  background-color: #e3f2fd;
  color: #1976d2;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 14px;
  margin-right: 10px;
  margin-bottom: 10px;
  position: relative;
}

.tag-remove {
  background: none;
  border: none;
  color: #1976d2;
  font-size: 16px;
  cursor: pointer;
  margin-left: 8px;
  padding: 0;
  width: 20px;
  height: 20px;
  line-height: 20px;
  text-align: center;
  border-radius: 50%;
}

.tag-remove:hover {
  background-color: rgba(25, 118, 210, 0.1);
}

.action-buttons {
  margin-top: 30px;
}

.btn {
  display: inline-block;
  padding: 10px 20px;
  text-decoration: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  margin-right: 10px;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

.btn-primary {
  background-color: #007bff;
  color: white;
  border: none;
}

.btn-primary:hover {
  background-color: #0069d9;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
  border: none;
}

.btn-secondary:hover {
  background-color: #5a6268;
}

.loading {
  text-align: center;
  padding: 50px;
  color: #999;
  font-size: 16px;
}
</style>