<template>
  <div class="atspi-analysis">
    <h2>微信辅助树分析工具</h2>

    <section class="panel">
      <h3>采集</h3>
      <div class="row">
        <label>最大节点数
          <input v-model.number="captureForm.max_nodes" type="number" min="1" max="5000" />
        </label>
        <label>最大深度
          <input v-model.number="captureForm.max_depth" type="number" min="-1" max="64" />
        </label>
        <label>页面类型
          <input v-model="captureForm.page_type" placeholder="聊天界面/联系人/弹窗" />
        </label>
        <label>功能类型
          <input v-model="captureForm.function_type" placeholder="按钮/列表项/菜单" />
        </label>
        <label class="check-wrap">
          <input v-model="captureForm.auto_activate" type="checkbox" /> 自动激活微信
        </label>
        <label class="check-wrap">
          <input v-model="captureForm.auto_refresh_tree" type="checkbox" /> 抓取前刷新辅助树
        </label>
      </div>
      <div class="row">
        <label>刷新轮次
          <input v-model.number="captureForm.refresh_rounds" type="number" min="1" max="8" />
        </label>
        <label>轮次间隔(ms)
          <input v-model.number="captureForm.refresh_interval_ms" type="number" min="0" max="3000" />
        </label>
      </div>
      <div class="row">
        <button class="btn btn-primary" :disabled="loading" @click="handleCapture">采集并入库</button>
        <button class="btn btn-info" :disabled="loading" @click="loadList">刷新列表</button>
        <button class="btn btn-success" :disabled="loading" @click="handleExport">导出智能体结构化数据</button>
        <button class="btn btn-secondary" :disabled="loading" @click="handleExportAllRaw">导出无过滤全量树</button>
        <button class="btn btn-danger" :disabled="loading" @click="handleClearAll">一键清空库</button>
      </div>
      <p class="status" v-if="statusText">{{ statusText }}</p>
    </section>

    <section class="panel">
      <h3>筛选 / 排序</h3>
      <div class="row">
        <label>深度
          <input v-model.number="filters.depth" type="number" min="0" placeholder="全部" />
        </label>
        <label>深度编号
          <input v-model="filters.depth_code" placeholder="如 00/01/02" />
        </label>
        <label>路径编码前缀
          <input v-model="filters.path_code_prefix" placeholder="如 99|01" />
        </label>
        <label>路径关键词
          <input v-model="filters.path_keyword" placeholder="root/child" />
        </label>
        <label>页面类型
          <input v-model="filters.page_type" placeholder="聊天界面" />
        </label>
        <label>控件角色
          <input v-model="filters.role" placeholder="button/input" />
        </label>
      </div>
      <div class="row">
        <label>文字关键词
          <input v-model="filters.text_keyword" placeholder="控件文本" />
        </label>
        <label>OCR关键词
          <input v-model="filters.ocr_keyword" placeholder="OCR内容" />
        </label>
        <label>X范围
          <div class="range-inline">
            <input v-model.number="filters.x_min" type="number" placeholder="min" />
            <input v-model.number="filters.x_max" type="number" placeholder="max" />
          </div>
        </label>
        <label>Y范围
          <div class="range-inline">
            <input v-model.number="filters.y_min" type="number" placeholder="min" />
            <input v-model.number="filters.y_max" type="number" placeholder="max" />
          </div>
        </label>
      </div>
      <div class="row">
        <label>排序字段
          <select v-model="filters.sort_by">
            <option value="created_at">创建时间</option>
            <option value="depth">深度</option>
            <option value="index">同级序号</option>
            <option value="x">X</option>
            <option value="y">Y</option>
          </select>
        </label>
        <label>排序方式
          <select v-model="filters.sort_order">
            <option value="desc">降序</option>
            <option value="asc">升序</option>
          </select>
        </label>
        <button class="btn btn-primary" :disabled="loading" @click="applyFilters">应用筛选</button>
      </div>
      <div class="row non-empty-row">
        <span class="filter-subtitle">非空筛选</span>
        <div class="non-empty-group">
          <label class="check-wrap check-wrap-inline">
            <input v-model="filters.non_empty_access_path" type="checkbox" /> 路径不为空
          </label>
          <label class="check-wrap check-wrap-inline">
            <input v-model="filters.non_empty_path_numeric_code" type="checkbox" /> 路径编码不为空
          </label>
          <label class="check-wrap check-wrap-inline">
            <input v-model="filters.non_empty_depth_code" type="checkbox" /> 深度编号不为空
          </label>
          <label class="check-wrap check-wrap-inline">
            <input v-model="filters.non_empty_page_type" type="checkbox" /> 页面类型不为空
          </label>
          <label class="check-wrap check-wrap-inline">
            <input v-model="filters.non_empty_role" type="checkbox" /> 角色不为空
          </label>
          <label class="check-wrap check-wrap-inline">
            <input v-model="filters.non_empty_text" type="checkbox" /> 文本不为空
          </label>
          <label class="check-wrap check-wrap-inline">
            <input v-model="filters.non_empty_ocr_text" type="checkbox" /> OCR不为空
          </label>
        </div>
      </div>
    </section>

    <section class="panel">
      <h3>辅助树列表</h3>
      <div class="row">
        <button class="btn btn-success" :disabled="loading" @click="handleExportListCsv">导出列表表格（CSV）</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>编码</th>
              <th>角色（类型）</th>
              <th>深度</th>
              <th>坐标</th>
              <th>文字</th>
              <th>页面类型</th>
              <th>功能类型</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in rows" :key="item.id">
              <td>{{ item.id }}</td>
              <td>{{ item.depth_code }}|{{ item.path_numeric_code }}</td>
              <td>{{ item.role || '-' }}</td>
              <td>{{ item.depth }}/{{ item.index }}</td>
              <td>{{ item.x }},{{ item.y }} ({{ item.width }}x{{ item.height }})</td>
              <td>{{ item.text || item.ocr_text || item.name }}</td>
              <td>
                <input v-model="item.page_type" class="inline-input" />
              </td>
              <td>
                <input v-model="item.function_type" class="inline-input" />
              </td>
              <td>
                <button class="btn btn-sm btn-info" @click="openPreview(item)">预览</button>
                <button class="btn btn-sm btn-success" @click="saveTag(item)">保存标记</button>
                <button class="btn btn-sm btn-danger" @click="removeRow(item.id)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager">
        <button class="btn" :disabled="filters.page <= 1 || loading" @click="changePage(filters.page - 1)">上一页</button>
        <span>第 {{ filters.page }} 页 / 共 {{ totalPages }} 页（总 {{ total }} 条）</span>
        <button class="btn" :disabled="filters.page >= totalPages || loading" @click="changePage(filters.page + 1)">下一页</button>
      </div>
    </section>

    <div v-if="previewVisible" class="preview-mask" @click.self="previewVisible = false">
      <div class="preview-card">
        <h3>控件预览</h3>
        <div class="preview-grid">
          <div>
            <img v-if="selectedItem?.screenshot_url" :src="toAbsUrl(selectedItem.screenshot_url)" class="preview-img" alt="node" />
            <p>控件图</p>
          </div>
          <div>
            <img v-if="selectedItem?.full_image_url" :src="toAbsUrl(selectedItem.full_image_url)" class="preview-img" alt="full" />
            <p>全屏图（定位: {{ selectedItem?.x }}, {{ selectedItem?.y }}）</p>
          </div>
        </div>
        <pre>{{ selectedItem }}</pre>
        <button class="btn btn-primary" @click="previewVisible = false">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  captureATSPI,
  clearATSPI,
  clearATSPIForce,
  deleteATSPI,
  exportATSPI,
  listATSPI,
  updateATSPI
} from '../api'

const loading = ref(false)
const statusText = ref('')
const rows = ref([])
const total = ref(0)
const previewVisible = ref(false)
const selectedItem = ref(null)

const totalPages = computed(() => Math.max(1, Math.ceil((total.value || 0) / (filters.value.page_size || 1))))

const captureForm = ref({
  max_nodes: 1200,
  max_depth: -1,
  auto_activate: false,
  auto_refresh_tree: false,
  refresh_rounds: 1,
  refresh_interval_ms: 0,
  page_type: '',
  function_type: ''
})

const buildDefaultFilters = () => ({
  page: 1,
  page_size: 30,
  depth: null,
  depth_code: '',
  path_code_prefix: '',
  path_keyword: '',
  non_empty_access_path: false,
  non_empty_path_numeric_code: false,
  non_empty_depth_code: false,
  page_type: '',
  role: '',
  non_empty_page_type: false,
  non_empty_role: false,
  text_keyword: '',
  ocr_keyword: '',
  non_empty_text: false,
  non_empty_ocr_text: false,
  x_min: null,
  x_max: null,
  y_min: null,
  y_max: null,
  sort_by: 'created_at',
  sort_order: 'desc'
})

const filters = ref(buildDefaultFilters())

const resetFiltersForCapture = () => {
  const currentSortBy = filters.value.sort_by
  const currentSortOrder = filters.value.sort_order
  const currentPageSize = filters.value.page_size
  filters.value = {
    ...buildDefaultFilters(),
    sort_by: currentSortBy,
    sort_order: currentSortOrder,
    page_size: currentPageSize,
    page: 1
  }
}

const compactParams = () => {
  const source = { ...filters.value }
  const params = {}
  Object.keys(source).forEach((key) => {
    const val = source[key]
    if (val !== '' && val !== null && val !== undefined) {
      params[key] = val
    }
  })
  return params
}

const toAbsUrl = (url) => {
  if (!url) return ''
  if (url.startsWith('http')) return url
  return `http://localhost:8000${url}`
}

const loadList = async () => {
  loading.value = true
  try {
    const data = await listATSPI(compactParams())
    rows.value = data.items || []
    total.value = data.total || 0
    statusText.value = `已加载 ${rows.value.length} 条（总 ${total.value}）`
  } catch (error) {
    statusText.value = `加载失败: ${error?.response?.data?.detail || error.message}`
  } finally {
    loading.value = false
  }
}

const handleCapture = async () => {
  loading.value = true
  statusText.value = '开始采集 AT-SPI 树与截图...'
  try {
    const data = await captureATSPI(captureForm.value)
    resetFiltersForCapture()
    await loadList()
    const refresh = data?.tree_refresh || {}
    const refreshRounds = Number(refresh.refresh_rounds || 1)
    const bestNodes = Number(refresh.best_nodes || 0)
    const bestPositioned = Number(refresh.best_positioned_nodes || 0)
    statusText.value = `采集完成，共写入 ${data?.inserted || 0} 条控件；刷新${refreshRounds}轮，最优节点${bestNodes}（可定位${bestPositioned}）；当前列表 ${rows.value.length} 条（总 ${total.value}）`
  } catch (error) {
    statusText.value = `采集失败: ${error?.response?.data?.detail || error.message}`
  } finally {
    loading.value = false
  }
}

const applyFilters = async () => {
  filters.value.page = 1
  await loadList()
}

const changePage = async (page) => {
  filters.value.page = page
  await loadList()
}

const saveTag = async (item) => {
  try {
    await updateATSPI({
      id: item.id,
      page_type: item.page_type,
      function_type: item.function_type
    })
    statusText.value = `ID ${item.id} 标记已保存`
  } catch (error) {
    statusText.value = `保存失败: ${error?.response?.data?.detail || error.message}`
  }
}

const removeRow = async (id) => {
  if (!confirm(`确认删除记录 ${id} ?`)) return
  try {
    await deleteATSPI([id])
    statusText.value = `已删除记录 ${id}`
    await loadList()
  } catch (error) {
    statusText.value = `删除失败: ${error?.response?.data?.detail || error.message}`
  }
}

const handleExport = async () => {
  try {
    const data = await exportATSPI({
      page_type: filters.value.page_type || undefined,
      role: filters.value.role || undefined,
      depth: filters.value.depth ?? undefined,
      depth_code: filters.value.depth_code || undefined,
      path_code_prefix: filters.value.path_code_prefix || undefined
    })
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json;charset=utf-8' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `wechat_atspi_export_${Date.now()}.json`
    link.click()
    URL.revokeObjectURL(link.href)
    statusText.value = `导出成功，共 ${data.count || 0} 条` 
  } catch (error) {
    statusText.value = `导出失败: ${error?.response?.data?.detail || error.message}`
  }
}

const handleExportAllRaw = async () => {
  try {
    const data = await exportATSPI({ no_filter: true })
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json;charset=utf-8' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `wechat_atspi_export_all_${Date.now()}.json`
    link.click()
    URL.revokeObjectURL(link.href)
    statusText.value = `全量导出成功，共 ${data.count || 0} 条`
  } catch (error) {
    statusText.value = `全量导出失败: ${error?.response?.data?.detail || error.message}`
  }
}

const handleClearAll = async () => {
  if (!confirm('确认一次性清空辅助树入库数据？此操作不可恢复。')) return
  loading.value = true
  statusText.value = '正在清空辅助树入库数据，请稍候...'
  try {
    let data
    try {
      data = await clearATSPI(true)
    } catch (primaryError) {
      data = await clearATSPIForce()
      statusText.value = `常规清空失败，已自动切换强制清空: ${primaryError?.response?.data?.detail || primaryError.message}`
    }
    let verify = await listATSPI({ page: 1, page_size: 1 })
    if ((verify?.total || 0) > 0) {
      data = await clearATSPIForce()
      verify = await listATSPI({ page: 1, page_size: 1 })
    }
    const deleted = data?.deleted || 0
    const remaining = verify?.total ?? data?.remaining ?? 0
    filters.value.page = 1
    await loadList()
    statusText.value = `清空完成，已清空 ${deleted} 条记录，剩余 ${remaining} 条`
  } catch (error) {
    statusText.value = `清空失败: ${error?.response?.data?.detail || error.message}`
  } finally {
    loading.value = false
  }
}

const csvEscape = (value) => {
  if (value === null || value === undefined) return ''
  const text = String(value).replace(/"/g, '""')
  return /[",\n]/.test(text) ? `"${text}"` : text
}

const handleExportListCsv = async () => {
  loading.value = true
  statusText.value = '正在导出辅助树列表表格...'
  try {
    const baseParams = compactParams()
    const pageSize = 500
    const allItems = []
    let page = 1

    while (true) {
      const data = await listATSPI({ ...baseParams, page, page_size: pageSize })
      const batch = data.items || []
      const totalCount = Number(data.total || 0)
      allItems.push(...batch)

      if (!batch.length || allItems.length >= totalCount) break
      page += 1
    }

    const headers = ['ID', '深度编号', '路径编码', '角色', '深度', '同级序号', 'X', 'Y', '宽', '高', '文字', 'OCR文本', '页面类型', '功能类型', '访问路径', '创建时间']
    const lines = [headers.map(csvEscape).join(',')]
    allItems.forEach((item) => {
      lines.push(
        [
          item.id,
          item.depth_code,
          item.path_numeric_code,
          item.role,
          item.depth,
          item.index,
          item.x,
          item.y,
          item.width,
          item.height,
          item.text || item.name || '',
          item.ocr_text,
          item.page_type,
          item.function_type,
          item.access_path,
          item.created_at
        ].map(csvEscape).join(',')
      )
    })

    const blob = new Blob(['\uFEFF' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `wechat_atspi_list_${Date.now()}.csv`
    link.click()
    URL.revokeObjectURL(link.href)
    statusText.value = `列表表格导出成功，共 ${allItems.length} 条`
  } catch (error) {
    statusText.value = `列表表格导出失败: ${error?.response?.data?.detail || error.message}`
  } finally {
    loading.value = false
  }
}

const openPreview = (item) => {
  selectedItem.value = item
  previewVisible.value = true
}

onMounted(async () => {
  await loadList()
})
</script>

<style scoped>
.atspi-analysis {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.panel {
  background: #fafafa;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 10px;
  align-items: center;
}

label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 160px;
}

.check-wrap {
  min-width: auto;
  flex-direction: row;
  align-items: center;
  gap: 6px;
  margin-top: 20px;
}

.check-wrap-inline {
  margin-top: 0;
}

.non-empty-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.non-empty-row {
  align-items: center;
}

.filter-subtitle {
  font-size: 13px;
  color: #444;
  margin-right: 4px;
}

input,
select {
  padding: 6px 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.range-inline {
  display: flex;
  gap: 6px;
}

.table-wrap {
  width: 100%;
  overflow: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

th,
td {
  border: 1px solid #eee;
  padding: 8px;
  vertical-align: top;
}

.path-cell {
  min-width: 280px;
}

.thumb {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border: 1px solid #ddd;
  cursor: pointer;
}

.inline-input {
  min-width: 110px;
}

.pager {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}

.preview-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}

.preview-card {
  background: #fff;
  width: 90vw;
  max-width: 1200px;
  max-height: 90vh;
  overflow: auto;
  border-radius: 8px;
  padding: 16px;
}

.preview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.preview-img {
  max-width: 100%;
  border: 1px solid #ddd;
}

.status {
  color: #333;
  margin-top: 8px;
}

.btn {
  padding: 7px 14px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-sm {
  padding: 4px 8px;
  margin-right: 6px;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-info {
  background: #17a2b8;
  color: white;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-success {
  background: #28a745;
  color: white;
}

.btn-danger {
  background: #dc3545;
  color: white;
}
</style>
