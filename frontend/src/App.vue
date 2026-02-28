<template>
  <div class="app">
    <header class="header">
      <h1>WeChat Copilot</h1>
      <nav>
        <router-link to="/">仪表盘</router-link>
        <router-link to="/customer-retargeting">智能回访</router-link>
        <router-link to="/sop-management">SOP管理</router-link>
        <router-link to="/sop-editor">SOP编辑器</router-link>
        <router-link to="/ai-assistant">AI助手</router-link>
        <router-link to="/wechat-automation">微信自动化</router-link>
        <router-link to="/wechat-operation-packages">微信操作打包</router-link>
        <router-link to="/customers">客户管理</router-link>
        <router-link to="/settings">系统设置</router-link>
        <router-link to="/rpa-test">RPA全局设置</router-link>
        <router-link to="/atspi-analysis">辅助树分析</router-link>
        <router-link to="/llm-core-debug">LLM统一调试</router-link>
      </nav>
    </header>
    <main class="main">
      <router-view />
    </main>
    <footer class="footer">
      <p>© 2026 WeChat Copilot - 智能微信自动化系统</p>
    </footer>
  </div>
</template>

<style scoped>
.app {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid #eaeaea;
}

.header h1 {
  color: #333;
  margin: 0;
}

nav a {
  margin-left: 20px;
  text-decoration: none;
  color: #666;
}

nav a:hover {
  color: #007bff;
}

.main {
  min-height: 600px;
}

.footer {
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #eaeaea;
  text-align: center;
  color: #999;
}
</style>