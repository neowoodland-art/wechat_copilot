<!-- /home/neogh/wechat_copilot/frontend/src/views/SOPEditor.vue -->
<template>
  <div class="sop-editor-page">
    <h2>SOP可视化编辑器</h2>
    <SOPVisualEditor />
  </div>
</template>

<script setup>
import SOPVisualEditor from '@/components/SOPVisualEditor.vue'
</script>

<style scoped>
.sop-editor-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}
</style>
