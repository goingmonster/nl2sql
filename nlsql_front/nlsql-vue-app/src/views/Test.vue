<template>
  <div class="test-chat-page">
    <div class="card">
      <div class="chat-header">
        <div>
          <h2 class="card-title">测试问答</h2>
          <p class="page-desc">基于任务会话进行 AI 问答，自动记录历史对话</p>
        </div>
        <div class="header-actions">
          <el-tag v-if="selectedTask" type="success">任务ID: {{ selectedTask.id }}</el-tag>
          <el-tag v-if="currentSessionId" type="info">会话ID: {{ currentSessionId }}</el-tag>
          <el-button @click="openTaskDialog">{{ selectedTask ? '切换任务' : '选择任务' }}</el-button>
          <el-button type="primary" @click="startNewSession" :disabled="!selectedTask">新建会话</el-button>
        </div>
      </div>

      <div class="session-title-row">
        <el-input v-model="sessionTitle" placeholder="会话标题（可选，首次提问时使用）" clearable />
      </div>

      <div class="conversation-box" v-loading="asking">
        <div v-if="messages.length === 0" class="empty-tip">
          请选择任务并输入问题开始会话
        </div>
        <div v-for="item in messages" :key="item.localId" class="message-row" :class="item.role">
          <div class="message-bubble">
            <div class="message-role">{{ item.role === 'user' ? '我' : 'AI' }}</div>
            <div class="message-content">{{ item.content }}</div>
            <div v-if="item.role === 'assistant' && item.sql_generated" class="sql-block">
              <div class="sql-label">SQL</div>
              <pre class="sql-content">{{ item.sql_generated }}</pre>
            </div>
            <div v-if="item.role === 'assistant' && item.sql_data !== undefined && item.sql_data !== null" class="sql-data-block">
              <div class="sql-label">SQL Data</div>
              <el-table
                v-if="isTabularData(item.sql_data)"
                :data="normalizeSqlRows(item.sql_data)"
                size="small"
                border
                max-height="300"
                class="sql-table"
              >
                <el-table-column
                  v-for="col in getSqlColumns(item.sql_data)"
                  :key="col"
                  :prop="col"
                  :label="col"
                  min-width="140"
                  show-overflow-tooltip
                />
              </el-table>
              <pre v-else class="sql-content">{{ formatSqlData(item.sql_data) }}</pre>
            </div>
            <div v-if="item.role === 'assistant' && hasMessageSelectedTables(item)" class="sql-data-block">
              <div class="sql-label">Selected Tables</div>
              <div class="selected-table-list">
                <el-tag
                  v-for="table in getMessageSelectedTables(item)"
                  :key="`${table.table_id}-${table.table_name}`"
                  type="warning"
                  effect="plain"
                  class="selected-table-tag"
                >
                  {{ table.table_name || '-' }} (ID: {{ table.table_id ?? '-' }})
                </el-tag>
              </div>
              <div v-if="getSelectTableReason(item)" class="ctx-row">
                <span class="ctx-key">reason:</span>
                <span class="ctx-value">{{ getSelectTableReason(item) }}</span>
              </div>
              <div v-if="getSelectTableCandidateCount(item) !== null" class="ctx-row">
                <span class="ctx-key">candidate_count:</span>
                <span class="ctx-value">{{ getSelectTableCandidateCount(item) }}</span>
              </div>
            </div>
            <div v-if="item.role === 'assistant' && hasQueryContext(item.query_context)" class="sql-data-block">
              <div class="sql-label">Query Context</div>
              <div class="query-context-block">
                <div v-if="normalizeQueryContext(item.query_context).driver_table" class="ctx-row">
                  <span class="ctx-key">driver_table:</span>
                  <span class="ctx-value">{{ normalizeQueryContext(item.query_context).driver_table }}</span>
                </div>

                <div v-if="normalizeQueryContext(item.query_context).allowed_tables?.length" class="ctx-row">
                  <span class="ctx-key">allowed_tables:</span>
                  <div class="ctx-tag-list">
                    <el-tag
                      v-for="table in normalizeQueryContext(item.query_context).allowed_tables"
                      :key="`allowed-${table}`"
                      size="small"
                      effect="plain"
                    >
                      {{ table }}
                    </el-tag>
                  </div>
                </div>

                <div v-if="normalizeQueryContext(item.query_context).joins?.length" class="ctx-row">
                  <span class="ctx-key">joins:</span>
                  <div class="ctx-join-list">
                    <div
                      v-for="(joinItem, idx) in normalizeQueryContext(item.query_context).joins"
                      :key="`join-${idx}`"
                      class="ctx-join-item"
                    >
                      {{ joinItem.from || '-' }} -> {{ joinItem.to || '-' }}
                    </div>
                  </div>
                </div>

                <div v-if="normalizeQueryContext(item.query_context).table_usage" class="ctx-row">
                  <span class="ctx-key">table_usage:</span>
                  <pre class="sql-content">{{ formatSqlData(normalizeQueryContext(item.query_context).table_usage) }}</pre>
                </div>
              </div>
            </div>
            <div v-if="item.role === 'assistant' && hasQColumnPatch(item.q_column_patch)" class="sql-data-block">
              <div class="sql-label">Q Column Patch</div>
              <div class="query-context-block">
                <div v-if="normalizeQColumnPatch(item.q_column_patch).tables?.length" class="ctx-row">
                  <span class="ctx-key">tables:</span>
                  <div class="ctx-tag-list">
                    <el-tag
                      v-for="table in normalizeQColumnPatch(item.q_column_patch).tables"
                      :key="`patch-table-${table}`"
                      size="small"
                      effect="plain"
                    >
                      {{ table }}
                    </el-tag>
                  </div>
                </div>

                <div v-if="normalizeQColumnPatch(item.q_column_patch).column_patches" class="ctx-row">
                  <span class="ctx-key">column_patches:</span>
                  <div class="patch-list">
                    <div
                      v-for="(patchItem, tableName) in normalizeQColumnPatch(item.q_column_patch).column_patches"
                      :key="`patch-${tableName}`"
                      class="patch-item"
                    >
                      <div class="patch-title">{{ tableName }}</div>
                      <div v-if="patchItem?.where" class="patch-line"><b>WHERE:</b> {{ patchItem.where }}</div>
                      <div v-if="patchItem?.reason" class="patch-line"><b>REASON:</b> {{ patchItem.reason }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="item.created_at" class="message-time">{{ formatDate(item.created_at) }}</div>
          </div>
        </div>
      </div>

      <div class="ask-row">
        <el-input
          v-model="question"
          type="textarea"
          :rows="3"
          placeholder="请输入你的问题"
          @keydown.ctrl.enter.prevent="handleAsk"
        />
        <el-button type="primary" class="send-btn" :loading="asking" @click="handleAsk">发送</el-button>
      </div>
    </div>

    <el-dialog v-model="taskDialogVisible" title="选择任务" width="680px">
      <el-select v-model="taskKeywordId" filterable clearable placeholder="搜索并选择任务" style="width: 100%" @change="handleTaskPick">
        <el-option
          v-for="task in taskList"
          :key="task.id"
          :label="`${task.id} - ${task.description || '无描述'}`"
          :value="task.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="taskDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getNlsqlTaskConfigList } from '@/api/nlsqlTaskConfig'
import { askTaskChat, getTaskChatConversations } from '@/api/taskChat'

const route = useRoute()

const taskList = ref([])
const selectedTask = ref(null)
const taskKeywordId = ref(null)
const taskDialogVisible = ref(false)

const currentSessionId = ref(null)
const sessionTitle = ref('')
const question = ref('')
const asking = ref(false)
const messages = ref([])

const openTaskDialog = () => {
  taskDialogVisible.value = true
}

const fetchTaskList = async () => {
  try {
    const res = await getNlsqlTaskConfigList({ page: 1, page_size: 100 })
    taskList.value = res.items || []
  } catch (error) {
    ElMessage.error('获取任务列表失败')
  }
}

const loadSessionHistory = async (sessionId) => {
  try {
    const res = await getTaskChatConversations(sessionId, { page: 1, page_size: 100 })
    const rows = (res.data || []).slice().reverse()
    const restored = []
    rows.forEach((row, idx) => {
      restored.push({
        localId: `${row.id}-u-${idx}`,
        role: 'user',
        content: row.question,
        created_at: row.created_at
      })
      if (row.answer) {
        restored.push({
          localId: `${row.id}-a-${idx}`,
          role: 'assistant',
          content: row.answer,
          created_at: row.created_at,
          sql_generated: row.sql_generated,
          sql_data: row.sql_data,
          selected_tables: row.selected_tables,
          select_table_result: row.select_table_result,
          query_context: row.query_context,
          q_column_patch: row.column_patch
        })
      }
    })
    messages.value = restored
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '加载历史会话失败')
  }
}

const initFromRouteQuery = async () => {
  const taskId = Number(route.query.task_id)
  const sessionId = Number(route.query.session_id)
  const sessionTitleQuery = typeof route.query.session_title === 'string' ? route.query.session_title : ''

  if (taskId) {
    const task = taskList.value.find(item => item.id === taskId)
    if (task) {
      selectedTask.value = task
      taskKeywordId.value = task.id
    }
  }

  if (sessionId && taskId) {
    currentSessionId.value = sessionId
    sessionTitle.value = sessionTitleQuery || ''
    await loadSessionHistory(sessionId)
    ElMessage.success(`已载入会话 #${sessionId}，可继续提问`)
  }
}

const handleTaskPick = (taskId) => {
  const task = taskList.value.find(item => item.id === taskId)
  if (!task) return
  selectedTask.value = task
  startNewSession()
  taskDialogVisible.value = false
}

const startNewSession = () => {
  currentSessionId.value = null
  messages.value = []
  question.value = ''
  ElMessage.success('已切换到新会话')
}

const handleAsk = async () => {
  if (!selectedTask.value) {
    taskDialogVisible.value = true
    ElMessage.warning('请先选择任务ID')
    return
  }
  if (!question.value.trim()) {
    ElMessage.warning('请输入问题')
    return
  }

  const userQuestion = question.value.trim()
  messages.value.push({
    localId: `${Date.now()}-u`,
    role: 'user',
    content: userQuestion,
    created_at: new Date().toISOString()
  })
  question.value = ''

  try {
    asking.value = true
    const payload = {
      task_id: selectedTask.value.id,
      question: userQuestion
    }
    if (currentSessionId.value) {
      payload.session_id = currentSessionId.value
    } else if (sessionTitle.value.trim()) {
      payload.session_title = sessionTitle.value.trim()
    }

    const res = await askTaskChat(payload)
    const data = res.data
    currentSessionId.value = data?.session?.id || currentSessionId.value

    messages.value.push({
      localId: `${Date.now()}-a`,
      role: 'assistant',
      content: data?.conversation?.answer || '未返回回答内容',
      created_at: data?.conversation?.created_at,
      sql_generated: data?.conversation?.sql_generated,
      sql_data: data?.conversation?.sql_data,
      selected_tables: data?.conversation?.selected_tables,
      select_table_result: data?.select_table_result,
      query_context: data?.conversation?.query_context || data?.query_context || data?.select_table_result?.query_context,
      q_column_patch: data?.qColumnPatch || data?.column_patch || data?.conversation?.column_patch
    })
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '问答失败')
  } finally {
    asking.value = false
  }
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleString('zh-CN')
}

const formatSqlData = (value) => {
  if (typeof value === 'string') return value
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

const isPlainObject = (value) => Object.prototype.toString.call(value) === '[object Object]'

const normalizeSqlRows = (value) => {
  if (Array.isArray(value)) return value
  if (isPlainObject(value)) return [value]
  return []
}

const isTabularData = (value) => {
  const rows = normalizeSqlRows(value)
  return rows.length > 0 && rows.every(row => isPlainObject(row))
}

const getSqlColumns = (value) => {
  const rows = normalizeSqlRows(value)
  const keySet = new Set()
  rows.forEach(row => {
    Object.keys(row).forEach(key => keySet.add(key))
  })
  return Array.from(keySet)
}

const normalizeSelectedTables = (value) => {
  if (Array.isArray(value)) return value
  return []
}

const hasSelectedTables = (value) => normalizeSelectedTables(value).length > 0

const normalizeSelectTableResult = (value) => {
  if (!value) return {}
  if (typeof value === 'string') {
    try {
      return JSON.parse(value)
    } catch {
      return {}
    }
  }
  return isPlainObject(value) ? value : {}
}

const getMessageSelectedTables = (item) => {
  const fromConversation = normalizeSelectedTables(item?.selected_tables)
  if (fromConversation.length > 0) return fromConversation
  const fromSelectResult = normalizeSelectedTables(normalizeSelectTableResult(item?.select_table_result).selected_tables)
  return fromSelectResult
}

const hasMessageSelectedTables = (item) => getMessageSelectedTables(item).length > 0

const getSelectTableReason = (item) => {
  const reason = normalizeSelectTableResult(item?.select_table_result).reason
  return typeof reason === 'string' && reason.trim() ? reason : ''
}

const getSelectTableCandidateCount = (item) => {
  const count = normalizeSelectTableResult(item?.select_table_result).candidate_count
  return typeof count === 'number' ? count : null
}

const normalizeQueryContext = (value) => {
  if (!value) return {}
  if (typeof value === 'string') {
    try {
      return JSON.parse(value)
    } catch {
      return {}
    }
  }
  return isPlainObject(value) ? value : {}
}

const hasQueryContext = (value) => {
  const ctx = normalizeQueryContext(value)
  return Boolean(
    ctx.driver_table ||
    (Array.isArray(ctx.allowed_tables) && ctx.allowed_tables.length > 0) ||
    (Array.isArray(ctx.joins) && ctx.joins.length > 0) ||
    (ctx.table_usage && Object.keys(ctx.table_usage).length > 0)
  )
}

const normalizeQColumnPatch = (value) => {
  if (!value) return {}
  if (typeof value === 'string') {
    try {
      return JSON.parse(value)
    } catch {
      return {}
    }
  }
  return isPlainObject(value) ? value : {}
}

const hasQColumnPatch = (value) => {
  const patch = normalizeQColumnPatch(value)
  const hasTables = Array.isArray(patch.tables) && patch.tables.length > 0
  const hasColumnPatches = patch.column_patches && Object.keys(patch.column_patches).length > 0
  return Boolean(hasTables || hasColumnPatches)
}


onMounted(() => {
  fetchTaskList().then(() => {
    initFromRouteQuery()
  })
})
</script>

<style scoped>
.test-chat-page {
  max-width: 1200px;
  margin: 0 auto;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 12px;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.session-title-row {
  margin-bottom: 12px;
}

.conversation-box {
  min-height: 360px;
  max-height: 58vh;
  overflow-y: auto;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 14px;
  background: #fff;
}

.empty-tip {
  color: var(--text-secondary);
  text-align: center;
  margin-top: 120px;
}

.message-row {
  display: flex;
  margin-bottom: 10px;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 76%;
  border-radius: 10px;
  padding: 10px 12px;
  background: #f5f7fb;
}

.message-row.user .message-bubble {
  background: rgba(106, 13, 173, 0.12);
}

.message-role {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.message-content {
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--text-primary);
}

.message-time {
  margin-top: 6px;
  font-size: 11px;
  color: #9aa7b7;
}

.sql-block,
.sql-data-block {
  margin-top: 8px;
}

.sql-label {
  margin-bottom: 4px;
  font-size: 12px;
  color: #617386;
  font-weight: 600;
}

.sql-content {
  margin: 0;
  padding: 8px;
  border-radius: 8px;
  background: #f1f5fb;
  color: #26486d;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  line-height: 1.5;
}

.sql-table {
  border-radius: 8px;
  overflow: hidden;
}

.selected-table-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.selected-table-tag {
  max-width: 100%;
}

.query-context-block {
  border: 1px solid #e5ecf5;
  border-radius: 8px;
  padding: 8px;
  background: #f8fbff;
}

.ctx-row {
  margin-bottom: 8px;
}

.ctx-row:last-child {
  margin-bottom: 0;
}

.ctx-key {
  display: inline-block;
  min-width: 98px;
  font-size: 12px;
  color: #586b80;
  font-weight: 600;
}

.ctx-value {
  font-size: 12px;
  color: #1f3a57;
}

.ctx-tag-list {
  display: inline-flex;
  gap: 6px;
  flex-wrap: wrap;
  vertical-align: top;
}

.ctx-join-list {
  margin-top: 4px;
}

.ctx-join-item {
  font-size: 12px;
  color: #294866;
  margin-bottom: 4px;
}

.patch-list {
  margin-top: 4px;
}

.patch-item {
  border: 1px dashed #c8d7e8;
  border-radius: 8px;
  padding: 8px;
  margin-bottom: 8px;
  background: #fff;
}

.patch-title {
  font-size: 12px;
  font-weight: 700;
  color: #345475;
  margin-bottom: 4px;
}

.patch-line {
  font-size: 12px;
  color: #284867;
  margin-bottom: 4px;
  white-space: pre-wrap;
  word-break: break-word;
}

.ask-row {
  margin-top: 12px;
  display: flex;
  gap: 10px;
  align-items: flex-end;
}

.send-btn {
  min-width: 86px;
}

@media (max-width: 860px) {
  .chat-header {
    flex-direction: column;
  }

  .ask-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
