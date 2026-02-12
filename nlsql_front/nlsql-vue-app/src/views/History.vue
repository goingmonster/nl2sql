<template>
  <div class="history-page">
    <div class="card">
      <h2 class="card-title">历史会话查看</h2>
      <p class="page-desc">按任务和关键词检索会话，查看完整问答记录</p>

      <div class="filter-row">
        <el-select v-model="filters.task_id" placeholder="选择任务ID" clearable filterable class="task-filter" @change="fetchSessions">
          <el-option
            v-for="task in taskList"
            :key="task.id"
            :label="`${task.id} - ${task.description || '无描述'}`"
            :value="task.id"
          />
        </el-select>
        <el-input v-model="filters.keyword" placeholder="搜索会话标题/问题/答案" clearable @keyup.enter="handleSearch" />
        <el-button type="primary" @click="handleSearch">搜索</el-button>
      </div>

      <el-table v-loading="loadingSessions" :data="sessionList" style="width: 100%">
        <el-table-column prop="id" label="会话ID" width="90" />
        <el-table-column prop="nlsql_task_id" label="任务ID" width="90" />
        <el-table-column prop="session_title" label="会话标题" min-width="220" show-overflow-tooltip />
        <el-table-column prop="conversation_count" label="对话数" width="90" />
        <el-table-column prop="updated_at" label="更新时间" width="180">
          <template #default="scope">{{ formatDate(scope.row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="210" fixed="right">
          <template #default="scope">
            <el-button link type="primary" @click="openSession(scope.row)">查看</el-button>
            <el-button link type="success" @click="continueSession(scope.row)">继续</el-button>
            <el-button link type="danger" @click="handleDeleteSession(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchSessions"
          @current-change="fetchSessions"
        />
      </div>
    </div>

    <el-dialog v-model="detailVisible" :title="`会话详情 #${currentSession?.id || ''}`" width="980px">
      <div class="detail-header">
        <div>任务ID：{{ currentSession?.nlsql_task_id }}</div>
        <div>会话标题：{{ currentSession?.session_title || '-' }}</div>
      </div>

      <div class="conversation-list" v-loading="loadingConversations">
        <div v-if="conversationList.length === 0" class="empty-tip">暂无对话记录</div>
        <div v-for="item in conversationList" :key="item.id" class="conversation-item">
          <div class="q-block">
            <div class="label">Q</div>
            <div class="content">{{ item.question }}</div>
          </div>
          <div class="a-block">
            <div class="label">A</div>
            <div class="content">{{ item.answer || '-' }}</div>
          </div>
          <div v-if="item.sql_generated" class="sql-panel">
            <div class="sql-title">SQL</div>
            <pre class="sql-pre">{{ item.sql_generated }}</pre>
          </div>
          <div v-if="item.sql_data !== undefined && item.sql_data !== null" class="sql-panel">
            <div class="sql-title">SQL Data</div>
            <el-table
              v-if="isTabularData(item.sql_data)"
              :data="normalizeSqlRows(item.sql_data)"
              size="small"
              border
              max-height="280"
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
            <pre v-else class="sql-pre">{{ formatSqlData(item.sql_data) }}</pre>
          </div>
          <div v-if="hasMessageSelectedTables(item)" class="sql-panel">
            <div class="sql-title">Selected Tables</div>
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
          <div v-if="hasQueryContext(item.query_context)" class="sql-panel">
            <div class="sql-title">Query Context</div>
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
                <pre class="sql-pre">{{ formatSqlData(normalizeQueryContext(item.query_context).table_usage) }}</pre>
              </div>
            </div>
          </div>
          <div v-if="hasQColumnPatch(item.column_patch)" class="sql-panel">
            <div class="sql-title">Q Column Patch</div>
            <div class="query-context-block">
              <div v-if="normalizeQColumnPatch(item.column_patch).tables?.length" class="ctx-row">
                <span class="ctx-key">tables:</span>
                <div class="ctx-tag-list">
                  <el-tag
                    v-for="table in normalizeQColumnPatch(item.column_patch).tables"
                    :key="`patch-table-${table}`"
                    size="small"
                    effect="plain"
                  >
                    {{ table }}
                  </el-tag>
                </div>
              </div>

              <div v-if="normalizeQColumnPatch(item.column_patch).column_patches" class="ctx-row">
                <span class="ctx-key">column_patches:</span>
                <div class="patch-list">
                  <div
                    v-for="(patchItem, tableName) in normalizeQColumnPatch(item.column_patch).column_patches"
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
          <div class="meta-row">
            <el-tag size="small" :type="item.is_right === true ? 'success' : item.is_right === false ? 'danger' : 'info'">
              {{ item.is_right === true ? '正确' : item.is_right === false ? '错误' : '未评价' }}
            </el-tag>
            <span class="meta-text">{{ formatDate(item.created_at) }}</span>
          </div>

          <div class="feedback-row">
            <el-select v-model="feedbackEdits[item.id].is_right" placeholder="评价" clearable class="feedback-select">
              <el-option label="正确" :value="true" />
              <el-option label="错误" :value="false" />
            </el-select>
            <el-input
              v-model="feedbackEdits[item.id].feedback"
              placeholder="填写反馈（可选）"
              clearable
            />
            <el-button
              type="primary"
              plain
              :loading="feedbackLoadingIds.includes(item.id)"
              @click="saveFeedback(item.id)"
            >保存反馈</el-button>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getNlsqlTaskConfigList } from '@/api/nlsqlTaskConfig'
import { deleteTaskChatSession, getTaskChatConversations, getTaskChatSessions, updateTaskChatConversationFeedback } from '@/api/taskChat'

const router = useRouter()

const loadingSessions = ref(false)
const loadingConversations = ref(false)
const detailVisible = ref(false)
const feedbackLoadingIds = ref([])

const taskList = ref([])
const sessionList = ref([])
const conversationList = ref([])
const currentSession = ref(null)
const feedbackEdits = reactive({})

const filters = reactive({
  task_id: null,
  keyword: ''
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const fetchTasks = async () => {
  try {
    const res = await getNlsqlTaskConfigList({ page: 1, page_size: 100 })
    taskList.value = res.items || []
  } catch (error) {
    ElMessage.error('获取任务列表失败')
  }
}

const fetchSessions = async () => {
  try {
    loadingSessions.value = true
    const params = {
      page: pagination.page,
      page_size: pagination.page_size
    }
    if (filters.task_id) params.task_id = filters.task_id
    if (filters.keyword.trim()) params.keyword = filters.keyword.trim()
    const res = await getTaskChatSessions(params)
    sessionList.value = res.data || []
    pagination.total = res.pagination?.total || 0
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '获取会话列表失败')
  } finally {
    loadingSessions.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchSessions()
}

const openSession = async (session) => {
  currentSession.value = session
  detailVisible.value = true
  try {
    loadingConversations.value = true
    const res = await getTaskChatConversations(session.id, { page: 1, page_size: 100 })
    conversationList.value = res.data || []
    conversationList.value.forEach(item => {
      feedbackEdits[item.id] = {
        is_right: item.is_right,
        feedback: item.feedback || ''
      }
    })
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '获取会话对话失败')
  } finally {
    loadingConversations.value = false
  }
}

const continueSession = (session) => {
  router.push({
    path: '/test',
    query: {
      task_id: String(session.nlsql_task_id),
      session_id: String(session.id),
      session_title: session.session_title || ''
    }
  })
}

const saveFeedback = async (conversationId) => {
  const editValue = feedbackEdits[conversationId]
  if (!editValue) return
  try {
    feedbackLoadingIds.value = [...feedbackLoadingIds.value, conversationId]
    await updateTaskChatConversationFeedback(conversationId, {
      is_right: editValue.is_right,
      feedback: editValue.feedback || null
    })
    const row = conversationList.value.find(item => item.id === conversationId)
    if (row) {
      row.is_right = editValue.is_right
      row.feedback = editValue.feedback || null
    }
    ElMessage.success('反馈已更新')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '更新反馈失败')
  } finally {
    feedbackLoadingIds.value = feedbackLoadingIds.value.filter(id => id !== conversationId)
  }
}

const handleDeleteSession = async (session) => {
  try {
    await ElMessageBox.confirm(`确认删除会话 #${session.id} 吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消'
    })
    await deleteTaskChatSession(session.id)
    ElMessage.success('删除成功')
    fetchSessions()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

const formatDate = (value) => {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN')
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


onMounted(async () => {
  await fetchTasks()
  fetchSessions()
})
</script>

<style scoped>
.history-page {
  max-width: 1280px;
  margin: 0 auto;
}

.filter-row {
  margin-bottom: 14px;
  display: flex;
  gap: 10px;
  align-items: center;
}

.task-filter {
  width: 260px;
  flex-shrink: 0;
}

.pagination-wrap {
  margin-top: 14px;
  display: flex;
  justify-content: center;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.conversation-list {
  max-height: 62vh;
  overflow-y: auto;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 12px;
}

.empty-tip {
  text-align: center;
  color: var(--text-secondary);
  padding: 30px 0;
}

.conversation-item {
  border: 1px solid #e6ebf2;
  border-radius: 10px;
  padding: 10px;
  margin-bottom: 10px;
}

.q-block,
.a-block {
  display: grid;
  grid-template-columns: 22px 1fr;
  gap: 8px;
  margin-bottom: 8px;
}

.label {
  font-weight: 700;
  color: var(--primary-color);
}

.content {
  white-space: pre-wrap;
  word-break: break-word;
}

.meta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.meta-text {
  color: #8fa1b2;
  font-size: 12px;
}

.sql-panel {
  margin-bottom: 8px;
}

.sql-title {
  margin-bottom: 4px;
  color: #5b6d80;
  font-size: 12px;
  font-weight: 600;
}

.sql-pre {
  margin: 0;
  padding: 8px;
  border-radius: 8px;
  background: #f1f5fb;
  color: #26486d;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-x: auto;
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

.feedback-row {
  margin-top: 10px;
  display: grid;
  grid-template-columns: 120px 1fr 110px;
  gap: 8px;
}

.feedback-select {
  width: 100%;
}

@media (max-width: 860px) {
  .filter-row {
    flex-direction: column;
    align-items: stretch;
  }

  .task-filter {
    width: 100%;
  }

  .detail-header {
    flex-direction: column;
    gap: 6px;
  }

  .feedback-row {
    grid-template-columns: 1fr;
  }
}
</style>
