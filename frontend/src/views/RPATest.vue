<template>
  <div class="rpa-test">
    <h1>RPA功能测试面板</h1>

    <div class="card test-section status-overview-card">
      <div class="card-header">
        <h3>系统状态（同步系统布局设置）</h3>
      </div>
      <div class="card-body">
        <div class="status-display">
          <div class="status-item">
            <span class="status-label">微信进程状态:</span>
            <span :class="['status-value', { 'status-active': systemStatus.isRunning }]">
              {{ systemStatus.isRunning ? '运行中' : '未运行' }}
            </span>
          </div>
          <div class="status-item">
            <span class="status-label">微信版本:</span>
            <span class="status-value">{{ systemStatus.version || '未知' }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">连接状态:</span>
            <span :class="['status-value', { 'status-active': systemStatus.isConnected }]">
              {{ systemStatus.isConnected ? '已连接' : '未连接' }}
            </span>
          </div>
          <button class="btn btn-secondary" @click="refreshSystemStatus">刷新系统状态</button>
        </div>
      </div>
    </div>

    <div class="panel-tabs">
      <button class="tab-btn" :class="{ active: activeGroup === 'basic' }" @click="activeGroup = 'basic'">1.基础控制</button>
      <button class="tab-btn" :class="{ active: activeGroup === 'template' }" @click="activeGroup = 'template'">2.设置区域</button>
      <button class="tab-btn" :class="{ active: activeGroup === 'atspi' }" @click="activeGroup = 'atspi'">3.界面ATSPI定位</button>
      <button class="tab-btn" :class="{ active: activeGroup === 'layout' }" @click="activeGroup = 'layout'">4.界面鼠标定位</button>
      <button class="tab-btn" :class="{ active: activeGroup === 'preview' }" @click="activeGroup = 'preview'">5.整合定位预览</button>
      <button class="tab-btn" :class="{ active: activeGroup === 'atomicControls' }" @click="activeGroup = 'atomicControls'">6.生成原子控件</button>
      <button class="tab-btn" :class="{ active: activeGroup === 'atomicContainerSettings' }" @click="activeGroup = 'atomicContainerSettings'">7.原子容器设置管理</button>
    </div>

    <div class="card test-section" v-if="activeGroup === 'basic'">
      <div class="card-header">
        <h3>基础控制（激活 / 状态 / 窗口 / 布局 / 微信启动 / 拟人化）</h3>
      </div>

      <div class="card-body" :class="{ 'section-readonly': setupLocked }">
        <div class="lock-tip" v-if="setupLocked">第一轮设置已确认锁定：当前区域仅查看，不可修改。</div>
        <div class="row">
          <div class="col-md-6">
            <div class="action-grid">
              <button class="btn btn-primary" @click="activateWeChat">激活微信</button>
              <button class="btn btn-secondary" @click="checkWeChatStatus">检查微信状态</button>
              <button class="btn btn-info" @click="getWindowInfo">获取窗口信息</button>
            </div>
            <div class="form-group">
              <label>窗口尺寸:</label>
              <div class="input-row">
                <input v-model="windowSize.width" type="number" placeholder="宽度">
                <input v-model="windowSize.height" type="number" placeholder="高度">
              </div>
            </div>
            <div class="form-group">
              <label>窗口位置:</label>
              <div class="input-row">
                <input v-model="windowPosition.x" type="number" placeholder="X坐标">
                <input v-model="windowPosition.y" type="number" placeholder="Y坐标">
              </div>
            </div>
            <button class="btn btn-warning" @click="setWindowSizeAndPosition">设置窗口大小和位置</button>
            <button class="btn btn-secondary" @click="saveWeChatWindowPreset" style="margin-left: 8px;">保存为激活预设</button>

            <div class="form-group" style="margin-top:12px;">
              <label>拟人化输入文本:</label>
              <input v-model="inputText" type="text" placeholder="要输入的文本">
              <div class="action-grid">
                <button class="btn btn-primary" @click="humanizedClick">拟人化点击</button>
                <button class="btn btn-success" @click="humanizedInput">拟人化输入</button>
              </div>
            </div>

            <div class="form-group" style="margin-top: 12px;">
              <label>微信脚本路径（微信管理-微信启动）:</label>
              <input v-model="wechatScriptPath" type="text" placeholder="/path/to/wechat/script.sh" class="form-control" />
              <div class="action-grid">
                <button class="btn btn-success" @click="launchWeChat" :disabled="isWeChatLaunching">
                  {{ isWeChatLaunching ? '启动中...' : '启动微信' }}
                </button>
                <button class="btn btn-info" @click="activateWeChat">激活微信</button>
                <button class="btn btn-secondary" @click="checkWeChatStatus">检查微信状态</button>
              </div>
            </div>

            <div class="form-group" style="margin-top: 12px;">
              <label>布局模式（原布局控制）:</label>
              <select v-model="selectedLayout" class="form-control">
                <option value="half-half">平铺布局（1/2 + 1/2）</option>
                <option value="one-third-two-thirds">前端1/3，微信2/3</option>
                <option value="custom">自定义</option>
              </select>
            </div>
            <div class="form-group" v-if="selectedLayout === 'custom'">
              <label>前端宽度百分比:</label>
              <input v-model.number="customFrontendWidth" type="number" min="10" max="90" />
            </div>
            <div class="action-grid">
              <button class="btn btn-primary" @click="applyLayout">应用布局</button>
              <button class="btn btn-success" @click="runHalfHalfRecognitionPipeline" :disabled="isPipelineRunning">
                {{ isPipelineRunning ? '执行中...' : '半屏布局并识别微信界面' }}
              </button>
            </div>

            <div class="form-group" style="margin-top: 12px;">
              <label>浏览器窗口控制目标:</label>
              <select v-model="windowTarget" class="form-control">
                <option value="active">当前活动窗口</option>
                <option value="browser">浏览器窗口</option>
                <option value="wechat">微信窗口</option>
              </select>
            </div>
            <div class="input-row" style="margin-bottom: 10px;">
              <input v-model.number="browserWindow.width" type="number" placeholder="宽度" />
              <input v-model.number="browserWindow.height" type="number" placeholder="高度" />
              <input v-model.number="browserWindow.x" type="number" placeholder="X" />
              <input v-model.number="browserWindow.y" type="number" placeholder="Y" />
            </div>
            <div class="action-grid">
              <button class="btn btn-secondary" @click="setBrowserWindowSize">设置窗口大小</button>
              <button class="btn btn-info" @click="maximizeBrowserWindow">最大化窗口</button>
              <button class="btn btn-warning" @click="syncBrowserWindowInfo">获取窗口信息</button>
            </div>
          </div>
          <div class="col-md-6">
            <div class="status-info">
              <p><strong>微信状态:</strong> {{ wechatStatus }}</p>
              <p><strong>窗口信息:</strong> {{ windowInfo }}</p>
              <p><strong>流程状态:</strong> {{ pipelineStatus || '未执行' }}</p>
              <p><strong>扫描配置:</strong> {{ scanProfilesSummary }}</p>
            </div>
            <div class="result-box" style="margin-top:10px;">
              <h4>拟人化结果:</h4>
              <pre>{{ humanizedResult }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="card test-section" v-if="activeGroup === 'atomicControls'">
      <div class="card-header">
        <h3>生成原子控件（供微信操作打包调用）</h3>
      </div>
      <div class="card-body">
        <div class="status-info" style="margin-bottom:10px;">
          <p><strong>说明:</strong> 当前页基于前面1-5完成后的校准控件，定义最小原子控件并保存到标准控件库。</p>
          <p><strong>用途:</strong> 后续在“微信操作打包”里直接拖拽调用这些标准控件即可编排流程。</p>
          <div class="action-grid" style="margin-top:8px;">
            <button class="btn btn-secondary" @click="activateWeChat">激活微信</button>
            <button class="btn btn-secondary" @click="getWindowInfo">列新窗口信息</button>
            <button class="btn btn-secondary" @click="refreshAtomicPositioning">刷新辅助树与定位</button>
          </div>
        </div>

        <div class="result-box" style="margin-bottom:10px;">
          <h4>来自第7步的配置文件（全局查询定义）</h4>
          <div class="action-grid" style="margin-top:8px;">
            <button class="btn btn-secondary" @click="loadAtomicPipelineConfig(false)">读取配置文件</button>
            <button class="btn btn-primary" @click="applyAtomicPipelineConfigToGenerator(false)">应用到当前生成器</button>
            <button
              class="btn btn-success"
              :disabled="!atomicPipelineCanAutoGenerate"
              @click="applyAtomicPipelineConfigToGenerator(true)"
            >按配置直接生成控件</button>
          </div>
          <pre v-if="atomicPipelineConfigSummary" style="margin-top:8px;">{{ atomicPipelineConfigSummary }}</pre>
          <p v-else style="margin-top:8px;color:#555;">尚未读取到配置文件，可先到第7步点击“保存并带入第6步”。</p>
          <p v-if="atomicPipelineConfig && !atomicPipelineCanAutoGenerate" style="margin-top:8px;color:#b91c1c;">
            当前配置的 query_count={{ Number(atomicPipelineConfig?.query_count || 0) }}，不是唯一控件（必须=1），已禁止直接生成。
          </p>
        </div>

        <div class="row">
          <div class="col-md-6">
            <div class="form-group">
              <label>profile_id（必填）:</label>
              <input v-model.number="atomicProfileId" @wheel.prevent type="number" min="1" placeholder="控件库所属profile_id">
              <div class="status-info" style="margin-top:6px;">
                当前列表 profile_id: {{ Number(atomicProfileId || 0) || '-' }}
                <span v-if="atomicLibraryLastLoadedAt"> | 最近加载: {{ atomicLibraryLastLoadedAt }}</span>
              </div>
            </div>

            <div class="form-group" style="margin-top:12px;">
              <label>选择已校准控件:</label>
              <select v-model="atomicSelectedRegionId" class="form-control" @change="syncAtomicFromCalibratedControl">
                <option value="">请选择控件</option>
                <option v-for="item in availableCalibratedControlsForAtomic" :key="item.region_id" :value="item.region_id">
                  {{ item.region_id }} | {{ item.name }} | {{ item.control_type }}
                </option>
              </select>
              <div class="status-info" style="margin-top:6px;">
                可选定位: {{ availableCalibratedControlsForAtomic.length }} / {{ calibratedControls.length }}
              </div>
            </div>

            <div class="form-group" style="margin-top:12px;">
              <label>control_uid（自动编号）:</label>
              <input v-model="atomicControlUid" type="text" readonly placeholder="自动生成，如 atspi_0001">
            </div>

            <div class="form-group" style="margin-top:12px;">
              <label>控件名称:</label>
              <input v-model="atomicControlName" type="text" placeholder="如 第一联系人 / 消息输入 / 发送按钮">
            </div>

            <div class="input-row" style="margin-top:8px;">
              <input v-model="atomicRegionKey" type="text" placeholder="region_key，如 contact_list/chat_input/main_menu">
              <input v-model="atomicControlType" type="text" placeholder="control_type，如 list_item/input/button">
            </div>

            <div class="input-row" style="margin-top:8px;">
              <input v-model="atomicPrimaryAction" type="text" placeholder="主动作，如 click/input_text">
              <input v-model="atomicNextAction" type="text" placeholder="后续动作，如 focus_input/send_message">
            </div>

            <div class="input-row" style="margin-top:8px;">
              <label style="display:flex;align-items:center;gap:6px;min-width:240px;">
                <input type="checkbox" v-model="atomicRequiresPreUseRescan" /> 使用前更新坐标（预重扫）
              </label>
              <label style="display:flex;align-items:center;gap:6px;min-width:220px;">
                <input type="checkbox" v-model="atomicHasPostClickChange" /> 点击后界面可能变化
              </label>
            </div>

            <div class="action-grid" style="margin-top:12px;">
              <button class="btn btn-secondary" @click="syncAtomicFromCalibratedControl">从已校准控件同步</button>
              <button class="btn btn-primary" @click="saveAtomicControlDefinition">保存为标准控件</button>
              <button class="btn btn-info" @click="generateAtomicControlsFromDiscovery('chat')">从聊天原子容器生成控件</button>
              <button class="btn btn-info" @click="generateAtomicControlsFromDiscovery('popup')">从弹窗原子容器生成控件</button>
              <button class="btn btn-warning" @click="generateAtomicControlsFromDiscovery('query')">从高级查询生成控件</button>
              <button class="btn btn-secondary" @click="resetAtomicEditor">清空编辑</button>
            </div>
          </div>

          <div class="col-md-6">
            <div class="result-box">
              <h4>标准控件预览（将写入微信操作打包可用控件）</h4>
              <pre>{{ formatJson(buildAtomicControlPayload()) }}</pre>
            </div>

            <div class="result-box" style="margin-top:12px;" v-if="atomicSaveResult">
              <h4>保存结果</h4>
              <pre>{{ atomicSaveResult }}</pre>
            </div>

            <div class="result-box" style="margin-top:12px;">
              <h4>原子控件导入导出（JSON备份）</h4>
              <div class="action-grid" style="margin-bottom:8px;">
                <button class="btn btn-secondary" @click="loadAtomicControlLibrary">加载已生成控件</button>
                <button class="btn btn-secondary" @click="exportAtomicControls">导出控件JSON</button>
                <button class="btn btn-primary" @click="importAtomicControls">导入控件JSON</button>
              </div>
              <textarea v-model="atomicImportExportText" rows="8" placeholder="这里显示导出的JSON，或粘贴要导入的JSON"></textarea>
            </div>
          </div>
        </div>

        <div class="result-box" style="margin-top:12px;">
          <h4>已生成原子控件列表（{{ atomicLibraryItems.length }}）</h4>
          <div class="action-grid" style="margin-bottom:8px;">
            <button class="btn btn-secondary" @click="loadAtomicControlLibrary">刷新列表</button>
            <button class="btn btn-danger" @click="clearAtomicControlsByProfile">清空当前profile控件</button>
            <button class="btn btn-warning" @click="loadAtomicControlReferences">查看引用关系</button>
          </div>
          <div v-if="atomicLibraryItems.length === 0" class="status-info">暂无控件，先保存一个标准控件。</div>
          <div v-for="item in atomicLibraryItems" :key="item.id" class="element-item">
            <p><strong>{{ item.control_uid }}</strong> | {{ item.control_type || '-' }} | {{ item.region_key || '-' }}</p>
            <p>
              bounds: ({{ item.bounds?.x || 0 }}, {{ item.bounds?.y || 0 }}, {{ item.bounds?.width || 0 }}x{{ item.bounds?.height || 0 }})
              | actions: {{ (item.actions || []).join(', ') || '-' }}
            </p>
            <div class="action-grid" style="margin-top:6px;">
              <button class="btn btn-sm btn-info" @click="editAtomicControlFromLibrary(item)">编辑</button>
              <button class="btn btn-sm btn-danger" @click="deleteAtomicControl(item)">删除</button>
            </div>
          </div>
        </div>

        <div class="result-box" style="margin-top:12px;" v-if="atomicReferencesResultText">
          <h4>当前profile控件引用关系</h4>
          <pre>{{ atomicReferencesResultText }}</pre>
        </div>

      </div>
    </div>

    <div class="card test-section" v-if="activeGroup === 'atspi'">
      <div class="card-header">
        <h3>界面ATSPI定位（全树/分层 + 点击位移校验）</h3>
      </div>
      <div class="card-body" :class="{ 'section-readonly': setupLocked }">
        <div class="lock-tip" v-if="setupLocked">第一轮设置已确认锁定：当前区域仅查看，不可修改。</div>
        <div class="form-group">
          <label>控件名称:</label>
          <input v-model="controlName" type="text" placeholder="控件名称">
          <div class="action-grid">
            <button class="btn btn-primary" @click="clickControl">点击控件</button>
            <button class="btn btn-success" @click="inputTextToControl">输入文本</button>
            <button class="btn btn-info" @click="getTextFromControl">获取文本</button>
          </div>
        </div>

        <div class="result-box">
          <h4>AT-SPI结果:</h4>
          <pre>{{ atspiResult }}</pre>
        </div>

        <div class="form-group mt-2">
          <label>树过滤条件:</label>
          <div class="input-row">
            <input v-model="atspiRoleFilter" type="text" placeholder="角色过滤，如 button">
            <input v-model="atspiNameFilter" type="text" placeholder="名称/文本过滤，如 发送">
          </div>
          <div class="input-row" style="margin-top:8px;">
            <input v-model.number="atspiMaxNodes" type="number" placeholder="max_nodes" />
            <input
              v-model.number="atspiMaxDepth"
              type="number"
              min="-1"
              placeholder="深度过滤 max_depth（-1=不限）"
            />
          </div>
          <div class="input-row" style="margin-top:8px; align-items:center; gap:12px;">
            <label style="display:flex; align-items:center; gap:6px; min-width:210px;">
              <input type="checkbox" v-model="atspiAutoRefreshTree" /> 抓取前刷新辅助树
            </label>
            <input v-model.number="atspiRefreshRounds" type="number" min="1" max="8" placeholder="刷新轮次(1-8)" />
            <input v-model.number="atspiRefreshIntervalMs" type="number" min="0" max="3000" placeholder="轮次间隔ms(0-3000)" />
          </div>
          <div class="action-grid">
            <button class="btn btn-secondary" @click="fetchATSPIControlTreeSnapshot(false, false)">获取AT-SPI原始快照（无过滤）</button>
            <button class="btn btn-warning" @click="fetchATSPIControlTreeSnapshot(true, false)">激活微信并抓原始快照</button>
            <button class="btn btn-info" @click="fetchATSPIControlTreeSnapshot(false, true)">按过滤条件抓快照</button>
          </div>
        </div>

        <div class="result-box" v-if="atspiSnapshotSummary">
          <h4>AT-SPI快照摘要:</h4>
          <pre>{{ atspiSnapshotSummary }}</pre>
        </div>

        <div class="form-group">
          <label>
            <input type="checkbox" v-model="atspiOnlyActionable" style="margin-right:6px;" />
            全树列表仅显示可操作节点（有尺寸 + 可交互角色）
          </label>
          <label style="display:block; margin-top:6px;">
            <input type="checkbox" v-model="atspiOnlyPositioned" style="margin-right:6px;" />
            全树列表仅显示有位置信息节点（宽高>0）
          </label>
          <div class="input-row" style="margin-top:8px;">
            <input v-model="atspiSearchText" type="text" placeholder="搜索节点：depth/path/name/text/role" />
          </div>
          <div class="status-info" style="margin-top:6px;">
            <p><strong>全树节点:</strong> {{ atspiAllSearchedNodes.length }} / {{ atspiSnapshotNodes.length }}</p>
            <p><strong>全树显示:</strong> {{ atspiFilteredDisplayNodes.length }}</p>
            <p><strong>有坐标节点:</strong> {{ atspiPositionedNodes.length }}</p>
          </div>
        </div>

        <div class="result-box" v-if="atspiFilteredDisplayNodes.length > 0">
          <h4>AT-SPI全树节点({{ atspiFilteredDisplayNodes.length }}):</h4>
          <div v-for="(node, index) in atspiFilteredDisplayNodes" :key="'atspi_node_' + index" class="element-item">
            <p>
              <strong>{{ node.role || 'unknown' }}</strong>
              | 深度: {{ node.depth ?? '-' }}
              | 名称: {{ node.name || '-' }}
              | 文本: {{ node.text || '-' }}
            </p>
            <p>
              位置({{ node.bounds.x }}, {{ node.bounds.y }}), 尺寸({{ node.bounds.width }}x{{ node.bounds.height }})
              <button class="btn btn-sm btn-outline-primary ml-2" @click="validateATSPIBoundsClick(node)">点击验证</button>
              <button class="btn btn-sm btn-outline-primary ml-2" @click="startATSPIControlCalibration(node)">校准并保存</button>
            </p>
            <p>路径: {{ node.path || '-' }}</p>
          </div>
        </div>

        <div class="result-box" v-else-if="atspiAllSearchedNodes.length > 0">
          <p>当前搜索词没有匹配节点，请调整搜索条件。</p>
        </div>

        <div class="result-box" v-if="atspiPositionedNodes.length > 0">
          <h4>带位置信息节点({{ atspiPositionedNodes.length }}):</h4>
          <div v-for="(node, index) in atspiPositionedNodes" :key="'atspi_pos_node_' + index" class="element-item">
            <p>
              <strong>{{ node.role || 'unknown' }}</strong>
              | 深度: {{ node.depth ?? '-' }}
              | 名称: {{ node.name || '-' }}
            </p>
            <p>
              位置({{ node.bounds.x }}, {{ node.bounds.y }}), 尺寸({{ node.bounds.width }}x{{ node.bounds.height }})
              <button class="btn btn-sm btn-outline-primary ml-2" @click="validateATSPIBoundsClick(node)">点击验证</button>
              <button class="btn btn-sm btn-outline-primary ml-2" @click="startATSPIControlCalibration(node)">校准并保存</button>
            </p>
            <p>路径: {{ node.path || '-' }}</p>
          </div>
        </div>

        <div class="result-box" v-if="atspiAllSearchedNodes.length > 0">
          <h4>结构规律分析（分层 / 次级窗体 / 区域）</h4>

          <h5>深度分层统计:</h5>
          <div v-for="row in atspiDepthStats" :key="'depth_' + row.depth" class="element-item">
            <p>Depth {{ row.depth }}: 总节点 {{ row.total }}，有坐标 {{ row.positioned }}</p>
          </div>

          <h5>角色分布(Top 15):</h5>
          <div v-for="row in atspiRoleStats" :key="'role_' + row.role" class="element-item">
            <p>{{ row.role }}: 总节点 {{ row.total }}，有坐标 {{ row.positioned }}</p>
          </div>

          <h5>次级窗体区域（按 Root -> Child[n]）:</h5>
          <div v-for="row in atspiSubWindowStats" :key="'sub_' + row.region" class="element-item">
            <p>{{ row.region }}: 总节点 {{ row.total }}，有坐标 {{ row.positioned }}</p>
          </div>

          <h5>坐标区域分布（3x3）:</h5>
          <div v-for="row in atspiZoneStats" :key="'zone_' + row.zone" class="element-item">
            <p>{{ row.zone }}: {{ row.count }}</p>
          </div>
        </div>

        <div class="result-box" v-if="atspiSnapshotNodes.length > 0">
          <h4>模板/OCR补盲清单:</h4>
          <div v-for="item in atspiFallbackChecklist" :key="item.id" class="element-item">
            <p>
              <strong>{{ item.label }}</strong>
              | 状态: {{ item.status }}
              | 建议: {{ item.recommendation }}
            </p>
            <p>关键词: {{ item.keywords.join(' / ') }}</p>
          </div>
        </div>

        <div class="result-box" v-if="atspiClickValidationResult">
          <h4>节点点击验证结果:</h4>
          <pre>{{ atspiClickValidationResult }}</pre>
        </div>

        <div class="result-box" v-if="atspiCalibrationDraft" style="margin-top:10px;">
          <h4>AT-SPI坐标校准工作台</h4>
          <div class="form-group">
            <label>全局偏差量（用于整批偏移）:</label>
            <div class="input-row">
              <input v-model.number="atspiGlobalOffsetX" type="number" placeholder="全局偏差X" />
              <input v-model.number="atspiGlobalOffsetY" type="number" placeholder="全局偏差Y" />
              <button class="btn btn-secondary" @click="applyGlobalOffsetToDraft">应用到当前控件</button>
            </div>
          </div>

          <div class="form-group">
            <label>控件元信息:</label>
            <div class="input-row">
              <input v-model="atspiCalibrationDraft.control_type" type="text" placeholder="类别名称，如 button" />
              <input v-model="atspiCalibrationDraft.ui_scene" type="text" placeholder="所在界面，如 聊天界面--菜单区区域" />
            </div>
            <div class="input-row" style="margin-top:8px;">
              <input v-model="atspiCalibrationDraft.function" type="text" placeholder="点击后作用，如 发送信息/激活输入框" />
              <label style="display:flex;align-items:center;gap:6px;min-width:220px;">
                <input type="checkbox" v-model="atspiCalibrationDraft.needs_rescan_after_click" /> 点击后需要更新界面定位
              </label>
            </div>
          </div>

          <div class="form-group">
            <label>坐标校准（在原坐标基础上手动微调）:</label>
            <div class="input-row">
              <input v-model.number="atspiCalibrationDraft.manual_offset_x" type="number" placeholder="手动偏移X" />
              <input v-model.number="atspiCalibrationDraft.manual_offset_y" type="number" placeholder="手动偏移Y" />
              <button class="btn btn-info" @click="recomputeCalibrationBounds">重新计算校准坐标</button>
            </div>
            <p style="margin:8px 0 0; color:#555;">
              原始: ({{ atspiCalibrationDraft.base_bounds.x }}, {{ atspiCalibrationDraft.base_bounds.y }}, {{ atspiCalibrationDraft.base_bounds.width }}x{{ atspiCalibrationDraft.base_bounds.height }})
              → 校准: ({{ atspiCalibrationDraft.bounds.x }}, {{ atspiCalibrationDraft.bounds.y }}, {{ atspiCalibrationDraft.bounds.width }}x{{ atspiCalibrationDraft.bounds.height }})
            </p>
          </div>

          <div class="action-grid">
            <button class="btn btn-primary" @click="validateCalibratedControlClick">按校准坐标点击验证</button>
            <button class="btn btn-success" @click="saveCalibratedControl">保存校准控件</button>
            <button class="btn btn-warning" @click="syncCalibratedControlsToAnnotationRows">同步到构建标注行</button>
            <button class="btn btn-secondary" @click="cancelCalibrationDraft">取消</button>
          </div>
        </div>

        <div class="result-box" v-if="calibratedControls.length > 0" style="margin-top:10px;">
          <h4>已保存校准控件({{ calibratedControls.length }})</h4>
          <div class="action-grid">
            <button class="btn btn-secondary" @click="exportCalibratedControls">导出校准控件</button>
            <button class="btn btn-warning" @click="syncCalibratedControlsToAnnotationRows">同步到构建标注行</button>
          </div>
          <div v-for="item in calibratedControls" :key="item.region_id" class="element-item">
            <p>
              <strong>#{{ item.serial_no }}</strong>
              | region_id: {{ item.region_id }}
              | 类别: {{ item.control_type }}
              | 名称: {{ item.name }}
            </p>
            <p>
              所在界面: {{ item.ui_scene }}
              | 作用: {{ item.function }}
              | 重识别: {{ item.needs_rescan_after_click ? '是' : '否' }}
            </p>
            <p>
              坐标: ({{ item.bounds.x }}, {{ item.bounds.y }}, {{ item.bounds.width }}x{{ item.bounds.height }})
              <button class="btn btn-sm btn-outline-primary ml-2" @click="validateCalibratedControlClick(item)">点击验证</button>
              <button class="btn btn-sm btn-danger ml-2" @click="removeCalibratedControl(item.region_id)">删除</button>
            </p>
          </div>
        </div>

        <div class="result-box" v-if="atspiClickBeforeImage || atspiClickAfterImage">
          <h4>点击前后打点校验图:</h4>
          <div class="row">
            <div class="col-md-6" v-if="atspiClickBeforeImage">
              <p><strong>点击前</strong></p>
              <img :src="atspiClickBeforeImage" alt="atspi-click-before" class="screenshot-image">
            </div>
            <div class="col-md-6" v-if="atspiClickAfterImage">
              <p><strong>点击后</strong></p>
              <img :src="atspiClickAfterImage" alt="atspi-click-after" class="screenshot-image">
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="card test-section" v-if="activeGroup === 'template'">
      <div class="card-header">
        <h3>设置区域（2套模板 / 5个区域）</h3>
      </div>
      <div class="card-body" :class="{ 'section-readonly': setupLocked }">
        <div class="lock-tip" v-if="setupLocked">第一轮设置已确认锁定：当前区域仅查看，不可修改。</div>
        <div class="form-group">
          <label>模板类型:</label>
          <select v-model="selectedTemplateType" class="form-control">
            <option value="chat">聊天界面模板</option>
            <option value="contacts">联系人界面模板</option>
          </select>
        </div>
        <div class="form-group">
          <label>配置名:</label>
          <input v-model="scanProfileName" class="form-control" />
        </div>
        <div class="form-group">
          <label>扫描超时(秒):</label>
          <input v-model.number="scanTimeoutSeconds" type="number" min="5" max="120" class="form-control" />
        </div>

        <div class="quick-actions" style="margin-top: 10px;">
          <button @click="startRegionAnnotation" class="btn btn-warning">启动5区域标注流程</button>
          <button @click="finishRegionAnnotation" class="btn btn-success" :disabled="currentAnnotationStep < regionAnnotationSteps.length || isRegionSaveInProgress">
            {{ isRegionSaveInProgress ? '保存中...' : '完成并保存区域配置' }}
          </button>
          <button @click="cancelRegionAnnotation" class="btn btn-danger">取消流程</button>
        </div>

        <div class="status-info" style="margin-top: 12px;">
          <div><strong>当前步骤:</strong> {{ isRegionAnnotationActive ? `${currentAnnotationStep + 1}/${regionAnnotationSteps.length}` : '未开始' }}</div>
          <div><strong>可用配置:</strong> {{ scanProfilesSummary }}</div>
        </div>

        <div v-if="regionSetupCompletion.visible" class="result-box" style="margin-top: 12px; border: 2px solid #28a745;">
          <h4>本次区域设置已完成</h4>
          <p>配置已保存：{{ regionSetupCompletion.profileName }}（{{ regionSetupCompletion.templateType === 'chat' ? '聊天界面模板' : '联系人界面模板' }}）。</p>
          
          <div v-if="regionSetupCompletion.screenshot" class="annotated-screenshot-preview" style="margin-top: 12px;">
            <h5>标注区域预览：</h5>
            <img :src="'data:image/png;base64,' + regionSetupCompletion.screenshot" alt="标注区域预览" class="screenshot-image" style="max-width: 100%; border: 1px solid #ddd;" />
            <p style="margin-top: 8px; color: #666; font-size: 0.9em;">请确认以上标注的区域是否正确。如果不正确，请重新进行区域标注。</p>
          </div>
          
          <div class="quick-actions">
            <button class="btn btn-warning" @click="restartRegionAnnotation" style="margin-right: 8px;">重新标注</button>
            <button class="btn btn-primary" @click="goToScanProgramSetup">进入后续扫描程序设置</button>
          </div>
        </div>

        <div v-if="isRegionAnnotationActive" class="form-group" style="margin-top: 12px; border: 2px solid #007bff; padding: 12px; border-radius: 8px;">
          <h4>5区域顺序标注流程 ({{ selectedTemplateType === 'chat' ? '聊天界面' : '联系人界面' }})</h4>
          <div class="annotation-steps">
            <div v-for="(region, index) in regionAnnotationSteps" :key="region.id" class="step-item" :class="{ active: currentAnnotationStep === index, completed: index < currentAnnotationStep }">
              <div class="step-header">
                <span class="step-number">{{ index + 1 }}</span>
                <span class="step-name">{{ region.name }}</span>
                <span class="step-status" v-if="index < currentAnnotationStep">✓</span>
                <span class="step-status" v-else-if="index === currentAnnotationStep">进行中</span>
              </div>
              <div class="step-description">{{ region.description }}</div>
              <div v-if="index === currentAnnotationStep" class="step-actions">
                <button @click="annotateCurrentRegion" class="btn btn-sm btn-primary">标注此区域（手动两点）</button>
                <button @click="skipCurrentRegion" class="btn btn-sm btn-secondary">跳过</button>
              </div>
              <div v-if="regionAnnotationSteps[index].bounds" class="step-bounds">
                边界: ({{ regionAnnotationSteps[index].bounds.x }}, {{ regionAnnotationSteps[index].bounds.y }}, {{ regionAnnotationSteps[index].bounds.width }}x{{ regionAnnotationSteps[index].bounds.height }})
              </div>
            </div>
          </div>

          <div class="result-box" v-if="manualRegionAnnotation.active" style="margin-top:10px;">
            <h5>手动区域标注中：{{ manualRegionAnnotation.regionName }}</h5>
            <p>操作说明：已激活微信并抓取当前窗口截图，请在下图 <strong>先点左上角，再点右下角</strong> 完成该区域标注。</p>
            <p>
              第一点击点: {{ manualRegionAnnotation.firstPoint ? `(${manualRegionAnnotation.firstPoint.x}, ${manualRegionAnnotation.firstPoint.y})` : '未选择' }}
              ，第二点击点: {{ manualRegionAnnotation.secondPoint ? `(${manualRegionAnnotation.secondPoint.x}, ${manualRegionAnnotation.secondPoint.y})` : '未选择' }}
            </p>
            <div class="action-grid">
              <button class="btn btn-secondary" @click="resetManualRegionPoints">重选本区域两点</button>
              <button class="btn btn-danger" @click="cancelManualRegionAnnotation">取消本次标注</button>
            </div>
            <div class="manual-region-canvas" v-if="fullWindowScreenshot">
              <img
                :src="fullWindowScreenshot"
                alt="manual-region-base"
                class="screenshot-image"
                @click="onManualRegionImageClick"
                @load="onManualRegionImageLoad"
              />
              <div v-if="manualRegionOverlayRect" class="overlay-box" :style="manualRegionOverlayRect">
                <span class="overlay-label">{{ manualRegionAnnotation.regionName }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="card test-section" v-if="activeGroup === 'layout'">
      <div class="card-header">
        <h3>界面鼠标定位（第二级控件校对）</h3>
      </div>
      <div class="card-body" :class="{ 'section-readonly': setupLocked }">
        <div class="lock-tip" v-if="setupLocked">第一轮设置已确认锁定：当前区域仅查看，不可修改。</div>
        <div class="form-group">
          <label>模板类型:</label>
          <select v-model="selectedTemplateType" class="form-control">
            <option value="chat">聊天界面</option>
            <option value="contacts">联系人界面</option>
          </select>
        </div>
        <div class="form-group">
          <label>配置名:</label>
          <input v-model="scanProfileName" class="form-control" />
        </div>
        <div class="form-group">
          <label>扫描超时(秒):</label>
          <input v-model.number="scanTimeoutSeconds" type="number" min="5" max="120" class="form-control" />
        </div>
        <div class="form-group">
          <label>扫描方向:</label>
          <select v-model="scanDirection" class="form-control">
            <option value="right_to_left">从右到左</option>
            <option value="left_to_right">从左到右</option>
          </select>
        </div>

        <div class="input-row">
          <input v-model.number="scanStepX" type="number" min="10" max="300" placeholder="横向步长(px)" />
          <input v-model.number="scanStepY" type="number" min="10" max="300" placeholder="纵向步长(px)" />
          <input v-model.number="scanSettleMs" type="number" min="500" max="5000" placeholder="停顿(ms，建议3000)" />
        </div>

        <div class="input-row" style="margin-top: 8px;">
          <input v-model.number="scanLockWidth" type="number" min="400" max="1920" placeholder="固定宽度" />
          <input v-model.number="scanLockHeight" type="number" min="300" max="1400" placeholder="固定高度" />
          <input v-model.number="scanLockX" type="number" placeholder="X" />
          <input v-model.number="scanLockY" type="number" placeholder="Y" />
        </div>

        <div class="quick-actions" style="margin-top: 10px;">
          <button @click="runFixWindowForScan" class="btn btn-primary">1) 固定微信窗口</button>
          <button @click="runFullScan" class="btn btn-info" :disabled="isScanRunning">
            {{ isScanRunning ? '2) 扫描中...' : '2) 全面扫描' }}
          </button>
          <button @click="cancelFullScan" class="btn btn-danger" :disabled="!isScanRunning">中断扫描</button>
          <button @click="runBuildProfile" class="btn btn-success">3) 构建标注配置</button>
          <button @click="refreshScanProfiles" class="btn btn-secondary">刷新配置列表</button>
        </div>

        <div class="result-box" style="margin-top: 12px;">
          <h4>手动扫描（空格采样 / 回车完成 / ESC退出）</h4>
          <div class="input-row" style="margin-bottom: 8px;">
            <select v-model="manualScanRegionName">
              <option value="search_bar">search_bar（搜索栏）</option>
              <option value="main_menu">main_menu（主菜单）</option>
              <option value="contact_list">contact_list（联系人列表）</option>
              <option value="chat_display">chat_display（聊天展示）</option>
              <option value="chat_input">chat_input（聊天输入）</option>
            </select>
            <input v-model="manualScanControlType" type="text" placeholder="控件类型，如 button" />
          </div>
          <div class="input-row" style="margin-bottom: 8px;">
            <input v-model.number="manualScanDiffThreshold" type="number" min="6" max="96" placeholder="diff阈值" />
            <input v-model.number="manualScanMinArea" type="number" min="30" max="2000" placeholder="最小变化面积" />
          </div>
          <div class="input-row" style="margin-bottom: 8px; align-items: center;">
            <label style="display:flex;align-items:center;gap:6px;min-width:180px;">
              <input type="checkbox" v-model="manualScanRequireQuad" /> 仅保留四边形候选
            </label>
            <input v-model.number="manualScanCursorIgnoreRadius" type="number" min="6" max="60" placeholder="光标剔除半径" />
          </div>
          <div class="quick-actions">
            <button class="btn btn-warning" @click="startManualScan" :disabled="isManualScanRunning">启动手动扫描</button>
            <button class="btn btn-primary" @click="captureManualScan" :disabled="!isManualScanRunning || isManualScanCapturing">空格：记录一次</button>
            <button class="btn btn-success" @click="finishManualScan" :disabled="!isManualScanRunning">回车：结束并汇总</button>
            <button class="btn btn-danger" @click="abortManualScan" :disabled="!isManualScanRunning">ESC：强制退出</button>
          </div>
          <div class="status-info" style="margin-top: 8px;">
            <div><strong>手动扫描状态:</strong> {{ manualScanStatus }}</div>
            <div><strong>会话ID:</strong> {{ manualScanSessionId || '-' }}</div>
            <div><strong>采样统计:</strong> {{ manualScanStats }}</div>
            <div><strong>比较范围:</strong> 仅当前所选区域（5区域之一），不会比较其它区域</div>
            <div><strong>快捷键提示:</strong> 仅在本页且手动扫描进行中生效（输入框聚焦时不拦截）</div>
          </div>
        </div>

        <div class="status-info" style="margin-top: 8px;" v-if="isScanRunning || scanProgressPercent > 0">
          <div><strong>扫描进度:</strong> {{ scanProgressPercent }}%</div>
          <div><strong>当前阶段:</strong> {{ scanProgressStage || '等待中' }}</div>
          <div><strong>阶段说明:</strong> {{ scanProgressMessage || '-' }}</div>
          <div class="scan-progress-wrap">
            <div class="scan-progress-bar" :style="{ width: `${scanProgressPercent}%` }"></div>
          </div>
        </div>

        <div class="form-group" style="margin-top: 12px;">
          <label>构建输入（可编辑JSON，用于入库构建）:</label>
          <textarea v-model="annotationJsonText" class="form-control" rows="8"></textarea>
        </div>

        <div class="quick-actions" style="margin-top: 8px;">
          <button @click="exportCurrentProfile" class="btn btn-warning">导出当前配置</button>
          <label class="btn btn-secondary" style="margin:0;">
            导入设置文件
            <input type="file" accept="application/json" style="display:none" @change="importProfileFile" />
          </label>
        </div>

        <div class="status-info" style="margin-top: 12px;">
          <div><strong>最近扫描结果:</strong> {{ scanLastMessage }}</div>
          <div><strong>可用配置:</strong> {{ scanProfilesSummary }}</div>
          <div><strong>区域调试:</strong> {{ scanRegionDebugSummary || '-' }}</div>
        </div>

        <div v-if="scanAnnotatedImage" class="form-group" style="margin-top: 12px;">
          <label>变化区域标记图:</label>
          <img :src="scanAnnotatedImage" alt="scan-annotated" class="screenshot-image" />
        </div>

        <div v-if="scanBuiltAnnotatedImage" class="form-group" style="margin-top: 12px;">
          <label>构建后标注确认图:</label>
          <img :src="scanBuiltAnnotatedImage" alt="scan-built-annotated" class="screenshot-image" />
          <p style="margin-top: 8px; color: #666; font-size: 0.9em;">请确认以上标注坐标是否可用；若不准确，请中断并重新扫描/调整标注后再构建。</p>
        </div>

        <div v-if="scanAnnotationRows.length" class="form-group" style="margin-top: 12px;">
          <label>变化区域标注（扫描后逐项填写）:</label>
          <table class="annotation-table">
            <thead>
              <tr>
                <th>启用</th>
                <th>区域ID</th>
                <th>名称</th>
                <th>动作(function)</th>
                <th>范围(x,y,w,h)</th>
                <th>可点击</th>
                <th>点击后重识别</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in scanAnnotationRows" :key="row.region_id">
                <td><input type="checkbox" v-model="row.enabled" /></td>
                <td>{{ row.region_id }}</td>
                <td><input v-model="row.name" class="form-control" /></td>
                <td><input v-model="row.function" class="form-control" /></td>
                <td class="bounds-cell">
                  <input v-model.number="row.bounds.x" type="number" class="form-control tiny" />
                  <input v-model.number="row.bounds.y" type="number" class="form-control tiny" />
                  <input v-model.number="row.bounds.width" type="number" class="form-control tiny" />
                  <input v-model.number="row.bounds.height" type="number" class="form-control tiny" />
                </td>
                <td><input type="checkbox" v-model="row.clickable" /></td>
                <td><input type="checkbox" v-model="row.needs_rescan_after_click" /></td>
              </tr>
            </tbody>
          </table>

          <div class="quick-actions" style="margin-top: 8px;">
            <button @click="generateAnnotationJsonFromRows" class="btn btn-secondary">生成构建JSON</button>
            <button @click="runBuildProfileFromRows" class="btn btn-success">按当前标注构建配置</button>
          </div>
        </div>
      </div>
    </div>

    <div class="card test-section" v-if="activeGroup === 'multiLayer'">
      <div class="card-header">
        <h3>多层标注 (AT-SPI + 鼠标扫描 + OCR+AI + 手动确认)</h3>
      </div>
      <div class="card-body">
        <div class="form-group">
          <label>配置名:</label>
          <input v-model="multiLayerProfileName" class="form-control" />
        </div>
        <div class="form-group">
          <label>模板类型:</label>
          <select v-model="multiLayerTemplateType" class="form-control">
            <option value="chat">聊天界面</option>
            <option value="contacts">联系人界面</option>
          </select>
        </div>
        <div class="form-group">
          <label>区域:</label>
          <select v-model="multiLayerRegionId" class="form-control">
            <option value="search_bar">搜索栏</option>
            <option value="main_menu">主菜单工具栏</option>
            <option value="contact_list">联系人列表</option>
            <option value="chat_display">聊天显示区</option>
            <option value="chat_input">聊天输入区</option>
          </select>
        </div>
        <div class="form-group">
          <label>启用层:</label>
          <div class="checkbox-group">
            <label><input type="checkbox" v-model="multiLayerIncludeAtsPi" /> AT-SPI树</label>
            <label><input type="checkbox" v-model="multiLayerIncludeMouseScan" /> 鼠标扫描</label>
            <label><input type="checkbox" v-model="multiLayerIncludeOcr" /> OCR+AI</label>
          </div>
        </div>
        <div class="action-grid">
          <button @click="performMultiLayerAnnotation" class="btn btn-primary">执行多层标注</button>
        </div>

        <div v-if="multiLayerResults" class="result-box" style="margin-top:10px;">
          <h4>多层标注结果:</h4>
          <div v-for="(layerResult, layerName) in multiLayerResults.layers" :key="layerName" class="layer-result">
            <h5>{{ layerName.toUpperCase() }}层 {{ layerResult.success ? '✓' : '✗' }}</h5>
            <div v-if="layerResult.error" class="error-msg">{{ layerResult.error }}</div>
            <div v-else-if="layerResult.candidates.length > 0">
              <div v-for="(candidate, idx) in layerResult.candidates" :key="`${layerName}_${idx}`" class="candidate-item">
                <p><strong>候选 {{ idx + 1 }}:</strong> 置信度 {{ (candidate.confidence * 100).toFixed(1) }}%</p>
                <p>边界: ({{ candidate.bounds.x }}, {{ candidate.bounds.y }}, {{ candidate.bounds.width }}x{{ candidate.bounds.height }})</p>
                <p v-if="candidate.text">文本: {{ candidate.text }}</p>
                <p v-if="candidate.role">角色: {{ candidate.role }}</p>
                <p v-if="candidate.hover_hits !== undefined">悬停命中: {{ candidate.hover_hits }}</p>
                <button @click="selectAnnotation(layerName, candidate)" class="btn btn-sm btn-success">选择此标注</button>
              </div>
            </div>
            <div v-else>无候选结果</div>
          </div>
        </div>

        <div v-if="selectedAnnotation" class="form-group" style="margin-top:10px; border: 2px solid #28a745; padding: 10px;">
          <h4>已选标注 ({{ selectedAnnotation.layer }})</h4>
          <p>边界: ({{ selectedAnnotation.bounds.x }}, {{ selectedAnnotation.bounds.y }}, {{ selectedAnnotation.bounds.width }}x{{ selectedAnnotation.bounds.height }})</p>
          <p>置信度: {{ (selectedAnnotation.confidence * 100).toFixed(1) }}%</p>
          <div class="form-group">
            <label>备注:</label>
            <input v-model="annotationNotes" class="form-control" placeholder="可选备注" />
          </div>
          <button @click="confirmSelectedAnnotation" class="btn btn-success">确认并保存</button>
          <button @click="cancelSelectedAnnotation" class="btn btn-secondary">取消</button>
        </div>
      </div>
    </div>

    <div class="card test-section" v-if="activeGroup === 'preview'">
      <div class="card-header">
        <h3>整合定位预览（最终确认）</h3>
      </div>
      <div class="card-body">
        <div class="quick-actions">
          <button class="btn btn-primary" @click="captureFullWindow">刷新预览底图</button>
          <button class="btn btn-info" @click="applyIntegratedRowsToCalibratedControls">应用整合结果到已校准控件</button>
          <button class="btn btn-success" @click="confirmAndLockSetup" :disabled="setupLocked">确认并锁定第一轮设置</button>
          <button class="btn btn-warning" @click="unlockSetup" :disabled="!setupLocked">解锁前4个设置区域</button>
        </div>
        <div class="status-info" style="margin-top:8px;">
          <p><strong>第一轮设置状态:</strong> {{ setupLocked ? '已锁定（前4区只读）' : '未锁定（可继续调整）' }}</p>
        </div>

        <div class="result-box" style="margin-top:10px;" v-if="fullWindowScreenshot">
          <h4>底图红框预览（前置区域标注 + AT-SPI校准 + 鼠标标注整合）</h4>
          <div class="preview-canvas" :style="{ width: `${previewRenderedWidth}px` }">
            <img :src="fullWindowScreenshot" alt="preview-base" class="screenshot-image" @load="handlePreviewImageLoad" />
            <div
              v-for="item in calibratedOverlayBoxes"
              :key="`overlay_${item.region_id}`"
              class="overlay-box"
              :style="item.style"
            >
              <span class="overlay-label">#{{ item.serial_no }} {{ item.name }} ({{ item.control_type }})</span>
            </div>
          </div>
          <p v-if="!calibratedOverlayBoxes.length" style="margin-top:8px; color:#666;">已加载底图，暂无可显示红框（请确认前置区域标注/AT-SPI校准/鼠标标注中至少一项已生成有效边界）。</p>
        </div>

        <div class="result-box" style="margin-top:10px;" v-else>
          <p>暂无底图红框预览，请先截图完整窗口。</p>
        </div>

        <div class="result-box" style="margin-top:10px;" v-if="integratedConflictGroups.length">
          <h4>冲突选择（{{ integratedConflictGroups.length }} 组）</h4>
          <p style="margin-bottom:8px; color:#666;">同一 region_id 存在多来源标注时，可在这里选择最终保留来源。</p>
          <div v-for="group in integratedConflictGroups" :key="`conflict_${group.region_id}`" class="element-item">
            <p><strong>{{ group.region_id }}</strong>（候选 {{ group.candidates.length }}）</p>
            <select
              class="form-control"
              :value="getIntegratedConflictSelection(group)"
              @change="updateIntegratedConflictSelection(group.region_id, $event.target.value)"
            >
              <option
                v-for="candidate in group.candidates"
                :key="candidate.candidate_key"
                :value="candidate.candidate_key"
              >
                {{ candidate.source_label }} | {{ candidate.name }} | ({{ candidate.bounds.x }}, {{ candidate.bounds.y }}, {{ candidate.bounds.width }}x{{ candidate.bounds.height }})
              </option>
            </select>
            <p v-if="group.resolved" style="margin-top:6px; color:#666;">当前生效: {{ group.resolved.source_label }} - {{ group.resolved.name }}</p>
          </div>
        </div>

        <div class="result-box" style="margin-top:10px;" v-if="integratedControlRows.length">
          <h4>控件统一确认清单({{ integratedControlRows.length }})</h4>
          <div v-for="item in integratedControlRows" :key="`confirm_${item.region_id}`" class="element-item">
            <p><strong>#{{ item.serial_no }} {{ item.name }}</strong> ({{ item.control_type }})</p>
            <p>来源: {{ item.source_label || '-' }} | 所在界面: {{ item.ui_scene || '-' }} | 作用: {{ item.function }} | 点击后重识别: {{ item.needs_rescan_after_click ? '是' : '否' }}</p>
            <p>坐标: ({{ item.bounds.x }}, {{ item.bounds.y }}, {{ item.bounds.width }}x{{ item.bounds.height }})</p>
          </div>
        </div>

        <div class="status-info">
          <p><strong>窗口锁定预设:</strong> {{ windowSize.width }}x{{ windowSize.height }} @ ({{ windowPosition.x }}, {{ windowPosition.y }})</p>
          <p><strong>ATSPI节点:</strong> {{ atspiPositionedNodes.length }}</p>
          <p><strong>模板识别元素:</strong> {{ analyzedElements.length }}</p>
          <p><strong>OCR命中条目:</strong> {{ ocrPreviewCount }}</p>
        </div>
        <div class="result-box" style="margin-top:10px;" v-if="integratedPreviewRows.length">
          <h4>整合标注预览({{ integratedPreviewRows.length }}):</h4>
          <div v-for="(item, idx) in integratedPreviewRows" :key="'preview_' + idx" class="element-item">
            <p><strong>[{{ item.source }}]</strong> {{ item.name }} ({{ item.type }})</p>
            <p>位置({{ item.bounds.x }}, {{ item.bounds.y }}), 尺寸({{ item.bounds.width }}x{{ item.bounds.height }})</p>
            <p v-if="item.extra">{{ item.extra }}</p>
          </div>
        </div>
        <div class="result-box" style="margin-top:10px;" v-else>
          <p>暂无可预览标注，请先执行 ATSPI 快照、模板识别或 OCR。</p>
        </div>
      </div>
    </div>

    <div class="alert alert-info mt-4">
      <p>此测试面板用于测试后端cpp_rpa模块的各个功能。</p>
      <p>所有操作都会调用后端API，通过C++ RPA模块执行相应的自动化任务。</p>
    </div>

    <div class="card test-section" v-if="activeGroup === 'atomicContainerSettings'">
      <div class="card-header">
        <h3>原子容器设置管理（查询定义/规则预设/激活点击输入）</h3>
      </div>
      <div class="card-body">
        <AtomicContainerSettings />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import axios from 'axios'
import AtomicContainerSettings from './AtomicContainerSettings.vue'

axios.defaults.baseURL = 'http://localhost:8000'

const WECHAT_WINDOW_PRESET_KEY = 'wechat_window_activation_preset_v1'
const ATSPI_CALIBRATED_CONTROLS_KEY = 'atspi_calibrated_controls_v1'
const SETUP_ROUND1_LOCK_KEY = 'rpa_setup_round1_locked_v1'
const ATOMIC_PROFILE_ID_KEY = 'rpa_atomic_profile_id_v1'
const SHARED_PROFILE_ID_KEY = 'wechat_shared_profile_id_v1'
const ATOMIC_CONTROLS_UPDATED_AT_KEY = 'wechat_atomic_controls_updated_at_v1'
const ATOMIC_QUERY_PIPELINE_CONFIG_KEY = 'rpa_atomic_pipeline_config_v1'
const DEFAULT_WECHAT_WINDOW_PRESET = {
  width: 980,
  height: 1025,
  x: 860,
  y: 0,
}

// 数据定义
const wechatStatus = ref('未知')
const systemStatus = ref({
  isRunning: false,
  isConnected: false,
  version: ''
})
const windowInfo = ref('')
const messageContent = ref('')
const latestMessages = ref([])
const contactKeyword = ref('')
const contacts = ref([])
const selectedContactInfo = ref('')
const atomicProfileId = ref(null)
const atomicSelectedRegionId = ref('')
const atomicControlUid = ref('')
const atomicControlName = ref('')
const atomicRegionKey = ref('')
const atomicControlType = ref('')
const atomicPrimaryAction = ref('click')
const atomicNextAction = ref('')
const atomicRequiresPreUseRescan = ref(false)
const atomicHasPostClickChange = ref(false)
const atomicSaveResult = ref('')
const atomicEditingControlId = ref(null)
const atomicLibraryItems = ref([])
const atomicImportExportText = ref('')
const atomicLibraryLastLoadedAt = ref('')
const atomicReferencesResultText = ref('')
const atomicGenerateQueryFilters = ref({
  role_contains: '',
  name_contains: '',
  expected_depth: '',
  require_non_zero_rect: 'true',
})
const atomicPipelineConfig = ref(null)
const atomicPipelineConfigSummary = ref('')
const controlName = ref('')
const atspiResult = ref('')
const atspiRoleFilter = ref('')
const atspiNameFilter = ref('')
const atspiMaxNodes = ref(2000)
const atspiMaxDepth = ref(-1)
const atspiAutoRefreshTree = ref(false)
const atspiRefreshRounds = ref(1)
const atspiRefreshIntervalMs = ref(0)
const atspiSnapshotNodes = ref([])
const atspiSnapshotSummary = ref('')
const atspiClickValidationResult = ref('')
const atspiClickBeforeImage = ref('')
const atspiClickAfterImage = ref('')
const atspiOnlyActionable = ref(false)
const atspiOnlyPositioned = ref(false)
const atspiSearchText = ref('')
const atspiGlobalOffsetX = ref(0)
const atspiGlobalOffsetY = ref(0)
const atspiCalibrationDraft = ref(null)
const calibratedControls = ref([])
const setupLocked = ref(false)
const previewRenderedWidth = ref(0)
const previewNaturalWidth = ref(0)
const previewNaturalHeight = ref(0)
const humanizedResult = ref('')
const windowSize = ref({ width: DEFAULT_WECHAT_WINDOW_PRESET.width, height: DEFAULT_WECHAT_WINDOW_PRESET.height })
const windowPosition = ref({ x: DEFAULT_WECHAT_WINDOW_PRESET.x, y: DEFAULT_WECHAT_WINDOW_PRESET.y })
const messageScreenshot = ref('')
const fullWindowScreenshot = ref('')
const inputText = ref('')
const isWeChatLaunching = ref(false)
const wechatScriptPath = ref('')
const uiElements = ref([])
const uiTreeAnalysis = ref('')
const analyzedElements = ref([])
const allButtons = ref([])
const annotatedElements = ref([])
const clickedElement = ref('')
const elementTestResult = ref('')
const lastClickStrategy = ref('')
const clickStrategyTrace = ref([])
const lastClickTotalElapsedMs = ref(0)
const ocrImagePath = ref('')
const ocrTextResult = ref('')
const selectedLayout = ref('one-third-two-thirds')
const customFrontendWidth = ref(33)
const windowTarget = ref('active')
const scanProfileName = ref('wechat_main_layout')
const scanTimeoutSeconds = ref(25)
const scanDirection = ref('right_to_left')
const scanStepX = ref(15)
const scanStepY = ref(20)
const scanSettleMs = ref(3000)
const scanLockWidth = ref(DEFAULT_WECHAT_WINDOW_PRESET.width)
const scanLockHeight = ref(DEFAULT_WECHAT_WINDOW_PRESET.height)
const scanLockX = ref(DEFAULT_WECHAT_WINDOW_PRESET.x)
const scanLockY = ref(DEFAULT_WECHAT_WINDOW_PRESET.y)
const scanLastMessage = ref('未执行')
const scanProfilesSummary = ref('无')
const scanAnnotatedImage = ref('')
const scanBuiltAnnotatedImage = ref('')
const scanTaskId = ref('')
const isScanRunning = ref(false)
const scanProgressPercent = ref(0)
const scanProgressStage = ref('')
const scanProgressMessage = ref('')
const scanRegionDebugSummary = ref('')
const scanAnnotationRows = ref([])
const manualScanSessionId = ref('')
const isManualScanRunning = ref(false)
const isManualScanCapturing = ref(false)
const manualScanStatus = ref('未启动')
const manualScanCaptures = ref(0)
const manualScanRawRects = ref(0)
const manualScanCandidateCount = ref(0)
const manualScanRegionName = ref('chat_input')
const manualScanControlType = ref('button')
const manualScanDiffThreshold = ref(14)
const manualScanMinArea = ref(120)
const manualScanRequireQuad = ref(true)
const manualScanCursorIgnoreRadius = ref(18)
const manualScanCoordinateFilePath = ref('')
const manualScanPointsFilePath = ref('')
const manualScanPollTimer = ref(null)
const manualScanFinalizing = ref(false)
const annotationJsonText = ref(JSON.stringify([
  {
    region_id: 'send_button',
    name: '发送按钮',
    function: 'send_message',
    clickable: true,
    needs_rescan_after_click: false,
    control_type: 'button',
    confidence: 0.95
  }
], null, 2))
const isPipelineRunning = ref(false)
const pipelineStatus = ref('')
const selectedTemplateType = ref('chat')
const isRegionAnnotationActive = ref(false)
const currentAnnotationStep = ref(0)
const isRegionSaveInProgress = ref(false)
const regionAnnotationBaselineReady = ref(false)
const regionAnnotationBaselineTemplate = ref('')
const regionSetupCompletion = ref({
  visible: false,
  profileName: '',
  templateType: 'chat',
  screenshot: null,
})
const manualRegionAnnotation = ref({
  active: false,
  regionIndex: -1,
  regionName: '',
  firstPoint: null,
  secondPoint: null,
})
const manualRegionImageMetrics = ref({
  renderedWidth: 0,
  renderedHeight: 0,
  naturalWidth: 0,
  naturalHeight: 0,
})
const integratedConflictSelections = ref({})
const regionAnnotationSteps = ref([
  { id: 'search_bar', name: '搜索栏', description: '顶部搜索输入框区域' },
  { id: 'main_menu', name: '主菜单工具栏', description: '顶部工具栏按钮区域' },
  { id: 'contact_list', name: '联系人列表', description: '左侧联系人列表区域' },
  { id: 'chat_display', name: '聊天显示区', description: '中间聊天消息显示区域' },
  { id: 'chat_input', name: '聊天输入区', description: '底部消息输入区域' }
])
const browserWindow = ref({
  width: window.innerWidth,
  height: window.innerHeight,
  x: window.screenX,
  y: window.screenY,
})
const activeGroup = ref('basic')

const manualScanStats = computed(() => {
  const coords = manualScanCoordinateFilePath.value ? `, 坐标文件: ${manualScanCoordinateFilePath.value}` : ''
  const points = manualScanPointsFilePath.value ? `, 点位文件: ${manualScanPointsFilePath.value}` : ''
  return `采样 ${manualScanCaptures.value} 次，原始变化块 ${manualScanRawRects.value}，候选 ${manualScanCandidateCount.value}${coords}${points}`
})

// 多层标注相关
const multiLayerProfileName = ref('wechat_main_layout')
const multiLayerTemplateType = ref('chat')
const multiLayerRegionId = ref('search_bar')
const multiLayerIncludeAtsPi = ref(true)
const multiLayerIncludeMouseScan = ref(true)
const multiLayerIncludeOcr = ref(true)
const multiLayerResults = ref(null)
const selectedAnnotation = ref(null)
const annotationNotes = ref('')

const atspiAllSearchedNodes = computed(() => {
  const nodes = atspiSnapshotNodes.value || []
  const keyword = String(atspiSearchText.value || '').trim().toLowerCase()
  if (!keyword) {
    return nodes
  }

  return nodes.filter((node) => {
    const searchable = [
      String(node?.depth ?? ''),
      String(node?.path || ''),
      String(node?.name || ''),
      String(node?.text || ''),
      String(node?.role || ''),
    ].join(' ').toLowerCase()
    return searchable.includes(keyword)
  })
})

const atspiFilteredDisplayNodes = computed(() => {
  let nodes = atspiAllSearchedNodes.value || []

  if (atspiOnlyPositioned.value) {
    nodes = nodes.filter((node) => {
      const bounds = node?.bounds || {}
      return Number(bounds.width || 0) > 0 && Number(bounds.height || 0) > 0
    })
  }

  if (!atspiOnlyActionable.value) {
    return nodes
  }

  const interactiveRoles = ['button', 'entry', 'text', 'textbox', 'list item', 'menu item', 'check box']
  return nodes.filter((node) => {
    const bounds = node?.bounds || {}
    const width = Number(bounds.width || 0)
    const height = Number(bounds.height || 0)
    if (width <= 0 || height <= 0) {
      return false
    }
    const role = String(node?.role || '').toLowerCase()
    const clickableHint = !!node?.clickable_hint
    return clickableHint || interactiveRoles.some((item) => role.includes(item))
  })
})

const atspiPositionedNodes = computed(() => {
  return (atspiAllSearchedNodes.value || [])
    .filter((node) => {
      const b = node?.bounds || {}
      return Number(b.width || 0) > 0 && Number(b.height || 0) > 0
    })
    .sort((a, b) => {
      const aa = Number(a?.bounds?.width || 0) * Number(a?.bounds?.height || 0)
      const bb = Number(b?.bounds?.width || 0) * Number(b?.bounds?.height || 0)
      return bb - aa
    })
})

const atspiDepthStats = computed(() => {
  const grouped = new Map()
  for (const node of atspiAllSearchedNodes.value || []) {
    const depth = Number(node?.depth ?? -1)
    const key = Number.isFinite(depth) ? depth : -1
    const hasPos = Number(node?.bounds?.width || 0) > 0 && Number(node?.bounds?.height || 0) > 0
    if (!grouped.has(key)) {
      grouped.set(key, { depth: key, total: 0, positioned: 0 })
    }
    const row = grouped.get(key)
    row.total += 1
    if (hasPos) row.positioned += 1
  }
  return Array.from(grouped.values()).sort((a, b) => a.depth - b.depth)
})

const atspiRoleStats = computed(() => {
  const grouped = new Map()
  for (const node of atspiAllSearchedNodes.value || []) {
    const role = String(node?.role || 'unknown').trim() || 'unknown'
    const hasPos = Number(node?.bounds?.width || 0) > 0 && Number(node?.bounds?.height || 0) > 0
    if (!grouped.has(role)) {
      grouped.set(role, { role, total: 0, positioned: 0 })
    }
    const row = grouped.get(role)
    row.total += 1
    if (hasPos) row.positioned += 1
  }
  return Array.from(grouped.values()).sort((a, b) => b.total - a.total).slice(0, 15)
})

const atspiSubWindowStats = computed(() => {
  const grouped = new Map()
  const regex = /^Root\s*->\s*Child\[(\d+)\]/
  for (const node of atspiAllSearchedNodes.value || []) {
    const path = String(node?.path || 'Root')
    const match = path.match(regex)
    const key = match ? `Child[${match[1]}]` : 'Root'
    const hasPos = Number(node?.bounds?.width || 0) > 0 && Number(node?.bounds?.height || 0) > 0
    if (!grouped.has(key)) {
      grouped.set(key, { region: key, total: 0, positioned: 0 })
    }
    const row = grouped.get(key)
    row.total += 1
    if (hasPos) row.positioned += 1
  }
  return Array.from(grouped.values()).sort((a, b) => b.total - a.total)
})

const atspiZoneStats = computed(() => {
  const nodes = atspiPositionedNodes.value || []
  if (!nodes.length) return []

  const xMin = Math.min(...nodes.map((n) => Number(n.bounds.x || 0)))
  const yMin = Math.min(...nodes.map((n) => Number(n.bounds.y || 0)))
  const xMax = Math.max(...nodes.map((n) => Number(n.bounds.x || 0) + Number(n.bounds.width || 0)))
  const yMax = Math.max(...nodes.map((n) => Number(n.bounds.y || 0) + Number(n.bounds.height || 0)))
  const w = Math.max(1, xMax - xMin)
  const h = Math.max(1, yMax - yMin)

  const grouped = new Map()
  for (const node of nodes) {
    const cx = Number(node.bounds.x || 0) + Number(node.bounds.width || 0) / 2
    const cy = Number(node.bounds.y || 0) + Number(node.bounds.height || 0) / 2
    const rx = (cx - xMin) / w
    const ry = (cy - yMin) / h
    const xPart = rx < 1 / 3 ? '左' : (rx < 2 / 3 ? '中' : '右')
    const yPart = ry < 1 / 3 ? '上' : (ry < 2 / 3 ? '中' : '下')
    const key = `${xPart}-${yPart}`
    grouped.set(key, (grouped.get(key) || 0) + 1)
  }
  return Array.from(grouped.entries())
    .map(([zone, count]) => ({ zone, count }))
    .sort((a, b) => b.count - a.count)
})

const atspiFallbackChecklist = computed(() => {
  const nodes = atspiSnapshotNodes.value || []
  const normalize = (v) => String(v || '').toLowerCase()
  const searchable = (node) => `${normalize(node.name)} ${normalize(node.text)} ${normalize(node.role)}`

  const targets = [
    { id: 'send_button', label: '发送按钮', keywords: ['发送', 'send'], fallback: '模板+OCR' },
    { id: 'input_box', label: '输入框', keywords: ['输入', 'entry', 'edit', 'text'], fallback: 'ATSPI优先，几何兜底' },
    { id: 'more_menu', label: '更多菜单', keywords: ['更多', 'more', 'menu'], fallback: '模板匹配' },
    { id: 'file_button', label: '文件/附件', keywords: ['文件', '附件', 'file', 'attach'], fallback: '模板+OCR' },
    { id: 'contact_list', label: '联系人列表', keywords: ['联系人', 'contact', 'list'], fallback: '几何+OCR' },
    { id: 'search_box', label: '搜索框', keywords: ['搜索', 'search', 'find'], fallback: '模板+OCR' },
  ]

  return targets.map((target) => {
    const hit = nodes.some((node) => {
      const text = searchable(node)
      return target.keywords.some((kw) => {
        const key = normalize(kw)
        return key && text.includes(key)
      })
    })
    return {
      ...target,
      status: hit ? '已命中' : '待补盲',
      recommendation: hit ? '优先 ATSPI 使用' : target.fallback,
    }
  })
})

const ocrPreviewCount = computed(() => {
  const text = String(ocrTextResult.value || '').trim()
  if (!text) return 0
  try {
    const parsed = JSON.parse(text)
    if (Array.isArray(parsed.text)) return parsed.text.length
  } catch {
    return text.split('\n').filter(Boolean).length
  }
  return 1
})

const integratedPreviewRows = computed(() => {
  const rows = []

  for (const row of (scanAnnotationRows.value || []).filter((item) => item?.enabled !== false).slice(0, 40)) {
    const bounds = row?.bounds || {}
    rows.push({
      source: '构建标注行',
      name: row?.name || row?.region_id || 'unknown',
      type: row?.control_type || 'unknown',
      bounds: {
        x: Number(bounds.x || 0),
        y: Number(bounds.y || 0),
        width: Number(bounds.width || 0),
        height: Number(bounds.height || 0),
      },
      extra: row?.region_id ? `region_id: ${row.region_id}` : '',
    })
  }

  for (const node of (atspiPositionedNodes.value || []).slice(0, 30)) {
    rows.push({
      source: 'ATSPI',
      name: node?.name || node?.text || 'unknown',
      type: node?.role || 'unknown',
      bounds: {
        x: Number(node?.bounds?.x || 0),
        y: Number(node?.bounds?.y || 0),
        width: Number(node?.bounds?.width || 0),
        height: Number(node?.bounds?.height || 0),
      },
      extra: node?.path ? `path: ${node.path}` : '',
    })
  }

  for (const element of (analyzedElements.value || []).slice(0, 30)) {
    const bounds = element?.bounds || {}
    rows.push({
      source: '模板坐标',
      name: element?.name || element?.id || 'unknown',
      type: element?.type || 'unknown',
      bounds: {
        x: Number(bounds.x || 0),
        y: Number(bounds.y || 0),
        width: Number(bounds.width || 0),
        height: Number(bounds.height || 0),
      },
      extra: '',
    })
  }

  for (const element of (annotatedElements.value || []).slice(0, 30)) {
    const bounds = element?.bounds || {}
    rows.push({
      source: '标注层',
      name: element?.name || element?.id || 'unknown',
      type: element?.type || 'unknown',
      bounds: {
        x: Number(bounds.x || 0),
        y: Number(bounds.y || 0),
        width: Number(bounds.width || 0),
        height: Number(bounds.height || 0),
      },
      extra: '',
    })
  }

  if (ocrPreviewCount.value > 0) {
    rows.push({
      source: 'OCR',
      name: 'OCR命中文本',
      type: 'text',
      bounds: { x: 0, y: 0, width: 0, height: 0 },
      extra: `命中 ${ocrPreviewCount.value} 条`,
    })
  }

  return rows.slice(0, 100)
})

const INTEGRATED_SOURCE_PRIORITY = {
  atspi: 1,
  scan: 2,
  region: 3,
}

const integratedRegionAnnotationRows = computed(() => {
  const rows = []
  for (const step of (regionAnnotationSteps.value || [])) {
    const bounds = step?.bounds || {}
    const width = Number(bounds.width || 0)
    const height = Number(bounds.height || 0)
    if (width <= 0 || height <= 0) continue
    const regionId = String(step?.id || '').trim() || `region_${rows.length + 1}`
    rows.push({
      serial_no: rows.length + 1,
      region_id: regionId,
      name: step?.name || regionId,
      control_type: 'region',
      ui_scene: selectedTemplateType.value || '',
      function: 'manual_region_anchor',
      needs_rescan_after_click: false,
      confidence: 1,
      source_kind: 'region',
      source_label: '前置区域标注',
      bounds: {
        x: Number(bounds.x || 0),
        y: Number(bounds.y || 0),
        width,
        height,
      },
    })
  }
  return rows
})

const integratedAllCandidates = computed(() => {
  const rows = []

  for (const row of (scanAnnotationRows.value || [])) {
    if (row?.enabled === false) continue
    const bounds = row?.bounds || {}
    const width = Number(bounds.width || 0)
    const height = Number(bounds.height || 0)
    if (width <= 0 || height <= 0) continue
    const regionId = String(row?.region_id || '').trim() || `scan_${rows.length + 1}`
    rows.push({
      serial_no: Number(row?.serial_no || 0) || rows.length + 1,
      region_id: regionId,
      name: row?.name || regionId,
      control_type: row?.control_type || 'other',
      ui_scene: row?.ui_scene || '',
      function: row?.function || 'unknown_action',
      needs_rescan_after_click: !!row?.needs_rescan_after_click,
      confidence: Number(row?.confidence || 0),
      source_kind: 'scan',
      source_label: row?.source_label || '鼠标标注/构建标注',
      bounds: {
        x: Number(bounds.x || 0),
        y: Number(bounds.y || 0),
        width,
        height,
      },
    })
  }

  for (const item of (calibratedControls.value || [])) {
    const bounds = item?.bounds || {}
    const width = Number(bounds.width || 0)
    const height = Number(bounds.height || 0)
    if (width <= 0 || height <= 0) continue
    const regionId = String(item?.region_id || '').trim() || `atspi_${rows.length + 1}`
    rows.push({
      ...item,
      serial_no: Number(item?.serial_no || 0) || rows.length + 1,
      region_id: regionId,
      confidence: Number(item?.confidence || 0),
      source_kind: 'atspi',
      source_label: 'AT-SPI校准',
      bounds: {
        x: Number(bounds.x || 0),
        y: Number(bounds.y || 0),
        width,
        height,
      },
    })
  }

  for (const regionRow of integratedRegionAnnotationRows.value) {
    rows.push({
      ...regionRow,
      serial_no: Number(regionRow?.serial_no || 0) || rows.length + 1,
      confidence: Number(regionRow?.confidence || 1),
      source_kind: 'region',
      source_label: '前置区域标注',
    })
  }

  return rows.map((item, index) => ({
    ...item,
    candidate_key: `${item.source_kind || 'unknown'}::${item.region_id || 'unknown'}::${index}`,
  }))
})

const resolveIntegratedCandidate = (candidates = [], regionId = '') => {
  const selectedKey = String(integratedConflictSelections.value?.[regionId] || '')
  const selected = candidates.find((item) => item?.candidate_key === selectedKey)
  if (selected) return selected

  const ranked = [...candidates].sort((a, b) => {
    const pa = INTEGRATED_SOURCE_PRIORITY[a?.source_kind] || 99
    const pb = INTEGRATED_SOURCE_PRIORITY[b?.source_kind] || 99
    if (pa !== pb) return pa - pb
    return Number(b?.confidence || 0) - Number(a?.confidence || 0)
  })
  return ranked[0] || null
}

const integratedConflictGroups = computed(() => {
  const grouped = new Map()
  for (const item of integratedAllCandidates.value) {
    const regionId = String(item?.region_id || '').trim() || item?.candidate_key
    if (!grouped.has(regionId)) {
      grouped.set(regionId, [])
    }
    grouped.get(regionId).push(item)
  }

  const conflicts = []
  for (const [region_id, candidates] of grouped.entries()) {
    if (!Array.isArray(candidates) || candidates.length <= 1) continue
    conflicts.push({
      region_id,
      candidates,
      resolved: resolveIntegratedCandidate(candidates, region_id),
    })
  }
  return conflicts.sort((a, b) => a.region_id.localeCompare(b.region_id))
})

const getIntegratedConflictSelection = (group) => {
  const regionId = String(group?.region_id || '')
  const candidates = Array.isArray(group?.candidates) ? group.candidates : []
  const resolved = resolveIntegratedCandidate(candidates, regionId)
  return resolved?.candidate_key || ''
}

const updateIntegratedConflictSelection = (regionId, candidateKey) => {
  integratedConflictSelections.value = {
    ...(integratedConflictSelections.value || {}),
    [regionId]: candidateKey,
  }
}

const integratedControlRows = computed(() => {
  const grouped = new Map()
  for (const item of integratedAllCandidates.value) {
    const regionId = String(item?.region_id || '').trim() || item?.candidate_key
    if (!grouped.has(regionId)) {
      grouped.set(regionId, [])
    }
    grouped.get(regionId).push(item)
  }

  const resolved = []
  for (const [regionId, candidates] of grouped.entries()) {
    const picked = resolveIntegratedCandidate(candidates, regionId)
    if (picked) {
      resolved.push({ ...picked })
    }
  }

  return resolved
    .sort((a, b) => {
      const sa = Number(a.serial_no || 0)
      const sb = Number(b.serial_no || 0)
      if (sa !== sb) return sa - sb
      return String(a.region_id || '').localeCompare(String(b.region_id || ''))
    })
    .map((item, index) => ({
      ...item,
      serial_no: index + 1,
    }))
})

const normalizeControlsForSyncCheck = (rows = []) => {
  return (rows || [])
    .map((item, index) => {
      const bounds = item?.bounds || {}
      const serialNo = Number(item?.serial_no || 0) > 0 ? Number(item.serial_no) : (index + 1)
      const regionId = String(item?.region_id || '').trim() || buildCalibratedRegionId(serialNo)
      return {
        region_id: regionId,
        serial_no: serialNo,
        name: String(item?.name || '').trim(),
        control_type: String(item?.control_type || 'other').trim(),
        function: String(item?.function || '').trim(),
        needs_rescan_after_click: !!item?.needs_rescan_after_click,
        bounds: {
          x: Number(bounds.x || 0),
          y: Number(bounds.y || 0),
          width: Number(bounds.width || 0),
          height: Number(bounds.height || 0),
        },
      }
    })
    .filter((item) => Number(item.bounds.width || 0) > 0 && Number(item.bounds.height || 0) > 0)
    .sort((a, b) => {
      const sa = Number(a.serial_no || 0)
      const sb = Number(b.serial_no || 0)
      if (sa !== sb) return sa - sb
      return String(a.region_id || '').localeCompare(String(b.region_id || ''))
    })
}

const hasPendingIntegratedSync = computed(() => {
  const integrated = normalizeControlsForSyncCheck(integratedControlRows.value || [])
  if (!integrated.length) return false
  const calibrated = normalizeControlsForSyncCheck(calibratedControls.value || [])
  return JSON.stringify(integrated) !== JSON.stringify(calibrated)
})

const calibratedOverlayBoxes = computed(() => {
  if (!previewRenderedWidth.value || !previewNaturalWidth.value || !previewNaturalHeight.value) {
    return []
  }

  const scale = previewRenderedWidth.value / previewNaturalWidth.value
  const wx = Number(windowPosition.value.x || 0)
  const wy = Number(windowPosition.value.y || 0)
  const imageWidth = Number(previewNaturalWidth.value || 0)
  const imageHeight = Number(previewNaturalHeight.value || 0)

  const insideRatio = (left, top, width, height) => {
    if (width <= 0 || height <= 0 || imageWidth <= 0 || imageHeight <= 0) {
      return 0
    }
    const right = left + width
    const bottom = top + height
    const interLeft = Math.max(0, left)
    const interTop = Math.max(0, top)
    const interRight = Math.min(imageWidth, right)
    const interBottom = Math.min(imageHeight, bottom)
    const interWidth = Math.max(0, interRight - interLeft)
    const interHeight = Math.max(0, interBottom - interTop)
    const interArea = interWidth * interHeight
    const totalArea = width * height
    return totalArea > 0 ? interArea / totalArea : 0
  }

  let relativeScore = 0
  let absoluteScore = 0
  for (const item of integratedControlRows.value) {
    const b = item?.bounds || {}
    const x = Number(b.x || 0)
    const y = Number(b.y || 0)
    const width = Number(b.width || 0)
    const height = Number(b.height || 0)
    if (width <= 0 || height <= 0) continue
    relativeScore += insideRatio(x, y, width, height)
    absoluteScore += insideRatio(x - wx, y - wy, width, height)
  }

  const useAbsolute = absoluteScore > relativeScore

  return integratedControlRows.value.map((item) => {
    const b = item?.bounds || {}
    const rawX = Number(b.x || 0)
    const rawY = Number(b.y || 0)
    const mappedX = useAbsolute ? (rawX - wx) : rawX
    const mappedY = useAbsolute ? (rawY - wy) : rawY
    const left = mappedX * scale
    const top = mappedY * scale
    const width = Math.max(2, Number(b.width || 0) * scale)
    const height = Math.max(2, Number(b.height || 0) * scale)
    return {
      ...item,
      style: {
        left: `${left}px`,
        top: `${top}px`,
        width: `${width}px`,
        height: `${height}px`,
      },
    }
  })
})

const manualRegionOverlayRect = computed(() => {
  if (!manualRegionAnnotation.value.active) return null
  const first = manualRegionAnnotation.value.firstPoint
  const second = manualRegionAnnotation.value.secondPoint
  if (!first || !second) return null

  const metrics = manualRegionImageMetrics.value
  const rw = Number(metrics.renderedWidth || 0)
  const rh = Number(metrics.renderedHeight || 0)
  const nw = Number(metrics.naturalWidth || 0)
  const nh = Number(metrics.naturalHeight || 0)
  if (!rw || !rh || !nw || !nh) return null

  const scaleX = rw / nw
  const scaleY = rh / nh
  const x1 = Math.min(Number(first.x || 0), Number(second.x || 0))
  const y1 = Math.min(Number(first.y || 0), Number(second.y || 0))
  const x2 = Math.max(Number(first.x || 0), Number(second.x || 0))
  const y2 = Math.max(Number(first.y || 0), Number(second.y || 0))

  return {
    left: `${x1 * scaleX}px`,
    top: `${y1 * scaleY}px`,
    width: `${Math.max(2, (x2 - x1) * scaleX)}px`,
    height: `${Math.max(2, (y2 - y1) * scaleY)}px`,
  }
})

// 辅助函数：显示消息
const showMessage = (message, type = 'info') => {
  // 使用浏览器原生alert作为备选方案
  alert(`${type.toUpperCase()}: ${message}`)
  console.log(`${type}: ${message}`)
}

const formatErrorDetail = (error, fallback = '未知错误') => {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (detail !== undefined && detail !== null) {
    try {
      return JSON.stringify(detail, null, 2)
    } catch {
      return String(detail)
    }
  }
  return error?.message || fallback
}

const formatJson = (data) => {
  try {
    return JSON.stringify(data, null, 2)
  } catch {
    return String(data)
  }
}

const selectedAtomicSourceControl = computed(() => {
  const regionId = String(atomicSelectedRegionId.value || '').trim()
  if (!regionId) return null
  return (calibratedControls.value || []).find((item) => String(item.region_id || '').trim() === regionId) || null
})

const usedAtomicSourceRegionIds = computed(() => {
  const used = new Set()
  for (const item of (atomicLibraryItems.value || [])) {
    const sourceRefId = String(item?.source_ref_id || '').trim()
    if (sourceRefId) {
      used.add(sourceRefId)
    }
  }
  return used
})

const availableCalibratedControlsForAtomic = computed(() => {
  const editingSourceRef = atomicEditingControlId.value
    ? String(((atomicLibraryItems.value || []).find((item) => Number(item?.id || 0) === Number(atomicEditingControlId.value || 0))?.source_ref_id || '')).trim()
    : ''
  const selected = String(atomicSelectedRegionId.value || '').trim()
  const allowSet = new Set([selected, editingSourceRef].filter(Boolean))
  return (calibratedControls.value || []).filter((item) => {
    const regionId = String(item?.region_id || '').trim()
    if (!regionId) return false
    if (allowSet.has(regionId)) return true
    return !usedAtomicSourceRegionIds.value.has(regionId)
  })
})

const atomicPipelineCanAutoGenerate = computed(() => {
  const config = atomicPipelineConfig.value
  if (!config) return false
  return Number(config?.query_count || 0) === 1
})

const generateAtomicControlUid = () => {
  const usedUid = new Set(
    (atomicLibraryItems.value || [])
      .map((item) => String(item?.control_uid || '').trim())
      .filter(Boolean)
  )
  const usedSerial = new Set()
  for (const uid of usedUid) {
    const match = /^atspi_(\d+)$/i.exec(uid)
    if (!match) continue
    usedSerial.add(Number(match[1] || 0))
  }

  let serial = 1
  while (usedSerial.has(serial)) {
    serial += 1
  }

  let candidate = `atspi_${String(serial).padStart(4, '0')}`
  while (usedUid.has(candidate)) {
    serial += 1
    candidate = `atspi_${String(serial).padStart(4, '0')}`
  }
  return candidate
}

const refreshAtomicControlUid = () => {
  if (atomicEditingControlId.value) return
  atomicControlUid.value = generateAtomicControlUid()
}

const parseAtomicActions = () => {
  const actions = []
  const primary = String(atomicPrimaryAction.value || '').trim()
  const next = String(atomicNextAction.value || '').trim()
  if (primary) actions.push(primary)
  if (next) actions.push(next)
  return actions
}

const buildAtomicControlPayload = () => {
  const librarySource = atomicEditingControlId.value
    ? ((atomicLibraryItems.value || []).find((item) => Number(item.id || 0) === Number(atomicEditingControlId.value || 0)) || {})
    : {}
  const source = selectedAtomicSourceControl.value || librarySource || {}
  const bounds = source?.bounds || {}
  const regionId = String(source?.region_id || atomicSelectedRegionId.value || '').trim()
  const finalUid = String(atomicControlUid.value || '').trim() || generateAtomicControlUid()
  const finalName = String(atomicControlName.value || source?.name || '').trim()
  const finalRegionKey = String(atomicRegionKey.value || '').trim() || 'chat'
  const finalControlType = String(atomicControlType.value || source?.control_type || '').trim()

  return {
    id: atomicEditingControlId.value || undefined,
    control_uid: finalUid,
    profile_id: Number(atomicProfileId.value || 0),
    enabled: true,
    region_key: finalRegionKey,
    role: String(source?.role || finalControlType || '').trim(),
    control_type: finalControlType,
    depth: Number(source?.depth || 0),
    depth_code: String(source?.depth_code || '00'),
    access_path: String(source?.path || source?.access_path || '').trim(),
    path_numeric_code: String(source?.path_numeric_code || '').trim(),
    x: Number(bounds.x || 0),
    y: Number(bounds.y || 0),
    width: Number(bounds.width || 0),
    height: Number(bounds.height || 0),
    text: finalName,
    window_type: 'chat',
    actions: parseAtomicActions(),
    is_clickable: true,
    has_post_click_change: !!atomicHasPostClickChange.value,
    source_type: 'calibrated',
    source_ref_id: regionId,
    confidence: Number(source?.confidence || 0.9),
    meta: {
      ui_scene: String(source?.ui_scene || '').trim(),
      function: String(source?.function || '').trim(),
      needs_rescan_after_click: !!source?.needs_rescan_after_click,
      requires_pre_use_rescan: !!atomicRequiresPreUseRescan.value,
      next_action: String(atomicNextAction.value || '').trim(),
    },
  }
}

const syncAtomicFromCalibratedControl = () => {
  const source = selectedAtomicSourceControl.value
  if (!source) {
    atomicSaveResult.value = ''
    refreshAtomicControlUid()
    return
  }

  refreshAtomicControlUid()
  atomicControlName.value = String(source.name || '').trim()
  atomicRegionKey.value = String(source.ui_scene || '').includes('输入') ? 'chat_input' : 'chat'
  atomicControlType.value = String(source.control_type || source.role || '').trim() || 'other'
  atomicPrimaryAction.value = String(source.function || '').includes('输入') ? 'input_text' : 'click'
  atomicNextAction.value = ''
  atomicRequiresPreUseRescan.value = false
  atomicHasPostClickChange.value = !!source.needs_rescan_after_click
  atomicEditingControlId.value = null
}

const resetAtomicEditor = () => {
  atomicSelectedRegionId.value = ''
  atomicControlUid.value = generateAtomicControlUid()
  atomicControlName.value = ''
  atomicRegionKey.value = ''
  atomicControlType.value = ''
  atomicPrimaryAction.value = 'click'
  atomicNextAction.value = ''
  atomicRequiresPreUseRescan.value = false
  atomicHasPostClickChange.value = false
  atomicEditingControlId.value = null
}

const normalizeAtomicFilters = (raw = {}) => {
  const payload = { ...(raw || {}) }
  Object.keys(payload).forEach((key) => {
    if (payload[key] === '' || payload[key] === null || payload[key] === undefined) {
      delete payload[key]
    }
  })
  return payload
}

const loadAtomicPipelineConfig = (silent = true) => {
  try {
    const raw = localStorage.getItem(ATOMIC_QUERY_PIPELINE_CONFIG_KEY)
    if (!raw) {
      atomicPipelineConfig.value = null
      atomicPipelineConfigSummary.value = ''
      if (!silent) {
        showMessage('未找到第7步保存的配置文件', 'warning')
      }
      return null
    }
    const parsed = JSON.parse(raw)
    atomicPipelineConfig.value = parsed
    const profileId = Number(parsed?.profile_id || 0)
    const queryCount = Number(parsed?.query_count || 0)
    const preset = String(parsed?.selected_preset || '').trim() || '-'
    atomicPipelineConfigSummary.value = `profile_id: ${profileId || '-'}\nquery_count: ${queryCount}\nselected_preset: ${preset}\nrecommended_source: ${parsed?.recommended_source || 'query'}`
    if (!silent) {
      showMessage('已读取第7步配置文件', 'success')
    }
    return parsed
  } catch (error) {
    atomicPipelineConfig.value = null
    atomicPipelineConfigSummary.value = ''
    if (!silent) {
      showMessage(`配置文件读取失败: ${error?.message || '未知错误'}`, 'error')
    }
    return null
  }
}

const applyAtomicPipelineConfigToGenerator = async (autoGenerate = false) => {
  const config = atomicPipelineConfig.value || loadAtomicPipelineConfig(true)
  if (!config) {
    showMessage('请先在第7步生成并保存配置文件', 'warning')
    return
  }

  const profileId = Number(config?.profile_id || 0)
  if (profileId > 0) {
    atomicProfileId.value = profileId
  }

  const filters = normalizeAtomicFilters(config?.filters || {})
  atomicGenerateQueryFilters.value = {
    ...filters,
  }

  const maxNodes = Number(config?.filters?.scan_max_nodes || config?.max_nodes || atspiMaxNodes.value || 2200)
  const maxDepth = Number(config?.filters?.scan_max_depth || config?.max_depth || atspiMaxDepth.value || 24)
  atspiMaxNodes.value = Number.isFinite(maxNodes) ? Math.max(200, maxNodes) : 2200
  atspiMaxDepth.value = Number.isFinite(maxDepth) ? maxDepth : 24
  activeGroup.value = 'atomicControls'

  if (autoGenerate) {
    const queryCount = Number(config?.query_count || 0)
    if (queryCount !== 1) {
      showMessage(`当前配置查询结果为 ${queryCount} 条，必须唯一（=1）才允许直接生成。请先回到第7步收敛查询条件。`, 'warning')
      return
    }
    await generateAtomicControlsFromDiscovery('query')
    return
  }
  showMessage('已应用配置到“从高级查询生成控件”参数，可直接点击生成', 'success')
}

const handleAtomicPipelineConfigReady = async (event) => {
  loadAtomicPipelineConfig(true)
  if (!atomicPipelineConfig.value) return
  if (event?.detail?.jumpToAtomicControls) {
    activeGroup.value = 'atomicControls'
  }
  await applyAtomicPipelineConfigToGenerator(false)
}

const refreshAtomicPositioning = async () => {
  atspiAutoRefreshTree.value = true
  atspiRefreshRounds.value = Math.max(1, Number(atspiRefreshRounds.value || 1))
  atspiRefreshIntervalMs.value = Math.max(0, Number(atspiRefreshIntervalMs.value || 0))
  await fetchATSPIControlTreeSnapshot(false, false)
}

const loadAtomicControlLibrary = async () => {
  try {
    const profileId = Number(atomicProfileId.value || 0)
    if (!profileId) {
      throw new Error('请先填写 profile_id')
    }
    atomicLibraryItems.value = []
    const response = await axios.get('/api/v1/wechat/ui/controls', {
      params: {
        profile_id: profileId,
        page: 1,
        page_size: 500,
      },
    })
    atomicLibraryItems.value = response.data?.items || []
    atomicLibraryLastLoadedAt.value = new Date().toLocaleString()
    refreshAtomicControlUid()
  } catch (error) {
    const detail = formatErrorDetail(error)
    atomicLibraryItems.value = []
    atomicLibraryLastLoadedAt.value = ''
    showMessage(`加载原子控件失败: ${detail}`, 'error')
  }
}

const editAtomicControlFromLibrary = (item) => {
  atomicEditingControlId.value = Number(item?.id || 0) || null
  atomicSelectedRegionId.value = String(item?.source_ref_id || '').trim()
  atomicControlUid.value = String(item?.control_uid || '').trim()
  atomicControlName.value = String(item?.text || '').trim()
  atomicRegionKey.value = String(item?.region_key || '').trim()
  atomicControlType.value = String(item?.control_type || '').trim()
  atomicPrimaryAction.value = String((item?.actions || [])[0] || 'click').trim()
  atomicNextAction.value = String((item?.meta || {})?.next_action || (item?.actions || [])[1] || '').trim()
  atomicRequiresPreUseRescan.value = !!((item?.meta || {})?.requires_pre_use_rescan)
  atomicHasPostClickChange.value = !!item?.has_post_click_change
}

const deleteAtomicControl = async (item) => {
  try {
    const profileId = Number(atomicProfileId.value || 0)
    if (!profileId) {
      throw new Error('请先填写 profile_id')
    }
    await axios.post('/api/v1/wechat/ui/controls/delete', {
      profile_id: profileId,
      ids: item?.id ? [Number(item.id)] : [],
      control_uids: item?.control_uid ? [String(item.control_uid)] : [],
      force_unlink_actions: true,
    })
    await loadAtomicControlLibrary()
    await loadAtomicControlReferences({ silent: true })
    showMessage(`已删除控件: ${item?.control_uid || item?.id}`, 'success')
  } catch (error) {
    const detail = formatErrorDetail(error)
    showMessage(`删除原子控件失败: ${detail}`, 'error')
  }
}

const clearAtomicControlsByProfile = async () => {
  try {
    const profileId = Number(atomicProfileId.value || 0)
    if (!profileId) {
      throw new Error('请先填写 profile_id')
    }
    const confirmed = window.confirm(`确认清空 profile_id=${profileId} 下的全部原子控件吗？`)
    if (!confirmed) return

    const response = await axios.post('/api/v1/wechat/ui/controls/delete', {
      profile_id: profileId,
      purge_profile: true,
      force_unlink_actions: true,
    })
    await loadAtomicControlLibrary()
    await loadAtomicControlReferences({ silent: true })
    const deleted = Number(response?.data?.deleted || 0)
    showMessage(`已清空 profile_id=${profileId}，删除 ${deleted} 个控件`, 'success')
  } catch (error) {
    const detail = formatErrorDetail(error)
    showMessage(`清空原子控件失败: ${detail}`, 'error')
  }
}

const loadAtomicControlReferences = async (options = {}) => {
  try {
    const silent = !!options?.silent
    const profileId = Number(atomicProfileId.value || 0)
    if (!profileId) {
      throw new Error('请先填写 profile_id')
    }
    const response = await axios.get('/api/v1/wechat/ui/controls/references', {
      params: {
        profile_id: profileId,
        include_cross_profile: true,
      },
    })
    atomicReferencesResultText.value = formatJson(response.data || {})
    const refsCount = Number(response?.data?.references_count || 0)
    if (!silent) {
      showMessage(`引用关系查询完成，共 ${refsCount} 条`, 'success')
    }
  } catch (error) {
    const detail = formatErrorDetail(error)
    atomicReferencesResultText.value = formatJson({ success: false, detail })
    if (!options?.silent) {
      showMessage(`查询引用关系失败: ${detail}`, 'error')
    }
  }
}

const exportAtomicControls = async () => {
  try {
    const profileId = Number(atomicProfileId.value || 0)
    if (!profileId) {
      throw new Error('请先填写 profile_id')
    }
    const response = await axios.get('/api/v1/wechat/ui/controls', {
      params: { profile_id: profileId },
    })
    const payload = {
      success: true,
      profile_id: profileId,
      exported_at: new Date().toISOString(),
      controls: response.data?.items || [],
    }
    atomicImportExportText.value = JSON.stringify(payload, null, 2)

    const blob = new Blob([atomicImportExportText.value], { type: 'application/json;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `atomic_controls_profile_${profileId}_${Date.now()}.json`
    link.click()
    URL.revokeObjectURL(url)
    showMessage('原子控件已导出', 'success')
  } catch (error) {
    const detail = error?.response?.data?.detail || error?.message || '未知错误'
    showMessage(`导出原子控件失败: ${detail}`, 'error')
  }
}

const importAtomicControls = async () => {
  try {
    const profileId = Number(atomicProfileId.value || 0)
    if (!profileId) {
      throw new Error('请先填写 profile_id')
    }
    const raw = String(atomicImportExportText.value || '').trim()
    if (!raw) {
      throw new Error('请先粘贴控件JSON')
    }
    const parsed = JSON.parse(raw)
    const controls = Array.isArray(parsed?.controls) ? parsed.controls : []
    const regions = Array.isArray(parsed?.regions) ? parsed.regions : []
    if (!controls.length) {
      throw new Error('JSON中未找到controls数组')
    }
    await axios.post('/api/v1/wechat/ui/controls/import', {
      profile: null,
      regions,
      controls: controls.map((item) => {
        const bounds = item?.bounds || {}
        return {
          ...item,
          profile_id: profileId,
          x: Number(item?.x ?? bounds?.x ?? 0),
          y: Number(item?.y ?? bounds?.y ?? 0),
          width: Number(item?.width ?? bounds?.width ?? 0),
          height: Number(item?.height ?? bounds?.height ?? 0),
          actions: Array.isArray(item?.actions) ? item.actions : [],
          meta: item?.meta || {},
        }
      }),
    })
    await loadAtomicControlLibrary()
    showMessage(`导入完成，共${controls.length}个控件`, 'success')
  } catch (error) {
    const detail = error?.response?.data?.detail || error?.message || '未知错误'
    showMessage(`导入原子控件失败: ${detail}`, 'error')
  }
}

const saveAtomicControlDefinition = async () => {
  try {
    if (!atomicEditingControlId.value) {
      atomicControlUid.value = generateAtomicControlUid()
    }
    const payload = buildAtomicControlPayload()
    if (!payload.profile_id) {
      throw new Error('请先填写 profile_id')
    }
    if (!String(payload.control_uid || '').trim()) {
      throw new Error('control_uid不能为空')
    }

    const normalizedUid = String(payload.control_uid || '').trim()
    const hit = (atomicLibraryItems.value || []).find((item) => String(item?.control_uid || '').trim() === normalizedUid)
    const editingId = Number(atomicEditingControlId.value || 0)
    const hitId = Number(hit?.id || 0)
    if (hit && (!editingId || hitId !== editingId)) {
      throw new Error(`control_uid已存在: ${normalizedUid}。若要新增，请使用新的control_uid；若要修改，请点列表里的“编辑”后保存。`)
    }

    const response = await axios.post('/api/v1/wechat/ui/controls/upsert', payload)
    atomicSaveResult.value = formatJson(response.data || {})
    persistAtomicProfileId()
    localStorage.setItem(ATOMIC_CONTROLS_UPDATED_AT_KEY, String(Date.now()))
    await loadAtomicControlLibrary()
    if (!atomicEditingControlId.value) {
      resetAtomicEditor()
    }
    showMessage('标准控件保存成功，可在微信操作打包中直接引用', 'success')
  } catch (error) {
    const detail = formatErrorDetail(error)
    atomicSaveResult.value = formatJson({ success: false, detail })
    showMessage(`保存标准控件失败: ${detail}`, 'error')
  }
}

const generateAtomicControlsFromDiscovery = async (source) => {
  try {
    const profileId = Number(atomicProfileId.value || 0)
    if (!profileId) {
      throw new Error('请先填写 profile_id')
    }

    const payload = {
      profile_id: profileId,
      source: String(source || 'chat'),
      max_nodes: Math.max(200, Number(atspiMaxNodes.value || 2200)),
      max_depth: Number(atspiMaxDepth.value ?? 24),
      limit: 300,
      filters: {
        ...(atomicGenerateQueryFilters.value || {}),
      },
    }

    if (payload.source === 'query') {
      Object.keys(payload.filters).forEach((key) => {
        const raw = payload.filters[key]
        if (raw === '' || raw === null || raw === undefined) {
          delete payload.filters[key]
          return
        }
        payload.filters[key] = String(raw)
      })
    }

    const response = await axios.post('/api/v1/wechat/ui/controls/generate_from_atomic', payload)
    const data = response.data || {}
    atomicSaveResult.value = formatJson(data)
    localStorage.setItem(ATOMIC_CONTROLS_UPDATED_AT_KEY, String(Date.now()))
    await loadAtomicControlLibrary()
    showMessage(`已生成标准控件 ${Number(data.generated || 0)} 个`, 'success')
  } catch (error) {
    const detail = formatErrorDetail(error)
    atomicSaveResult.value = formatJson({ success: false, detail })
    showMessage(`生成标准控件失败: ${detail}`, 'error')
  }
}

const getTemplateScopedProfileName = () => {
  const base = String(scanProfileName.value || '').trim() || 'wechat_main_layout'
  if (base.endsWith('_chat') || base.endsWith('_contacts')) {
    return base
  }
  return `${base}_${selectedTemplateType.value}`
}

const loadAtomicProfileId = () => {
  try {
    const raw = localStorage.getItem(ATOMIC_PROFILE_ID_KEY) || localStorage.getItem(SHARED_PROFILE_ID_KEY)
    if (!raw) return
    const parsed = Number(raw)
    if (parsed > 0) {
      atomicProfileId.value = parsed
    }
  } catch {
  }
}

const persistAtomicProfileId = () => {
  try {
    const profileId = Number(atomicProfileId.value || 0)
    if (profileId > 0) {
      localStorage.setItem(ATOMIC_PROFILE_ID_KEY, String(profileId))
      localStorage.setItem(SHARED_PROFILE_ID_KEY, String(profileId))
    } else {
      localStorage.removeItem(ATOMIC_PROFILE_ID_KEY)
      localStorage.removeItem(SHARED_PROFILE_ID_KEY)
    }
  } catch {
  }
}

const persistCalibratedControls = () => {
  localStorage.setItem(ATSPI_CALIBRATED_CONTROLS_KEY, JSON.stringify(calibratedControls.value || []))
}

const loadCalibratedControls = () => {
  try {
    const raw = localStorage.getItem(ATSPI_CALIBRATED_CONTROLS_KEY)
    if (!raw) {
      calibratedControls.value = []
      return
    }
    const parsed = JSON.parse(raw)
    calibratedControls.value = Array.isArray(parsed) ? parsed : []
  } catch {
    calibratedControls.value = []
  }
}

const loadSetupLockState = () => {
  try {
    setupLocked.value = localStorage.getItem(SETUP_ROUND1_LOCK_KEY) === '1'
  } catch {
    setupLocked.value = false
  }
}

const persistSetupLockState = () => {
  localStorage.setItem(SETUP_ROUND1_LOCK_KEY, setupLocked.value ? '1' : '0')
}

const confirmAndLockSetup = () => {
  setupLocked.value = true
  persistSetupLockState()
  showMessage('已确认并锁定第一轮设置（前4个功能区域只读）', 'success')
}

const unlockSetup = () => {
  setupLocked.value = false
  persistSetupLockState()
  showMessage('已解锁前4个功能区域，可继续修改', 'success')
}

const handlePreviewImageLoad = (event) => {
  const img = event?.target
  if (!img) return
  previewRenderedWidth.value = Number(img.clientWidth || 0)
  previewNaturalWidth.value = Number(img.naturalWidth || 0)
  previewNaturalHeight.value = Number(img.naturalHeight || 0)
}

const buildCalibratedRegionId = (serialNo) => `atspi_${String(serialNo).padStart(4, '0')}`

const nextCalibratedSerialNo = () => {
  const maxSerial = (calibratedControls.value || []).reduce((maxValue, item) => {
    const current = Number(item?.serial_no || 0)
    return current > maxValue ? current : maxValue
  }, 0)
  return maxSerial + 1
}

const recomputeCalibrationBounds = () => {
  if (!atspiCalibrationDraft.value) return
  const draft = atspiCalibrationDraft.value
  const base = draft.base_bounds || { x: 0, y: 0, width: 0, height: 0 }
  draft.bounds = {
    x: Number(base.x || 0) + Number(draft.global_offset_x || 0) + Number(draft.manual_offset_x || 0),
    y: Number(base.y || 0) + Number(draft.global_offset_y || 0) + Number(draft.manual_offset_y || 0),
    width: Number(base.width || 0),
    height: Number(base.height || 0),
  }
}

const startATSPIControlCalibration = (node) => {
  const bounds = node?.bounds || {}
  const width = Number(bounds.width || 0)
  const height = Number(bounds.height || 0)
  if (width <= 0 || height <= 0) {
    showMessage('该节点没有有效坐标，无法进入校准', 'error')
    return
  }

  atspiCalibrationDraft.value = {
    serial_no: 0,
    region_id: '',
    name: node?.name || node?.text || `node_${node?.index ?? 'unknown'}`,
    control_type: String(node?.role || 'other').trim() || 'other',
    ui_scene: '聊天界面--菜单区区域',
    function: '激活',
    clickable: true,
    needs_rescan_after_click: false,
    confidence: Number(node?.match_score || 0.9),
    source: 'atspi',
    role: node?.role || '',
    path: node?.path || '',
    text: node?.text || '',
    base_bounds: {
      x: Number(bounds.x || 0),
      y: Number(bounds.y || 0),
      width,
      height,
    },
    global_offset_x: Number(atspiGlobalOffsetX.value || 0),
    global_offset_y: Number(atspiGlobalOffsetY.value || 0),
    manual_offset_x: 0,
    manual_offset_y: 0,
    bounds: {
      x: Number(bounds.x || 0) + Number(atspiGlobalOffsetX.value || 0),
      y: Number(bounds.y || 0) + Number(atspiGlobalOffsetY.value || 0),
      width,
      height,
    },
  }
  showMessage('已载入控件到校准工作台，可微调后验证/保存', 'info')
}

const applyGlobalOffsetToDraft = () => {
  if (!atspiCalibrationDraft.value) return
  atspiCalibrationDraft.value.global_offset_x = Number(atspiGlobalOffsetX.value || 0)
  atspiCalibrationDraft.value.global_offset_y = Number(atspiGlobalOffsetY.value || 0)
  recomputeCalibrationBounds()
}

const cancelCalibrationDraft = () => {
  atspiCalibrationDraft.value = null
}

const validateCalibratedControlClick = async (item = null) => {
  const target = item || atspiCalibrationDraft.value
  if (!target) {
    showMessage('请先选择或创建一个校准控件', 'error')
    return
  }
  await validateATSPIBoundsClick({ bounds: target.bounds, role: target.role || target.control_type, name: target.name, path: target.path })
}

const saveCalibratedControl = () => {
  if (!atspiCalibrationDraft.value) {
    showMessage('请先选择一个节点进行校准', 'error')
    return
  }
  recomputeCalibrationBounds()
  const draft = JSON.parse(JSON.stringify(atspiCalibrationDraft.value))
  const duplicateIndex = calibratedControls.value.findIndex((item) => item.path === draft.path && item.control_type === draft.control_type && item.name === draft.name)

  if (duplicateIndex >= 0) {
    const serialNo = Number(calibratedControls.value[duplicateIndex].serial_no || 0) || nextCalibratedSerialNo()
    draft.serial_no = serialNo
    draft.region_id = buildCalibratedRegionId(serialNo)
    calibratedControls.value.splice(duplicateIndex, 1, draft)
    showMessage(`已更新校准控件 #${serialNo}`, 'success')
  } else {
    const serialNo = nextCalibratedSerialNo()
    draft.serial_no = serialNo
    draft.region_id = buildCalibratedRegionId(serialNo)
    calibratedControls.value.push(draft)
    showMessage(`已保存校准控件 #${serialNo}`, 'success')
  }

  calibratedControls.value.sort((a, b) => Number(a.serial_no || 0) - Number(b.serial_no || 0))
  persistCalibratedControls()
}

const removeCalibratedControl = (regionId) => {
  calibratedControls.value = calibratedControls.value.filter((item) => item.region_id !== regionId)
  persistCalibratedControls()
  showMessage('已删除校准控件', 'success')
}

const exportCalibratedControls = () => {
  try {
    const payload = {
      exported_at: new Date().toISOString(),
      count: calibratedControls.value.length,
      controls: calibratedControls.value,
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'atspi_calibrated_controls.json'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
    showMessage('导出校准控件成功', 'success')
  } catch (error) {
    showMessage('导出校准控件失败: ' + error.message, 'error')
  }
}

const syncCalibratedControlsToAnnotationRows = () => {
  if (!calibratedControls.value.length) {
    showMessage('暂无校准控件可同步', 'error')
    return
  }

  const merged = new Map()
  for (const row of (scanAnnotationRows.value || [])) {
    const regionId = String(row?.region_id || '').trim()
    if (!regionId) continue
    merged.set(regionId, { ...row })
  }

  for (const item of calibratedControls.value) {
    const regionId = String(item?.region_id || '').trim()
    if (!regionId) continue
    merged.set(regionId, {
      enabled: true,
      region_id: regionId,
      name: item.name,
      function: item.function,
      clickable: item.clickable !== false,
      needs_rescan_after_click: !!item.needs_rescan_after_click,
      control_type: item.control_type || 'other',
      confidence: Number(item.confidence || 0.9),
      ui_scene: item.ui_scene || '',
      serial_no: Number(item.serial_no || 0),
      source_label: 'AT-SPI校准',
      bounds: {
        x: Number(item.bounds?.x || 0),
        y: Number(item.bounds?.y || 0),
        width: Number(item.bounds?.width || 0),
        height: Number(item.bounds?.height || 0),
      },
    })
  }

  scanAnnotationRows.value = Array.from(merged.values())
  generateAnnotationJsonFromRows()
  showMessage(`已同步AT-SPI校准到构建标注行，当前共 ${scanAnnotationRows.value.length} 条`, 'success')
}

const toCalibratedControlRow = (item, index) => {
  const bounds = item?.bounds || {}
  const serialNo = Number(item?.serial_no || 0) > 0 ? Number(item.serial_no) : (index + 1)
  const regionId = String(item?.region_id || '').trim() || buildCalibratedRegionId(serialNo)
  return {
    serial_no: serialNo,
    region_id: regionId,
    name: String(item?.name || regionId || `control_${serialNo}`).trim(),
    control_type: String(item?.control_type || 'other').trim() || 'other',
    ui_scene: String(item?.ui_scene || '').trim(),
    function: String(item?.function || 'unknown_action').trim(),
    clickable: item?.clickable !== false,
    needs_rescan_after_click: !!item?.needs_rescan_after_click,
    confidence: Number(item?.confidence || 0.9),
    source: String(item?.source_kind || item?.source || 'integrated').trim(),
    role: String(item?.role || item?.control_type || '').trim(),
    path: String(item?.path || '').trim(),
    text: String(item?.text || item?.name || '').trim(),
    bounds: {
      x: Number(bounds.x || 0),
      y: Number(bounds.y || 0),
      width: Number(bounds.width || 0),
      height: Number(bounds.height || 0),
    },
  }
}

const applyIntegratedRowsToCalibratedControls = () => {
  const rows = integratedControlRows.value || []
  if (!rows.length) {
    showMessage('暂无整合结果可应用，请先完成预览与冲突选择', 'error')
    return
  }

  const normalized = rows
    .map((item, index) => toCalibratedControlRow(item, index))
    .filter((item) => Number(item?.bounds?.width || 0) > 0 && Number(item?.bounds?.height || 0) > 0)

  if (!normalized.length) {
    showMessage('整合结果没有有效坐标，无法应用', 'error')
    return
  }

  calibratedControls.value = normalized.sort((a, b) => Number(a.serial_no || 0) - Number(b.serial_no || 0))
  persistCalibratedControls()

  const currentRegionId = String(atomicSelectedRegionId.value || '').trim()
  if (currentRegionId && !calibratedControls.value.find((item) => String(item.region_id || '').trim() === currentRegionId)) {
    atomicSelectedRegionId.value = ''
  }

  showMessage(`已应用整合结果，共 ${calibratedControls.value.length} 条校准控件`, 'success')
}

const getWeChatWindowPreset = () => {
  try {
    const raw = localStorage.getItem(WECHAT_WINDOW_PRESET_KEY)
    if (!raw) {
      return { ...DEFAULT_WECHAT_WINDOW_PRESET }
    }
    const parsed = JSON.parse(raw)
    return {
      width: Number(parsed?.width ?? DEFAULT_WECHAT_WINDOW_PRESET.width),
      height: Number(parsed?.height ?? DEFAULT_WECHAT_WINDOW_PRESET.height),
      x: Number(parsed?.x ?? DEFAULT_WECHAT_WINDOW_PRESET.x),
      y: Number(parsed?.y ?? DEFAULT_WECHAT_WINDOW_PRESET.y),
    }
  } catch {
    return { ...DEFAULT_WECHAT_WINDOW_PRESET }
  }
}

const saveWeChatWindowPreset = (silent = false) => {
  const preset = {
    width: Number(windowSize.value.width),
    height: Number(windowSize.value.height),
    x: Number(windowPosition.value.x),
    y: Number(windowPosition.value.y),
  }
  localStorage.setItem(WECHAT_WINDOW_PRESET_KEY, JSON.stringify(preset))
  scanLockWidth.value = preset.width
  scanLockHeight.value = preset.height
  scanLockX.value = preset.x
  scanLockY.value = preset.y
  if (!silent) {
    showMessage(`已保存激活预设: ${preset.width}x${preset.height} @ (${preset.x}, ${preset.y})`, 'success')
  }
}

const refreshSystemStatus = async () => {
  try {
    const response = await axios.get('/api/v1/layout/status')
    if (response.data?.success && response.data?.data) {
      systemStatus.value = {
        isRunning: !!response.data.data.isRunning,
        isConnected: !!response.data.data.isConnected,
        version: response.data.data.version || '',
      }
      return
    }
    showMessage(response.data?.error || response.data?.message || '获取系统状态失败', 'error')
  } catch (error) {
    showMessage('获取系统状态失败: ' + error.message, 'error')
  }
}

const ensureWeChatWindowLockedBeforeActivate = async () => {
  const preset = getWeChatWindowPreset()
  const response = await axios.post('/api/v1/rpa/wechat/ui_profile/fix_window', {
    width: preset.width,
    height: preset.height,
    x: preset.x,
    y: preset.y,
    tolerance: 8,
    retries: 2,
    force_x11_fallback: true,
  })
  if (!response.data?.success) {
    throw new Error(response.data?.detail || response.data?.error || response.data?.message || '固定微信窗口失败')
  }
  return response.data
}

const launchWeChat = async () => {
  if (!wechatScriptPath.value) {
    showMessage('请先设置微信脚本路径', 'error')
    return
  }

  isWeChatLaunching.value = true
  try {
    const response = await axios.post('/api/v1/layout/launch', {
      scriptPath: wechatScriptPath.value,
    })
    if (response.data?.success) {
      showMessage(response.data?.message || '微信启动成功', 'success')
      await refreshSystemStatus()
      return
    }
    showMessage(response.data?.error || response.data?.message || '微信启动失败', 'error')
  } catch (error) {
    showMessage('微信启动失败: ' + error.message, 'error')
  } finally {
    isWeChatLaunching.value = false
  }
}

// 微信基础操作
const activateWeChat = async () => {
  try {
    saveWeChatWindowPreset(true)
    await ensureWeChatWindowLockedBeforeActivate()
    const response = await axios.post('/api/v1/layout/wechat/activate')
    if (response.data.success) {
      showMessage(response.data.message, 'success')
    } else {
      showMessage(response.data.message || '激活微信失败', 'error')
    }
  } catch (error) {
    console.error('激活微信失败:', error)
    showMessage('激活微信失败: ' + error.message, 'error')
  }
}

const checkWeChatStatus = async () => {
  try {
    const response = await axios.post('/api/v1/rpa/wechat/check_status')
    if (response.data.success) {
      wechatStatus.value = response.data.message
      showMessage(response.data.message, 'success')
    } else {
      showMessage(response.data.message || '检查微信状态失败', 'error')
    }
    await refreshSystemStatus()
  } catch (error) {
    console.error('检查微信状态失败:', error)
    showMessage('检查微信状态失败: ' + error.message, 'error')
  }
}

const getWindowInfo = async () => {
  try {
    const response = await axios.post('/api/v1/rpa/wechat/get_window_info')
    if (response.data.success) {
      windowInfo.value = `${response.data.window_info.title} (${response.data.window_info.width}x${response.data.window_info.height})`
      showMessage('窗口信息获取成功', 'success')
    } else {
      showMessage(response.data.message || '获取窗口信息失败', 'error')
    }
  } catch (error) {
    console.error('获取窗口信息失败:', error)
    showMessage('获取窗口信息失败: ' + error.message, 'error')
  }
}

// 控制微信窗口大小和位置
const setWindowSizeAndPosition = async () => {
  try {
    const response = await axios.post('/api/v1/layout/wechat/set_window', {
      width: windowSize.value.width,
      height: windowSize.value.height,
      x: windowPosition.value.x,
      y: windowPosition.value.y
    })
    saveWeChatWindowPreset(true)
    alert('窗口设置成功: ' + JSON.stringify(response.data))
  } catch (error) {
    console.error('设置窗口失败:', error)
    alert('设置窗口失败')
  }
}

const lockWeChatWindow = async () => {
  try {
    await ensureWeChatWindowLockedBeforeActivate()
    showMessage('固定微信窗口成功', 'success')
  } catch (error) {
    showMessage('固定微信窗口失败: ' + error.message, 'error')
  }
}

const registerBrowserWindow = async () => {
  try {
    await axios.post('/api/v1/layout/browser/register_active')
  } catch (error) {
    console.warn('注册浏览器窗口失败:', error)
  }
}

const applyLayout = async () => {
  try {
    await registerBrowserWindow()
    const response = await axios.post('/api/v1/layout/arrange_layout', {
      layout: selectedLayout.value,
      frontendWidthPercent: customFrontendWidth.value,
    })
    if (!response.data?.success) {
      showMessage(response.data?.error || '布局设置失败', 'error')
      return
    }
    showMessage(response.data?.message || '布局设置成功', 'success')
  } catch (error) {
    showMessage('布局设置失败: ' + error.message, 'error')
  }
}

const setBrowserWindowSize = async () => {
  try {
    const response = await axios.post('/api/v1/layout/set_window_size', {
      width: parseInt(browserWindow.value.width),
      height: parseInt(browserWindow.value.height),
      x: parseInt(browserWindow.value.x),
      y: parseInt(browserWindow.value.y),
      target: windowTarget.value,
    })
    if (!response.data?.success) {
      showMessage(response.data?.error || response.data?.warning || '窗口设置失败', 'error')
      return
    }
    showMessage(response.data?.message || '窗口设置成功', 'success')
  } catch (error) {
    showMessage('窗口设置失败: ' + error.message, 'error')
  }
}

const maximizeBrowserWindow = async () => {
  browserWindow.value.width = screen.availWidth
  browserWindow.value.height = screen.availHeight
  browserWindow.value.x = 0
  browserWindow.value.y = 0
  await setBrowserWindowSize()
}

const syncBrowserWindowInfo = () => {
  browserWindow.value.width = window.innerWidth
  browserWindow.value.height = window.innerHeight
  browserWindow.value.x = window.screenX
  browserWindow.value.y = window.screenY
  showMessage(`当前窗口: ${browserWindow.value.width}x${browserWindow.value.height} @ (${browserWindow.value.x}, ${browserWindow.value.y})`, 'info')
}

const runFixWindowForScan = async () => {
  try {
    const response = await axios.post('/api/v1/rpa/wechat/ui_profile/fix_window', {
      width: parseInt(scanLockWidth.value),
      height: parseInt(scanLockHeight.value),
      x: parseInt(scanLockX.value),
      y: parseInt(scanLockY.value),
      tolerance: 8,
      retries: 2,
      force_x11_fallback: true,
    })
    if (!response.data?.success) {
      showMessage(response.data?.detail || response.data?.error || '固定窗口失败', 'error')
      return
    }
    scanLastMessage.value = response.data?.message || '窗口固定完成'
    showMessage(scanLastMessage.value, 'success')
  } catch (error) {
    showMessage('固定窗口失败: ' + error.message, 'error')
  }
}

const applyFullScanResult = async (payload) => {
  const candidates = payload?.base_scan_candidates || []
  scanAnnotationRows.value = candidates.map((item, index) => {
    const bounds = item.bounds || { x: 0, y: 0, width: 0, height: 0 }
    return {
      enabled: true,
      region_id: item.id || `hover_${index}`,
      name: item.name || `区域_${index}`,
      function: 'unknown_action',
      clickable: true,
      needs_rescan_after_click: false,
      control_type: 'other',
      confidence: 0.9,
      bounds: {
        x: Number(bounds.x || 0),
        y: Number(bounds.y || 0),
        width: Number(bounds.width || 0),
        height: Number(bounds.height || 0),
      },
    }
  })

  scanAnnotatedImage.value = payload?.mouse_scan_meta?.annotated_image_data || ''
  const meta = payload?.mouse_scan_meta || {}
  const regionDebug = meta.region_debug || {}
  const debugParts = Object.entries(regionDebug).map(([regionId, info]) => {
    const scanned = Number(info?.scanned_points || 0)
    const after = Number(info?.candidates_after_merge || 0)
    return `${regionId}:${scanned}点/${after}候选`
  })
  scanRegionDebugSummary.value = debugParts.join(' | ')
  scanLastMessage.value = `扫描完成: base=${payload?.layer_counts?.base_scan_layer ?? 0}, control=${payload?.layer_counts?.control_layer ?? 0}, points=${meta.points_scanned || 0}`
  scanProgressPercent.value = 100
  scanProgressStage.value = 'done'
  scanProgressMessage.value = '全面扫描完成'
  await refreshScanProfiles()
}

const pollFullScanTask = async (taskId) => {
  while (true) {
    const response = await axios.get('/api/v1/rpa/wechat/ui_profile/full_scan_async/status', {
      params: { task_id: taskId },
    })
    const task = response.data?.task || {}
    scanProgressPercent.value = Number(task.progress || 0)
    scanProgressStage.value = task.stage || ''
    scanProgressMessage.value = task.message || ''

    if (task.status === 'success') {
      await applyFullScanResult(task.result || {})
      return
    }

    if (task.status === 'cancelled') {
      throw new Error(task.message || '扫描已取消')
    }

    if (task.status === 'error') {
      throw new Error(task.error || task.message || '扫描失败')
    }

    await new Promise((resolve) => setTimeout(resolve, 800))
  }
}

const cancelFullScan = async () => {
  if (!scanTaskId.value || !isScanRunning.value) {
    return
  }
  try {
    await axios.post('/api/v1/rpa/wechat/ui_profile/full_scan_async/cancel', {
      task_id: scanTaskId.value,
    })
    scanProgressMessage.value = '已发送中断请求，等待扫描线程收敛...'
    showMessage('已请求中断扫描', 'info')
  } catch (error) {
    showMessage('中断扫描失败: ' + error.message, 'error')
  }
}

const runFullScan = async () => {
  if (isScanRunning.value) {
    return
  }
  try {
    const profileName = getTemplateScopedProfileName()
    isScanRunning.value = true
    scanProgressPercent.value = 0
    scanProgressStage.value = 'queued'
    scanProgressMessage.value = '创建扫描任务中...'
    scanRegionDebugSummary.value = ''
    scanBuiltAnnotatedImage.value = ''

    const response = await axios.post('/api/v1/rpa/wechat/ui_profile/full_scan_async/start', {
      profile_name: profileName,
      template_type: selectedTemplateType.value,
      timeout_seconds: parseInt(scanTimeoutSeconds.value),
      include_mouse_scan: true,
      include_control_layer: true,
      persist_as_baseline: true,
      use_real_mouse_scan: true,
      scan_direction: scanDirection.value,
      scan_step_x: parseInt(scanStepX.value),
      scan_step_y: parseInt(scanStepY.value),
      scan_settle_ms: parseInt(scanSettleMs.value),
    })

    if (!response.data?.success) {
      showMessage(response.data?.detail || response.data?.error || '全面扫描失败', 'error')
      return
    }

    scanTaskId.value = response.data.task_id || ''
    await pollFullScanTask(scanTaskId.value)
    showMessage('全面扫描完成', 'success')
  } catch (error) {
    if (String(error.message || '').includes('取消')) {
      scanLastMessage.value = '扫描已中断'
      showMessage('扫描已中断', 'info')
    } else {
      showMessage('全面扫描失败: ' + error.message, 'error')
    }
  } finally {
    isScanRunning.value = false
    scanTaskId.value = ''
  }
}

const runHalfHalfRecognitionPipeline = async () => {
  if (isPipelineRunning.value) return

  isPipelineRunning.value = true
  try {
    selectedLayout.value = 'half-half'
    customFrontendWidth.value = 50
    pipelineStatus.value = '1/4 注册浏览器窗口...'

    const registerResp = await axios.post('/api/v1/layout/browser/register_active')
    if (!registerResp.data?.success) {
      pipelineStatus.value = '失败：浏览器窗口未注册'
      showMessage(registerResp.data?.error || '请先聚焦浏览器后重试', 'error')
      return
    }

    pipelineStatus.value = '2/4 应用浏览器/微信各半布局...'
    const layoutResp = await axios.post('/api/v1/layout/arrange_layout', {
      layout: 'half-half',
      frontendWidthPercent: 50,
      useMargins: true,
    })
    if (!layoutResp.data?.success) {
      pipelineStatus.value = '失败：布局设置错误'
      showMessage(layoutResp.data?.error || '布局失败', 'error')
      return
    }

    const wechatPos = layoutResp.data?.positions?.wechat
    if (!wechatPos) {
      pipelineStatus.value = '失败：未获取微信窗口坐标'
      showMessage('布局返回中缺少微信窗口位置数据', 'error')
      return
    }

    scanLockWidth.value = Number(wechatPos.width || scanLockWidth.value)
    scanLockHeight.value = Number(wechatPos.height || scanLockHeight.value)
    scanLockX.value = Number(wechatPos.x || scanLockX.value)
    scanLockY.value = Number(wechatPos.y || scanLockY.value)

    pipelineStatus.value = '3/4 固定微信窗口...'
    await runFixWindowForScan()

    pipelineStatus.value = '4/4 真实鼠标扫描识别中...'
    await runFullScan()

    pipelineStatus.value = `完成：半屏布局+识别成功，候选区域 ${scanAnnotationRows.value.length} 个`
  } catch (error) {
    pipelineStatus.value = `失败：${error.message}`
    showMessage('流程失败: ' + error.message, 'error')
  } finally {
    isPipelineRunning.value = false
  }
}

const generateAnnotationJsonFromRows = () => {
  const rows = scanAnnotationRows.value
    .filter((row) => row.enabled)
    .map((row) => ({
      region_id: row.region_id,
      name: row.name,
      function: row.function,
      clickable: !!row.clickable,
      needs_rescan_after_click: !!row.needs_rescan_after_click,
      control_type: row.control_type || 'other',
      confidence: Number(row.confidence || 0.9),
      bounds: {
        x: Number(row.bounds?.x || 0),
        y: Number(row.bounds?.y || 0),
        width: Number(row.bounds?.width || 0),
        height: Number(row.bounds?.height || 0),
      },
    }))

  annotationJsonText.value = JSON.stringify(rows, null, 2)
  showMessage(`已生成构建输入JSON，共 ${rows.length} 条`, 'success')
}

const runBuildProfileFromRows = async () => {
  generateAnnotationJsonFromRows()
  await runBuildProfile()
}

const toAnnotationRowsFromCandidates = (candidates = []) => {
  return (candidates || []).map((item, index) => {
    const bounds = item?.bounds || {}
    return {
      enabled: true,
      region_id: item?.id || item?.region_id || `manual_${index}`,
      name: item?.name || `手动候选_${index + 1}`,
      function: item?.function || 'unknown_action',
      clickable: item?.clickable_candidate !== false,
      needs_rescan_after_click: !!item?.needs_rescan_after_click,
      control_type: item?.type || item?.control_type || 'other',
      confidence: Number(item?.confidence || 0.9),
      bounds: {
        x: Number(bounds.x || 0),
        y: Number(bounds.y || 0),
        width: Number(bounds.width || 0),
        height: Number(bounds.height || 0),
      },
    }
  })
}

const stopManualScanPolling = () => {
  if (manualScanPollTimer.value) {
    clearInterval(manualScanPollTimer.value)
    manualScanPollTimer.value = null
  }
}

const pollManualScanStatus = async () => {
  if (!manualScanSessionId.value || !isManualScanRunning.value) {
    return
  }

  try {
    const response = await axios.get('/api/v1/rpa/wechat/ui_profile/manual_scan/status', {
      params: { session_id: manualScanSessionId.value },
    })
    if (!response.data?.success) {
      return
    }

    const session = response.data?.session || {}
    manualScanCaptures.value = Number(session.captures || 0)
    manualScanRawRects.value = Number(session.raw_rects || 0)
    manualScanCandidateCount.value = Number(session.candidate_count || 0)

    const status = String(session.status || 'running')
    if (status === 'running' || status === 'starting') {
      manualScanStatus.value = `手动扫描进行中（后台监听${session.hotkey_listener_active ? '已开启' : '准备中'}）：请在微信窗口按空格采样，回车结束，ESC退出`
      return
    }

    if (status === 'finished') {
      manualScanStatus.value = '检测到回车结束，正在汇总预览...'
      if (!manualScanFinalizing.value) {
        manualScanFinalizing.value = true
        await finishManualScan()
        manualScanFinalizing.value = false
      }
      return
    }

    if (status === 'aborted') {
      stopManualScanPolling()
      isManualScanRunning.value = false
      const sid = manualScanSessionId.value
      manualScanSessionId.value = ''
      manualScanStatus.value = '已检测到ESC退出（未保存）'
      showMessage(`会话 ${sid} 已退出（未保存）`, 'info')
      return
    }

    if (status === 'error') {
      stopManualScanPolling()
      isManualScanRunning.value = false
      const sid = manualScanSessionId.value
      manualScanSessionId.value = ''
      manualScanStatus.value = `会话异常: ${session.last_error || 'unknown'}`
      showMessage(`手动扫描异常: ${session.last_error || 'unknown'}（会话 ${sid}）`, 'error')
    }
  } catch (error) {
    // 轮询容错，不打断流程
    console.warn('手动扫描状态轮询失败:', error)
  }
}

const startManualScan = async () => {
  if (isManualScanRunning.value) return
  try {
    manualScanStatus.value = '启动手动扫描中...'
    stopManualScanPolling()
    manualScanFinalizing.value = false
    manualScanCoordinateFilePath.value = ''
    manualScanPointsFilePath.value = ''
    const response = await axios.post('/api/v1/rpa/wechat/ui_profile/manual_scan/start', {
      profile_name: getTemplateScopedProfileName(),
      template_type: selectedTemplateType.value,
      region_name: String(manualScanRegionName.value || 'chat_input').trim() || 'chat_input',
      control_type: String(manualScanControlType.value || 'button').trim() || 'button',
      diff_threshold: Number(manualScanDiffThreshold.value || 14),
      min_contour_area: Number(manualScanMinArea.value || 120),
      require_quad: !!manualScanRequireQuad.value,
      cursor_ignore_radius: Number(manualScanCursorIgnoreRadius.value || 18),
      listen_global_hotkeys: true,
    })

    if (!response.data?.success) {
      showMessage(response.data?.detail || response.data?.error || '启动手动扫描失败', 'error')
      manualScanStatus.value = '启动失败'
      return
    }

    manualScanSessionId.value = response.data.session_id || ''
    isManualScanRunning.value = true
    manualScanCaptures.value = 0
    manualScanRawRects.value = 0
    manualScanCandidateCount.value = 0
    if (response.data?.baseline_image) {
      fullWindowScreenshot.value = response.data.baseline_image
    }
    manualScanStatus.value = '手动扫描进行中：请将焦点放在微信窗口，按空格采样，回车完成，ESC退出'
    manualScanPollTimer.value = setInterval(pollManualScanStatus, 700)
    showMessage(response.data?.message || '手动扫描已启动', 'success')
  } catch (error) {
    manualScanStatus.value = '启动失败'
    showMessage('启动手动扫描失败: ' + error.message, 'error')
  }
}

const captureManualScan = async () => {
  if (!isManualScanRunning.value || !manualScanSessionId.value || isManualScanCapturing.value) return
  try {
    isManualScanCapturing.value = true
    const response = await axios.post('/api/v1/rpa/wechat/ui_profile/manual_scan/capture', {
      session_id: manualScanSessionId.value,
    })
    if (!response.data?.success) {
      showMessage(response.data?.detail || response.data?.error || '手动采样失败', 'error')
      return
    }

    manualScanCaptures.value = Number(response.data.capture_index || manualScanCaptures.value)
    manualScanCandidateCount.value = Number(response.data.candidate_count || 0)
    manualScanRawRects.value += Number(response.data.rects_detected_this_capture || 0)
    if (response.data?.annotated_image_data) {
      scanAnnotatedImage.value = response.data.annotated_image_data
    }
    scanAnnotationRows.value = toAnnotationRowsFromCandidates(response.data?.candidates || [])
    generateAnnotationJsonFromRows()
    manualScanStatus.value = `已采样 ${manualScanCaptures.value} 次，新增 ${Number(response.data.new_candidates_added || 0)} 个候选`
  } catch (error) {
    showMessage('手动采样失败: ' + error.message, 'error')
  } finally {
    isManualScanCapturing.value = false
  }
}

const finishManualScan = async () => {
  if (!isManualScanRunning.value || !manualScanSessionId.value) return
  try {
    const response = await axios.post('/api/v1/rpa/wechat/ui_profile/manual_scan/finish', {
      session_id: manualScanSessionId.value,
    })
    if (!response.data?.success) {
      showMessage(response.data?.detail || response.data?.error || '结束手动扫描失败', 'error')
      return
    }

    if (response.data?.annotated_image_data) {
      scanAnnotatedImage.value = response.data.annotated_image_data
    }
    scanAnnotationRows.value = toAnnotationRowsFromCandidates(response.data?.candidates || [])
    generateAnnotationJsonFromRows()

    manualScanCaptures.value = Number(response.data.captures || manualScanCaptures.value)
    manualScanCandidateCount.value = Number(response.data.candidate_count || 0)
    manualScanCoordinateFilePath.value = response.data.coordinate_file_path || ''
    manualScanPointsFilePath.value = response.data.points_file_path || ''

    const coordFile = manualScanCoordinateFilePath.value ? `，坐标文件: ${manualScanCoordinateFilePath.value}` : ''
    const pointsFile = manualScanPointsFilePath.value ? `，点位文件: ${manualScanPointsFilePath.value}` : ''
    scanLastMessage.value = `手动扫描完成，候选 ${manualScanCandidateCount.value} 个${coordFile}${pointsFile}`

    stopManualScanPolling()
    isManualScanRunning.value = false
    manualScanSessionId.value = ''
    manualScanStatus.value = '手动扫描已完成'
    showMessage(response.data?.message || '手动扫描完成', 'success')
  } catch (error) {
    showMessage('结束手动扫描失败: ' + error.message, 'error')
  }
}

const abortManualScan = async () => {
  if (!isManualScanRunning.value || !manualScanSessionId.value) return
  try {
    await axios.post('/api/v1/rpa/wechat/ui_profile/manual_scan/abort', {
      session_id: manualScanSessionId.value,
    })
    showMessage('已退出手动扫描（未保存）', 'info')
  } catch (error) {
    showMessage('退出手动扫描失败: ' + error.message, 'error')
  } finally {
    stopManualScanPolling()
    isManualScanRunning.value = false
    manualScanSessionId.value = ''
    manualScanStatus.value = '已退出（未保存）'
  }
}

const runBuildProfile = async () => {
  try {
    const profileName = getTemplateScopedProfileName()
    const annotations = JSON.parse(annotationJsonText.value)
    const response = await axios.post('/api/v1/rpa/wechat/ui_profile/build', {
      profile_name: profileName,
      strict_window_match: true,
      annotations,
    })
    if (!response.data?.success) {
      showMessage(response.data?.detail || response.data?.error || '构建配置失败', 'error')
      return
    }

    scanLastMessage.value = `配置构建完成: stable=${response.data?.stable_element_count ?? 0}`
    try {
      const previewResp = await axios.get('/api/v1/rpa/wechat/ui_profile/annotated_preview', {
        params: { profile_name: profileName },
      })
      if (previewResp.data?.success && previewResp.data?.screenshot) {
        scanBuiltAnnotatedImage.value = previewResp.data.screenshot
      }
    } catch (previewError) {
      console.warn('获取构建后标注确认图失败:', previewError)
      scanBuiltAnnotatedImage.value = ''
    }
    await refreshScanProfiles()
    showMessage('配置构建完成，已生成标注确认图', 'success')
  } catch (error) {
    showMessage('构建配置失败，请检查构建输入JSON格式: ' + error.message, 'error')
  }
}

const refreshScanProfiles = async () => {
  try {
    const response = await axios.get('/api/v1/rpa/wechat/ui_profile/list')
    if (!response.data?.success) {
      scanProfilesSummary.value = '读取失败'
      return
    }
    const names = (response.data?.profiles || []).map((item) => `${item.profile_name}(${item.status})`)
    scanProfilesSummary.value = names.length ? names.join(', ') : '无'
  } catch {
    scanProfilesSummary.value = '读取异常'
  }
}

const exportCurrentProfile = async () => {
  try {
    const profileName = getTemplateScopedProfileName()
    const response = await axios.get('/api/v1/rpa/wechat/ui_profile/export', {
      params: { profile_name: profileName },
    })
    if (!response.data?.success) {
      showMessage(response.data?.detail || response.data?.error || '导出失败', 'error')
      return
    }

    const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${profileName}.json`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
    showMessage('导出成功', 'success')
  } catch (error) {
    showMessage('导出失败: ' + error.message, 'error')
  }
}

const importProfileFile = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return

  try {
    const text = await file.text()
    const parsed = JSON.parse(text)
    const profileName = parsed.profile_name || scanProfileName.value
    const profile = parsed.profile || parsed

    const response = await axios.post('/api/v1/rpa/wechat/ui_profile/import', {
      profile_name: profileName,
      profile,
    })

    if (!response.data?.success) {
      showMessage(response.data?.detail || response.data?.error || '导入失败', 'error')
      return
    }

    scanProfileName.value = profileName
    await refreshScanProfiles()
    scanLastMessage.value = `已导入配置: ${profileName}`
    showMessage('导入成功', 'success')
  } catch (error) {
    showMessage('导入失败: ' + error.message, 'error')
  } finally {
    event.target.value = ''
  }
}

const loadSavedRegionAnnotationDraft = async () => {
  const finalProfileName = `${scanProfileName.value}_${selectedTemplateType.value}`
  try {
    const response = await axios.get('/api/v1/rpa/wechat/ui_profile/export', {
      params: { profile_name: finalProfileName },
    })
    if (!response.data?.success || !response.data?.profile) {
      return { loaded: false, count: 0 }
    }

    const profile = response.data.profile || {}
    const savedRegions = profile.regions || {}
    let restoredCount = 0

    regionAnnotationSteps.value.forEach((step) => {
      const region = savedRegions[step.id] || {}
      const bounds = region.bounds || null
      if (bounds && Number(bounds.width || 0) > 0 && Number(bounds.height || 0) > 0) {
        step.bounds = {
          x: Number(bounds.x || 0),
          y: Number(bounds.y || 0),
          width: Number(bounds.width || 0),
          height: Number(bounds.height || 0),
        }
        restoredCount += 1
      } else {
        step.bounds = null
      }
    })

    return { loaded: restoredCount > 0, count: restoredCount }
  } catch {
    return { loaded: false, count: 0 }
  }
}

const startRegionAnnotation = async () => {
  isRegionAnnotationActive.value = true
  currentAnnotationStep.value = 0
  isRegionSaveInProgress.value = false
  regionAnnotationBaselineReady.value = false
  regionAnnotationBaselineTemplate.value = selectedTemplateType.value
  regionSetupCompletion.value = {
    visible: false,
    profileName: '',
    templateType: selectedTemplateType.value,
  }
  manualRegionAnnotation.value.active = false
  manualRegionAnnotation.value.firstPoint = null
  manualRegionAnnotation.value.secondPoint = null
  regionAnnotationSteps.value.forEach((step) => {
    step.bounds = null
  })

  const restored = await loadSavedRegionAnnotationDraft()
  if (restored.loaded) {
    const firstUnmarked = regionAnnotationSteps.value.findIndex((step) => !step.bounds)
    currentAnnotationStep.value = firstUnmarked < 0 ? regionAnnotationSteps.value.length : firstUnmarked
    
    if (restored.count === regionAnnotationSteps.value.length) {
      // 所有区域都已标注完成，显示预览
      const finalProfileName = `${scanProfileName.value}_${selectedTemplateType.value}`
      try {
        const screenshotResponse = await axios.post('/api/v1/rpa/wechat/generate_annotated_screenshot', {
          profile_name: finalProfileName
        })
        if (screenshotResponse.data.success) {
          regionSetupCompletion.value = {
            visible: true,
            profileName: finalProfileName,
            templateType: selectedTemplateType.value,
            screenshot: screenshotResponse.data.screenshot,
          }
          isRegionAnnotationActive.value = false // 停止标注流程，显示预览
          showMessage(`已加载完整的区域配置（${restored.count}/5），显示预览。如需修改请点击"重新标注"`, 'success')
          return
        }
      } catch (screenshotError) {
        console.warn('生成标注截图失败:', screenshotError)
      }
    }
    
    showMessage(`已恢复已保存区域配置（${restored.count}/5），可继续标注或直接保存`, 'success')
  }
}

const resetManualRegionPoints = () => {
  manualRegionAnnotation.value.firstPoint = null
  manualRegionAnnotation.value.secondPoint = null
}

const cancelManualRegionAnnotation = () => {
  manualRegionAnnotation.value.active = false
  manualRegionAnnotation.value.firstPoint = null
  manualRegionAnnotation.value.secondPoint = null
}

const onManualRegionImageLoad = (event) => {
  const img = event?.target
  if (!img) return
  manualRegionImageMetrics.value = {
    renderedWidth: Number(img.clientWidth || 0),
    renderedHeight: Number(img.clientHeight || 0),
    naturalWidth: Number(img.naturalWidth || 0),
    naturalHeight: Number(img.naturalHeight || 0),
  }
}

const finalizeManualRegionSelection = () => {
  const first = manualRegionAnnotation.value.firstPoint
  const second = manualRegionAnnotation.value.secondPoint
  const idx = Number(manualRegionAnnotation.value.regionIndex)
  const step = regionAnnotationSteps.value[idx]
  if (!first || !second || !step) return

  const x1 = Math.min(Number(first.x || 0), Number(second.x || 0))
  const y1 = Math.min(Number(first.y || 0), Number(second.y || 0))
  const x2 = Math.max(Number(first.x || 0), Number(second.x || 0))
  const y2 = Math.max(Number(first.y || 0), Number(second.y || 0))

  const relativeBounds = {
    x: Math.round(x1),
    y: Math.round(y1),
    width: Math.max(1, Math.round(x2 - x1)),
    height: Math.max(1, Math.round(y2 - y1)),
  }
  const absoluteBounds = {
    x: Math.round(Number(windowPosition.value.x || 0) + relativeBounds.x),
    y: Math.round(Number(windowPosition.value.y || 0) + relativeBounds.y),
    width: relativeBounds.width,
    height: relativeBounds.height,
  }

  step.bounds = absoluteBounds
  currentAnnotationStep.value += 1
  manualRegionAnnotation.value.active = false
  manualRegionAnnotation.value.firstPoint = null
  manualRegionAnnotation.value.secondPoint = null

  if (currentAnnotationStep.value >= regionAnnotationSteps.value.length) {
    showMessage('5个区域已全部手动标注，可点击“完成并保存区域配置”', 'success')
  } else {
    showMessage(`区域 ${step.name} 标注完成，继续下一个区域`, 'success')
  }
}

const onManualRegionImageClick = (event) => {
  if (!manualRegionAnnotation.value.active) return
  const img = event?.target
  if (!img) return
  const rect = img.getBoundingClientRect()
  const metrics = manualRegionImageMetrics.value
  if (!rect.width || !rect.height || !metrics.naturalWidth || !metrics.naturalHeight) return

  const rawX = event.clientX - rect.left
  const rawY = event.clientY - rect.top
  const x = Math.max(0, Math.min(metrics.naturalWidth, Math.round((rawX / rect.width) * metrics.naturalWidth)))
  const y = Math.max(0, Math.min(metrics.naturalHeight, Math.round((rawY / rect.height) * metrics.naturalHeight)))

  if (!manualRegionAnnotation.value.firstPoint) {
    manualRegionAnnotation.value.firstPoint = { x, y }
    showMessage('已记录第一点（左上角），请继续点击第二点（右下角）', 'info')
    return
  }

  manualRegionAnnotation.value.secondPoint = { x, y }
  finalizeManualRegionSelection()
}

const annotateCurrentRegion = async () => {
  const step = regionAnnotationSteps.value[currentAnnotationStep.value]
  if (!step) return

  try {
    const needsNewBaseline =
      !regionAnnotationBaselineReady.value ||
      regionAnnotationBaselineTemplate.value !== selectedTemplateType.value ||
      !fullWindowScreenshot.value

    if (needsNewBaseline) {
      saveWeChatWindowPreset(true)
      await ensureWeChatWindowLockedBeforeActivate()
      await axios.post('/api/v1/layout/wechat/activate')
      await captureFullWindow(true)
      regionAnnotationBaselineReady.value = true
      regionAnnotationBaselineTemplate.value = selectedTemplateType.value
      showMessage(`已获取${selectedTemplateType.value === 'chat' ? '聊天界面' : '联系人界面'}基准图，后续区域将复用该基准图`, 'success')
    }

    manualRegionAnnotation.value = {
      active: true,
      regionIndex: currentAnnotationStep.value,
      regionName: step.name,
      firstPoint: null,
      secondPoint: null,
    }
    showMessage(`请在截图上为“${step.name}”点击左上角和右下角`, 'info')
  } catch (error) {
    showMessage('标注失败: ' + error.message, 'error')
  }
}

const skipCurrentRegion = () => {
  currentAnnotationStep.value += 1
  if (currentAnnotationStep.value >= regionAnnotationSteps.value.length) {
    finishRegionAnnotation()
  }
}

const finishRegionAnnotation = async () => {
  if (isRegionSaveInProgress.value) return

  try {
    isRegionSaveInProgress.value = true
    const finalProfileName = `${scanProfileName.value}_${selectedTemplateType.value}`
    const regions = {}
    regionAnnotationSteps.value.forEach((step) => {
      if (step.bounds) {
        regions[step.id] = {
          name: step.name,
          bounds: step.bounds,
          description: step.description,
        }
      }
    })

    const response = await axios.post('/api/v1/rpa/wechat/ui_profile/import', {
      profile_name: finalProfileName,
      profile: {
        profile_name: finalProfileName,
        template_type: selectedTemplateType.value,
        status: 'regions_ready',
        updated_at: new Date().toISOString(),
        window_lock: {
          x: Number(windowPosition.value.x || 0),
          y: Number(windowPosition.value.y || 0),
          width: Number(windowSize.value.width || 0),
          height: Number(windowSize.value.height || 0),
        },
        regions,
        layers: {
          base_scan_layer: [],
          annotation_layer: [],
          control_layer: [],
          geometry_layer: {},
        },
        execution: {
          rescan_region_ids: [],
          rescan_required_on_click: false,
        },
        stable_elements: [],
      },
    })
    if (!response.data?.success) {
      showMessage(response.data?.detail || response.data?.error || '保存配置失败', 'error')
      return
    }

    isRegionAnnotationActive.value = false
    currentAnnotationStep.value = 0
    await refreshScanProfiles()
    
    // 生成标注截图
    try {
      const screenshotResponse = await axios.post('/api/v1/rpa/wechat/generate_annotated_screenshot', {
        profile_name: finalProfileName
      })
      if (screenshotResponse.data.success) {
        regionSetupCompletion.value = {
          visible: true,
          profileName: finalProfileName,
          templateType: selectedTemplateType.value,
          screenshot: screenshotResponse.data.screenshot,
        }
      } else {
        regionSetupCompletion.value = {
          visible: true,
          profileName: finalProfileName,
          templateType: selectedTemplateType.value,
          screenshot: null,
        }
      }
    } catch (screenshotError) {
      console.warn('生成标注截图失败:', screenshotError)
      regionSetupCompletion.value = {
        visible: true,
        profileName: finalProfileName,
        templateType: selectedTemplateType.value,
        screenshot: null,
      }
    }
    
    showMessage('本次区域设置已完成（仅保存区域，不会自动扫描）。请手动点击“进入后续扫描程序设置”。', 'success')
  } catch (error) {
    showMessage('保存配置失败: ' + error.message, 'error')
  } finally {
    isRegionSaveInProgress.value = false
  }
}

const restartRegionAnnotation = () => {
  // 清除预览状态，重新开始标注流程
  regionSetupCompletion.value = {
    visible: false,
    profileName: '',
    templateType: selectedTemplateType.value,
  }
  
  // 直接开始新的标注流程，不加载已保存配置
  isRegionAnnotationActive.value = true
  currentAnnotationStep.value = 0
  isRegionSaveInProgress.value = false
  regionAnnotationBaselineReady.value = false
  regionAnnotationBaselineTemplate.value = selectedTemplateType.value
  manualRegionAnnotation.value.active = false
  manualRegionAnnotation.value.firstPoint = null
  manualRegionAnnotation.value.secondPoint = null
  regionAnnotationSteps.value.forEach((step) => {
    step.bounds = null
  })
  
  showMessage('已清除之前的标注，开始新的标注流程', 'info')
}

const goToScanProgramSetup = () => {
  activeGroup.value = 'layout'
}

const cancelRegionAnnotation = () => {
  isRegionAnnotationActive.value = false
  currentAnnotationStep.value = 0
  isRegionSaveInProgress.value = false
  regionAnnotationBaselineReady.value = false
  manualRegionAnnotation.value.active = false
  manualRegionAnnotation.value.firstPoint = null
  manualRegionAnnotation.value.secondPoint = null
  regionAnnotationSteps.value.forEach((step) => {
    step.bounds = null
  })
}

// 截图消息区域
const captureMessageArea = async () => {
  try {
    const response = await axios.post('/api/v1/rpa/wechat/capture_message_area')
    if (response.data.success && response.data.screenshot) {
      messageScreenshot.value = response.data.screenshot
      showMessage(response.data.message || '截图消息区域成功', 'success')
    } else {
      showMessage(response.data.message || '截图消息区域失败', 'error')
    }
  } catch (error) {
    console.error('截图消息区域失败:', error)
    showMessage('截图消息区域失败: ' + error.message, 'error')
  }
}

// 截图完整窗口
const captureFullWindow = async (silent = false) => {
  try {
    const response = await axios.post('/api/v1/rpa/wechat/capture_full_window')
    if (response.data.success && response.data.screenshot) {
      fullWindowScreenshot.value = response.data.screenshot
      if (!silent) {
        showMessage(response.data.message || '截图完整窗口成功', 'success')
      }
    } else {
      if (!silent) {
        showMessage(response.data.message || '截图完整窗口失败', 'error')
      }
    }
  } catch (error) {
    console.error('截图完整窗口失败:', error)
    if (!silent) {
      showMessage('截图完整窗口失败: ' + error.message, 'error')
    }
  }
}

// 消息操作
const sendWeChatMessage = async () => {
  try {
    const response = await axios.post('/api/v1/rpa/wechat/send_message', {
      message: messageContent.value
    })
    if (response.data.success) {
      showMessage(response.data.message, 'success')
    } else {
      showMessage(response.data.message || '发送消息失败', 'error')
    }
  } catch (error) {
    console.error('发送消息失败:', error)
    showMessage('发送消息失败: ' + error.message, 'error')
  }
}

const getLatestMessages = async () => {
  try {
    const response = await axios.post('/api/v1/rpa/wechat/messages/latest', { count: 10 })
    if (response.data.success) {
      latestMessages.value = response.data.messages
      showMessage('获取最新消息成功', 'success')
    } else {
      showMessage(response.data.message || '获取最新消息失败', 'error')
    }
  } catch (error) {
    console.error('获取最新消息失败:', error)
    showMessage('获取最新消息失败: ' + error.message, 'error')
  }
}

// 联系人操作
const searchContact = async () => {
  try {
    const response = await axios.post('/api/v1/rpa/wechat/contacts/search', {}, {
      params: { keyword: contactKeyword.value }
    })
    if (response.data.success) {
      contacts.value = [response.data.contact]
      selectedContactInfo.value = formatJson(response.data.contact || {})
      showMessage('搜索联系人成功', 'success')
    } else {
      showMessage(response.data.message || '搜索联系人失败', 'error')
    }
  } catch (error) {
    console.error('搜索联系人失败:', error)
    showMessage('搜索联系人失败: ' + error.message, 'error')
  }
}

const getContacts = async () => {
  try {
    const response = await axios.post('/api/v1/rpa/wechat/contacts/list', {}, {
      params: { max_count: 100 }
    })
    if (response.data.success) {
      contacts.value = response.data.contacts
      showMessage('获取联系人列表成功', 'success')
    } else {
      showMessage(response.data.message || '获取联系人列表失败', 'error')
    }
  } catch (error) {
    console.error('获取联系人列表失败:', error)
    showMessage('获取联系人列表失败: ' + error.message, 'error')
  }
}

// AT-SPI操作
const clickControl = async () => {
  try {
    const response = await axios.post('/api/v1/rpa/atspi/click_control', {}, {
      params: { control_name: controlName.value }
    })
    if (response.data.success) {
      atspiResult.value = response.data.message
      showMessage(response.data.message, 'success')
    } else {
      showMessage(response.data.message || '点击控件失败', 'error')
    }
  } catch (error) {
    console.error('点击控件失败:', error)
    showMessage('点击控件失败: ' + error.message, 'error')
  }
}

const inputTextToControl = async () => {
  try {
    const response = await axios.post('/api/v1/rpa/atspi/input_text', {}, {
      params: {
        control_name: controlName.value,
        text: '示例文本'
      }
    })
    if (response.data.success) {
      atspiResult.value = response.data.message
      showMessage(response.data.message, 'success')
    } else {
      showMessage(response.data.message || '输入文本到控件失败', 'error')
    }
  } catch (error) {
    console.error('输入文本到控件失败:', error)
    showMessage('输入文本到控件失败: ' + error.message, 'error')
  }
}

const getTextFromControl = async () => {
  try {
    const response = await axios.post('/api/v1/rpa/atspi/get_text', {}, {
      params: { control_name: controlName.value }
    })
    if (response.data.success) {
      atspiResult.value = response.data.message + ': ' + response.data.text
      showMessage(response.data.message, 'success')
    } else {
      showMessage(response.data.message || '从控件获取文本失败', 'error')
    }
  } catch (error) {
    console.error('从控件获取文本失败:', error)
    showMessage('从控件获取文本失败: ' + error.message, 'error')
  }
}

const fetchATSPIControlTreeSnapshot = async (autoActivate = false, applyFilters = false) => {
  try {
    if (autoActivate) {
      saveWeChatWindowPreset(true)
      await ensureWeChatWindowLockedBeforeActivate()
      await axios.post('/api/v1/layout/wechat/activate')
      await new Promise((resolve) => setTimeout(resolve, 1200))
    }
    const roleFilter = applyFilters ? atspiRoleFilter.value : ''
    const nameFilter = applyFilters ? atspiNameFilter.value : ''
    const hasNameFilter = !!String(nameFilter || '').trim()
    const useNoFilterFullMode = !applyFilters
    const params = {
      role_filter: roleFilter,
      name_filter: nameFilter,
      max_nodes: useNoFilterFullMode ? 0 : Number(atspiMaxNodes.value || 5000),
      max_depth: useNoFilterFullMode ? -1 : Number(atspiMaxDepth.value ?? -1),
      auto_refresh_tree: useNoFilterFullMode ? false : !!atspiAutoRefreshTree.value,
      refresh_rounds: useNoFilterFullMode ? 1 : Number(atspiRefreshRounds.value || 1),
      refresh_interval_ms: useNoFilterFullMode ? 0 : Number(atspiRefreshIntervalMs.value || 0),
      auto_activate: false,
      prefer_tree: true,
      deep_search: true,
      include_common_keywords: false,
      require_keyword_match: hasNameFilter,
      deduplicate: false,
      export_json: true,
    }

    let response = null
    let lastError = null
    for (const endpoint of ['/api/v1/rpa/atspi/tree_snapshot', '/api/v1/atspi/tree_snapshot']) {
      try {
        response = await axios.post(endpoint, {}, { params })
        if (response?.data) break
      } catch (err) {
        lastError = err
      }
    }
    if (!response) {
      throw lastError || new Error('AT-SPI树快照接口不可用')
    }

    if (response.data.success) {
      atspiSnapshotNodes.value = response.data.nodes || []
      const refresh = response.data.filters?.tree_refresh || {}
      const sourceStatus = response.data.filters?.data_source_status || {}
      const treeSourceNodes = sourceStatus?.tree_snapshot?.nodes ?? '-'
      const controlSourceNodes = sourceStatus?.control_snapshot?.nodes ?? '-'
      const managerUiNodes = sourceStatus?.manager_get_ui_elements?.nodes ?? '-'
      const engineUiNodes = sourceStatus?.engine_get_ui_elements?.nodes ?? '-'
      const engineTraverseNodes = sourceStatus?.engine_traverse_control_tree?.nodes ?? '-'
      atspiSnapshotSummary.value = `快照模式: ${applyFilters ? '按过滤条件' : '原始无过滤'}\n返回节点: ${response.data.count}\n原始模式: ${response.data.filters?.raw_mode || '-'}\n树尝试: ${response.data.filters?.tree_attempted ? '是' : '否'} / 树节点: ${response.data.filters?.tree_nodes_count ?? '-'}\n刷新: ${refresh.enabled ? '开启' : '关闭'} / 轮次=${refresh.refresh_rounds ?? '-'} / 最优轮次=${refresh.best_round ?? '-'} / 最优节点=${refresh.best_nodes ?? '-'} / 可定位=${refresh.best_positioned_nodes ?? '-'}\n数据源节点: tree=${treeSourceNodes}, control=${controlSourceNodes}, manager_ui=${managerUiNodes}, engine_ui=${engineUiNodes}, engine_traverse=${engineTraverseNodes}\n过滤条件: role=${response.data.filters?.role_filter || '-'}, name=${response.data.filters?.name_filter || '-'}, max_nodes=${response.data.filters?.max_nodes ?? '-'}, max_depth=${response.data.filters?.max_depth ?? '-'}\n自动激活: ${response.data.activated ? '是' : '否'}\n导出文件: ${response.data.export_file || '-'}`
      showMessage(response.data.message || 'AT-SPI树快照成功', 'success')
    } else {
      atspiSnapshotNodes.value = []
      atspiSnapshotSummary.value = response.data.message || 'AT-SPI树快照失败'
      showMessage(response.data.message || 'AT-SPI树快照失败', 'error')
    }
  } catch (error) {
    console.error('AT-SPI树快照失败:', error)
    const detail = error?.response?.data?.detail || error.message
    showMessage('AT-SPI树快照失败: ' + detail, 'error')
  }
}

const extractOCRText = async () => {
  const path = String(ocrImagePath.value || '').trim()
  if (!path) {
    showMessage('请先输入OCR图片路径', 'error')
    return
  }
  try {
    const response = await axios.post('/api/v1/rpa/ocr/extract_text', {}, {
      params: { image_path: path }
    })
    ocrTextResult.value = formatJson(response.data)
    if (response.data?.success) {
      showMessage('OCR识别成功', 'success')
      return
    }
    showMessage(response.data?.message || 'OCR识别失败', 'error')
  } catch (error) {
    showMessage('OCR识别失败: ' + error.message, 'error')
  }
}

const validateATSPIBoundsClick = async (node) => {
  try {
    atspiClickValidationResult.value = ''
    atspiClickBeforeImage.value = ''
    atspiClickAfterImage.value = ''
    const bounds = node?.bounds || {}
    const width = Number(bounds.width || 0)
    const height = Number(bounds.height || 0)
    if (width <= 0 || height <= 0) {
      atspiClickValidationResult.value = formatJson({
        success: false,
        message: '该节点没有可点击边界（width/height=0），请选择具体控件节点',
        node: {
          role: node?.role || '',
          name: node?.name || '',
          path: node?.path || ''
        }
      })
      showMessage('该节点不可点击，请选择有尺寸的控件节点', 'error')
      return
    }

    const params = {
      x: bounds.x || 0,
      y: bounds.y || 0,
      width,
      height,
      precise: true,
      capture_validation: true
    }

    let response = null
    let lastError = null
    for (const endpoint of ['/api/v1/atspi/click_by_bounds', '/api/v1/rpa/atspi/click_by_bounds']) {
      try {
        response = await axios.post(endpoint, {}, { params })
        if (response?.data) break
      } catch (err) {
        lastError = err
      }
    }
    if (!response) {
      throw lastError || new Error('AT-SPI边界点击接口不可用')
    }

    atspiClickValidationResult.value = formatJson(response.data)
    atspiClickBeforeImage.value = response.data?.validation_images?.before_data || ''
    atspiClickAfterImage.value = response.data?.validation_images?.after_data || ''
    if (response.data.success) {
      showMessage(`节点点击验证成功: ${node?.role || 'unknown'}`, 'success')
    } else {
      showMessage(response.data.message || '节点点击验证失败', 'error')
    }
  } catch (error) {
    console.error('节点点击验证失败:', error)
    atspiClickValidationResult.value = String(error)
    const detail = error?.response?.data?.detail || error.message
    showMessage('AT-SPI边界点击验证失败: ' + detail, 'error')
  }
}

const humanizedInput = async () => {
  try {
    const response = await axios.post('/api/v1/rpa/humanized/input', {}, {
      params: { text: inputText.value }
    })
    if (response.data.success) {
      showMessage('拟人化输入成功', 'success')
    } else {
      showMessage(response.data.message || '拟人化输入失败', 'error')
    }
  } catch (error) {
    console.error('拟人化输入失败:', error)
    showMessage('拟人化输入失败: ' + error.message, 'error')
  }
}

const fetchUIElements = async () => {
  try {
    const response = await axios.post('/api/v1/rpa/wechat/fetch_ui_elements')
    if (response.data.success) {
      uiElements.value = response.data.elements
      showMessage('获取界面元素成功', 'success')
    } else {
      showMessage(response.data.message || '获取界面元素失败', 'error')
    }
  } catch (error) {
    console.error('获取界面元素失败:', error)
    showMessage('获取界面元素失败: ' + error.message, 'error')
  }
}

const analyzeUITree = async () => {
  try {
    const response = await axios.post('/api/v1/rpa/wechat/analyze_ui_tree')
    if (response.data.success) {
      uiTreeAnalysis.value = response.data.analysis
      showMessage('分析控件树成功', 'success')
    } else {
      showMessage(response.data.message || '分析控件树失败', 'error')
    }
  } catch (error) {
    console.error('分析控件树失败:', error)
    showMessage('分析控件树失败: ' + error.message, 'error')
  }
}

// 分析界面元素
const analyzeUIElements = async () => {
  try {
    const response = await axios.post('/api/v1/rpa/wechat/analyze_ui_elements')
    if (response.data.success) {
      analyzedElements.value = response.data.elements
      showMessage(`发现 ${response.data.elements.length} 个界面元素`, 'success')
    } else {
      showMessage(response.data.message || '分析界面元素失败', 'error')
    }
  } catch (error) {
    console.error('分析界面元素失败:', error)
    showMessage('分析界面元素失败: ' + error.message, 'error')
  }
}

// 查找所有按钮
const findAllButtons = async () => {
  try {
    const response = await axios.post('/api/v1/rpa/wechat/find_all_buttons')
    if (response.data.success) {
      allButtons.value = response.data.buttons
      showMessage(`发现 ${response.data.buttons.length} 个按钮`, 'success')
    } else {
      showMessage(response.data.message || '查找按钮失败', 'error')
    }
  } catch (error) {
    console.error('查找按钮失败:', error)
    showMessage('查找按钮失败: ' + error.message, 'error')
  }
}

// 点击界面元素
const clickElement = async (elementId) => {
  try {
    clickedElement.value = elementId
    lastClickStrategy.value = ''
    clickStrategyTrace.value = []
    lastClickTotalElapsedMs.value = 0
    const response = await axios.post('/api/v1/rpa/wechat/click_element', {}, {
      params: { element_id: elementId }
    })
    lastClickStrategy.value = response.data.strategy || ''
    clickStrategyTrace.value = response.data.trace || []
    lastClickTotalElapsedMs.value = response.data.total_elapsed_ms || 0
    if (response.data.success) {
      elementTestResult.value = response.data.message
      showMessage(response.data.message, 'success')
    } else {
      showMessage(response.data.message || '点击元素失败', 'error')
      elementTestResult.value = response.data.message
    }
  } catch (error) {
    console.error('点击元素失败:', error)
    showMessage('点击元素失败: ' + error.message, 'error')
    elementTestResult.value = '点击失败: ' + error.message
  }
}

// 标注所有UI元素
const captureAndAnnotateAllElements = async () => {
  try {
    const response = await axios.post('/api/v1/rpa/wechat/capture_and_annotate_all_elements')
    if (response.data.success) {
      fullWindowScreenshot.value = response.data.screenshot
      annotatedElements.value = response.data.elements || []
      showMessage(response.data.message || `标注完成，识别 ${annotatedElements.value.length} 个元素`, 'success')
    } else {
      showMessage(response.data.message || '标注所有UI元素失败', 'error')
    }
  } catch (error) {
    console.error('标注所有UI元素失败:', error)
    showMessage('标注所有UI元素失败: ' + error.message, 'error')
  }
}

const performMultiLayerAnnotation = async () => {
  try {
    const response = await axios.post('/api/v1/rpa/wechat/ui_profile/annotate_multi_layer', {
      profile_name: multiLayerProfileName.value,
      region_id: multiLayerRegionId.value,
      template_type: multiLayerTemplateType.value,
      include_atspi: multiLayerIncludeAtsPi.value,
      include_mouse_scan: multiLayerIncludeMouseScan.value,
      include_ocr: multiLayerIncludeOcr.value
    })
    
    if (response.data.success) {
      multiLayerResults.value = response.data
      showMessage('多层标注完成', 'success')
    } else {
      showMessage(response.data.message || '多层标注失败', 'error')
    }
  } catch (error) {
    console.error('多层标注失败:', error)
    showMessage('多层标注失败: ' + error.message, 'error')
  }
}

const selectAnnotation = (layerName, candidate) => {
  selectedAnnotation.value = {
    layer: layerName,
    bounds: candidate.bounds,
    confidence: candidate.confidence,
    source: candidate.source
  }
}

const confirmSelectedAnnotation = async () => {
  if (!selectedAnnotation.value) return
  
  try {
    const response = await axios.post('/api/v1/rpa/wechat/ui_profile/confirm_annotation', {
      profile_name: multiLayerProfileName.value,
      region_id: multiLayerRegionId.value,
      selected_layer: selectedAnnotation.value.layer,
      bounds: selectedAnnotation.value.bounds,
      confidence: selectedAnnotation.value.confidence,
      notes: annotationNotes.value
    })
    
    if (response.data.success) {
      showMessage('标注确认成功', 'success')
      selectedAnnotation.value = null
      annotationNotes.value = ''
      multiLayerResults.value = null
    } else {
      showMessage(response.data.message || '标注确认失败', 'error')
    }
  } catch (error) {
    console.error('确认标注失败:', error)
    showMessage('确认标注失败: ' + error.message, 'error')
  }
}

const cancelSelectedAnnotation = () => {
  selectedAnnotation.value = null
  annotationNotes.value = ''
}

onMounted(async () => {
  await refreshSystemStatus()
  syncBrowserWindowInfo()
  const preset = getWeChatWindowPreset()
  windowSize.value = { width: preset.width, height: preset.height }
  windowPosition.value = { x: preset.x, y: preset.y }
  scanLockWidth.value = preset.width
  scanLockHeight.value = preset.height
  scanLockX.value = preset.x
  scanLockY.value = preset.y
  loadSetupLockState()
  loadCalibratedControls()
  loadAtomicProfileId()
  loadAtomicPipelineConfig(true)
  window.addEventListener('atomic-pipeline-config-ready', handleAtomicPipelineConfigReady)
  if (Number(atomicProfileId.value || 0) > 0) {
    await loadAtomicControlLibrary()
  }
  await refreshScanProfiles()

  watch(activeGroup, (group) => {
    if (group === 'atomicControls' && hasPendingIntegratedSync.value) {
      showMessage('检测到第5步整合结果尚未应用，请先回到第5步点击“应用整合结果到已校准控件”再继续。', 'warning')
    }
    if (group === 'atomicControls' && Number(atomicProfileId.value || 0) > 0) {
      loadAtomicControlLibrary()
    }
  })

  watch(atomicProfileId, (value, oldValue) => {
    const now = Number(value || 0)
    const prev = Number(oldValue || 0)
    persistAtomicProfileId()
    if (now > 0 && now !== prev) {
      loadAtomicControlLibrary()
    }
    if (now <= 0) {
      atomicLibraryItems.value = []
      atomicLibraryLastLoadedAt.value = ''
    }
  })
})

onUnmounted(() => {
  window.removeEventListener('atomic-pipeline-config-ready', handleAtomicPipelineConfigReady)
  stopManualScanPolling()
})

</script>

<style scoped>
.rpa-test {
  padding: 20px;
}

.status-overview-card {
  margin-top: 8px;
}

.status-display {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 6px 10px;
  background: #f5f7fa;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-label {
  font-weight: 600;
  color: #495057;
}

.status-value {
  color: #6c757d;
}

.status-value.status-active {
  color: #155724;
  font-weight: 600;
}

.panel-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 12px 0 16px;
}

.tab-btn {
  border: 1px solid #cfd4da;
  background: #fff;
  color: #333;
  padding: 8px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.tab-btn.active {
  background: #007bff;
  color: #fff;
  border-color: #007bff;
}

.action-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.card {
  margin-bottom: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
}

.card-header {
  background-color: #f8f9fa;
  padding: 12px 20px;
  border-bottom: 1px solid #ddd;
}

.card-body {
  padding: 20px;
}

.row {
  display: flex;
  flex-wrap: wrap;
  margin: 0 -10px;
}

.col-md-6 {
  flex: 0 0 50%;
  max-width: 50%;
  padding: 0 10px;
  margin-bottom: 15px;
}

.btn {
  display: inline-block;
  padding: 6px 12px;
  margin-right: 8px;
  margin-bottom: 10px;
  font-size: 14px;
  font-weight: 400;
  line-height: 1.5;
  text-align: center;
  white-space: nowrap;
  vertical-align: middle;
  cursor: pointer;
  border: 1px solid transparent;
  border-radius: 4px;
  transition: color 0.15s ease-in-out, background-color 0.15s ease-in-out, border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
}

.btn-primary {
  color: #fff;
  background-color: #007bff;
  border-color: #007bff;
}

.btn-primary:hover {
  background-color: #0069d9;
  border-color: #0062cc;
}

.btn-secondary {
  color: #fff;
  background-color: #6c757d;
  border-color: #6c757d;
}

.btn-info {
  color: #fff;
  background-color: #17a2b8;
  border-color: #17a2b8;
}

.btn-success {
  color: #fff;
  background-color: #28a745;
  border-color: #28a745;
}

.btn-warning {
  color: #212529;
  background-color: #ffc107;
  border-color: #ffc107;
}

.btn-danger {
  color: #fff;
  background-color: #dc3545;
  border-color: #dc3545;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.form-group input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  margin-bottom: 10px;
  box-sizing: border-box;
}

.form-control {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box;
}

.input-row {
  display: flex;
  gap: 10px;
}

.input-row input {
  flex: 1;
  margin-bottom: 0;
}

.status-info {
  background-color: #f5f5f5;
  padding: 10px;
  border-radius: 4px;
  min-height: 60px;
}

.scan-progress-wrap {
  margin-top: 8px;
  width: 100%;
  height: 10px;
  background: #e9ecef;
  border-radius: 6px;
  overflow: hidden;
}

.scan-progress-bar {
  height: 100%;
  background: #17a2b8;
  transition: width 0.25s ease;
}

.result-box {
  background-color: #f9f9f9;
  padding: 10px;
  border-radius: 4px;
  min-height: 100px;
}

.screenshot-container {
  margin-top: 15px;
}

.screenshot-image {
  max-width: 100%;
  height: auto;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.messages-list,
.contacts-list {
  margin-top: 15px;
}

.message-item,
.contact-item {
  padding: 5px 0;
  border-bottom: 1px solid #eee;
}

.message-item:last-child,
.contact-item:last-child {
  border-bottom: none;
}

.alert {
  padding: 12px 16px;
  margin-bottom: 16px;
  border: 1px solid transparent;
  border-radius: 4px;
}

.alert-info {
  color: #0c5460;
  background-color: #d1ecf1;
  border-color: #bee5eb;
}

.element-item {
  margin: 5px 0;
  padding: 5px;
  border: 1px solid #e0e0e0;
  border-radius: 3px;
  background-color: #f9f9f9;
}

.layer-result {
  margin-bottom: 15px;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
}

.layer-result h5 {
  margin: 0 0 8px 0;
  color: #333;
}

.candidate-item {
  margin: 8px 0;
  padding: 8px;
  background: #f8f9fa;
  border-radius: 4px;
  border-left: 3px solid #007bff;
}

.error-msg {
  color: #dc3545;
  font-style: italic;
}

.checkbox-group {
  display: flex;
  gap: 15px;
  margin-top: 5px;
}

.checkbox-group label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-weight: normal;
}

.ml-2 {
  margin-left: 0.5rem;
}

.btn-sm {
  padding: 0.25rem 0.5rem;
  font-size: 0.875rem;
  line-height: 1.5;
  border-radius: 0.2rem;
}

.btn-outline-primary {
  color: #007bff;
  border-color: #007bff;
  background-color: transparent;
}

.btn-outline-primary:hover {
  color: #fff;
  background-color: #007bff;
  border-color: #007bff;
}

.btn-sm.btn-danger {
  color: #fff;
  background-color: #dc3545;
  border-color: #dc3545;
}

.trace-step {
  margin: 6px 0;
  padding: 6px 8px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  background-color: #fff;
}

.trace-line {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.trace-icon {
  min-width: 18px;
}

.trace-meta {
  color: #6c757d;
}

.trace-reason {
  margin: 4px 0 0 26px;
  color: #495057;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.annotation-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 8px;
}

.annotation-table th,
.annotation-table td {
  border: 1px solid #e0e0e0;
  padding: 6px;
  vertical-align: top;
}

.bounds-cell {
  display: grid;
  grid-template-columns: repeat(2, minmax(80px, 1fr));
  gap: 6px;
}

.tiny {
  min-width: 80px;
}

.annotation-steps {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.step-item {
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: 8px;
  background: #fff;
}

.step-item.active {
  border-color: #007bff;
  background: #f0f7ff;
}

.step-item.completed {
  border-color: #28a745;
  background: #f3fff7;
}

.step-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.step-number {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #007bff;
  color: #fff;
  text-align: center;
  line-height: 20px;
  font-size: 12px;
}

.step-description,
.step-bounds {
  margin-top: 6px;
  color: #555;
}

.step-actions {
  margin-top: 8px;
}

.section-readonly {
  pointer-events: none;
  opacity: 0.6;
}

.lock-tip {
  margin-bottom: 10px;
  padding: 8px 10px;
  background: #fff3cd;
  border: 1px solid #ffeeba;
  border-radius: 4px;
  color: #856404;
  font-size: 13px;
}

.preview-canvas {
  position: relative;
  display: inline-block;
  max-width: 100%;
}

.manual-region-canvas {
  position: relative;
  display: inline-block;
  max-width: 100%;
  margin-top: 8px;
}

.manual-region-canvas .screenshot-image {
  cursor: crosshair;
}

.overlay-box {
  position: absolute;
  border: 2px solid #ff2d2d;
  box-sizing: border-box;
  pointer-events: none;
}

.overlay-label {
  position: absolute;
  left: 0;
  top: -20px;
  background: rgba(255, 45, 45, 0.9);
  color: #fff;
  padding: 1px 6px;
  font-size: 12px;
  border-radius: 3px;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .col-md-6 {
    flex: 0 0 100%;
    max-width: 100%;
  }
}
</style>