<template>
  <div class="table-metadata-view">
    <div class="card search-card">
      <h2 class="card-title">问答样例管理</h2>
      <p class="page-desc">支持导入问答对、增删改查、批量删除与 AI 分析 where 条件</p>

      <div class="search-section">
        <el-input
          v-model="searchForm.table_name"
          placeholder="按表名/关键词筛选"
          clearable
          class="search-input"
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-select
          v-model="searchForm.task_id"
          placeholder="选择任务"
          clearable
          class="task-select"
          @change="handleTaskFilterChange"
        >
          <el-option
            v-for="task in taskList"
            :key="task.id"
            :label="`${task.id} - ${task.description || '无描述'}`"
            :value="task.id"
          />
        </el-select>

        <el-button type="primary" @click="handleSearch">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          新增
        </el-button>
        <el-button @click="handleOpenImport">导入问答对</el-button>
        <el-button type="success" :disabled="selectedRows.length === 0" @click="handleOpenAnalyze">
          AI分析问答对 ({{ selectedRows.length }})
        </el-button>
        <el-button type="danger" :disabled="selectedRows.length === 0" @click="handleBatchDelete">
          批量删除 ({{ selectedRows.length }})
        </el-button>
        <el-button type="warning" :disabled="selectedRows.length === 0" @click="handleExport">
          导出 ({{ selectedRows.length }})
        </el-button>
      </div>
    </div>

    <div class="card table-card">
      <div class="table-container">
        <el-table
          ref="tableRef"
          v-loading="loading"
          :data="qaList"
          style="width: 100%"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="55" />
          <el-table-column prop="id" label="ID" width="90" />
          <el-table-column prop="nlsql_task_id" label="任务ID" width="100" />
          <el-table-column prop="question" label="问题" min-width="260" show-overflow-tooltip />
          <el-table-column prop="sql" label="SQL" min-width="240" show-overflow-tooltip />
          <el-table-column label="使用的表" width="120">
            <template #default="scope">
              <el-tag
                v-if="scope.row.tables && scope.row.tables.length > 0"
                type="success"
                size="small"
              >
                {{ scope.row.tables.length }} 表
              </el-tag>
              <span v-else class="empty-text">-</span>
            </template>
          </el-table-column>
          <el-table-column label="WHERE 条件" width="120">
            <template #default="scope">
              {{ Array.isArray(scope.row.where_conditions) ? scope.row.where_conditions.length : 0 }} 条
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="scope">
              <el-tag :type="scope.row.is_enabled ? 'success' : 'info'">{{ scope.row.is_enabled ? '启用' : '禁用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="190" fixed="right">
            <template #default="scope">
              <el-link type="primary" @click="handleView(scope.row)">查看</el-link>
              <el-divider direction="vertical" />
              <el-link type="primary" @click="handleEdit(scope.row)">编辑</el-link>
              <el-divider direction="vertical" />
              <el-link type="danger" @click="handleDelete(scope.row)">删除</el-link>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <div class="compact-pagination">
      <div class="pagination-content">
        <span class="record-count">共 {{ pagination.total }} 条</span>
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          size="small"
          layout="prev, pager, next, sizes"
          :background="false"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>

    <el-dialog
      v-model="showEditDialog"
      :title="isEditing ? '编辑问答样例' : '新增问答样例'"
      width="980px"
      @close="resetEditForm"
    >
      <el-form ref="formRef" :model="editForm" :rules="formRules" label-width="120px">
        <el-form-item label="任务ID" prop="nlsql_task_id">
          <el-select
            v-model="editForm.nlsql_task_id"
            placeholder="请选择任务"
            style="width: 100%"
            :disabled="isEditing"
          >
            <el-option
              v-for="task in taskList"
              :key="task.id"
              :label="`${task.id} - ${task.description || '无描述'}`"
              :value="task.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="问题" prop="question">
          <el-input v-model="editForm.question" type="textarea" :rows="3" placeholder="请输入问题" />
        </el-form-item>
        <el-form-item label="SQL" prop="sql">
          <el-input v-model="editForm.sql" type="textarea" :rows="6" placeholder="请输入 SQL" />
        </el-form-item>
        <el-form-item label="WHERE条件(JSON)">
          <el-input
            v-model="editForm.where_conditions_text"
            type="textarea"
            :rows="6"
            placeholder='可输入JSON数组，如 [{"field":"day_key","operator":"eq","value":"2025-12-06"}]'
          />
        </el-form-item>
        <el-form-item label="使用的表">
          <el-input
            v-model="editForm.tables_text"
            type="textarea"
            :rows="3"
            placeholder='可输入JSON数组，如 ["orders", "users"]'
          />
        </el-form-item>
        <el-form-item label="是否启用">
          <el-switch v-model="editForm.is_enabled" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" :loading="saveLoading" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showViewDialog" title="问答样例详情" width="980px">
      <div v-if="viewDetail" class="view-detail-wrap">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="ID">{{ viewDetail.id }}</el-descriptions-item>
          <el-descriptions-item label="任务ID">{{ viewDetail.nlsql_task_id }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="viewDetail.is_enabled ? 'success' : 'info'">{{ viewDetail.is_enabled ? '启用' : '禁用' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDate(viewDetail.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatDate(viewDetail.updated_at) }}</el-descriptions-item>
          <el-descriptions-item label="问题" :span="2">{{ viewDetail.question }}</el-descriptions-item>
        </el-descriptions>

        <div class="detail-section">
          <h4>使用的表</h4>
          <div v-if="Array.isArray(viewDetail.tables) && viewDetail.tables.length > 0" class="tag-list">
            <el-tag v-for="(table, index) in viewDetail.tables" :key="`table-${index}`" type="success" size="small" class="table-tag">
              {{ table }}
            </el-tag>
          </div>
          <div v-else class="empty-text">暂无表信息</div>
        </div>

        <div class="detail-section">
          <h4>SQL</h4>
          <pre class="code-block">{{ viewDetail.sql || '-' }}</pre>
        </div>

        <div class="detail-section">
          <h4>WHERE 条件</h4>
          <div v-if="Array.isArray(viewDetail.where_conditions) && viewDetail.where_conditions.length > 0" class="condition-list">
            <div v-for="(item, index) in viewDetail.where_conditions" :key="`cond-${index}`" class="condition-item">
              <span class="cond-field">{{ item.field }}</span>
              <span class="cond-op">{{ item.operator }}</span>
              <span class="cond-val">{{ formatConditionValue(item.value) }}</span>
              <span v-if="item.description" class="cond-desc">{{ item.description }}</span>
            </div>
          </div>
          <div v-else class="empty-text">暂无 WHERE 条件</div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showViewDialog = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showImportDialog" title="导入问答对" width="920px" @close="resetImportForm">
      <el-form :model="importForm" label-width="120px">
        <el-form-item label="任务ID" required>
          <el-select v-model="importForm.task_id" placeholder="请选择任务" style="width: 100%">
            <el-option
              v-for="task in taskList"
              :key="task.id"
              :label="`${task.id} - ${task.description || '无描述'}`"
              :value="task.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="JSON内容" required>
          <el-input
            v-model="importForm.json_text"
            type="textarea"
            :rows="14"
            placeholder='请粘贴JSON数组，例如 [{"question":"...","sql":"...","where_conditions":[...]}]'
          />
          <div class="help-text">根节点必须是数组，每项至少包含 question 和 sql 字段。</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showImportDialog = false">取消</el-button>
        <el-button type="primary" :loading="importLoading" @click="handleImport">导入</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showAnalyzeDialog" title="AI分析问答对" width="600px" @close="resetAnalyzeForm">
      <el-form :model="analyzeForm" label-width="140px">
        <el-form-item label="已选问答对">
          <el-tag type="info">{{ selectedRows.length }} 条</el-tag>
        </el-form-item>
        <el-form-item label="LLM配置" required>
          <el-select v-model="analyzeForm.llm_config_id" placeholder="请选择LLM配置" style="width: 100%">
            <el-option
              v-for="llm in llmList"
              :key="llm.id"
              :label="`${llm.id} - ${llm.provider || 'unknown'} - ${llm.model_name || '-'}`"
              :value="llm.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAnalyzeDialog = false">取消</el-button>
        <el-button type="primary" :loading="analyzeLoading" @click="handleAnalyze">开始分析</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  batchDeleteQaEmbedding,
  createQaEmbedding,
  deleteQaEmbedding,
  generateQaWhereConditions,
  getQaEmbedding,
  getQaEmbeddingList,
  importQaEmbedding,
  updateQaEmbedding,
  exportQaEmbeddings
} from '@/api/qaEmbedding'
import { getNlsqlTaskConfigList } from '@/api/nlsqlTaskConfig'
import { getLlmConfigList } from '@/api/llmConfig'

const loading = ref(false)
const saveLoading = ref(false)
const importLoading = ref(false)
const analyzeLoading = ref(false)

const qaList = ref([])
const taskList = ref([])
const llmList = ref([])
const selectedRows = ref([])
const tableRef = ref(null)

const showEditDialog = ref(false)
const showViewDialog = ref(false)
const showImportDialog = ref(false)
const showAnalyzeDialog = ref(false)

const isEditing = ref(false)
const formRef = ref(null)
const viewDetail = ref(null)

const searchForm = reactive({
  table_name: '',
  task_id: null
})

const pagination = reactive({
  page: 1,
  page_size: 10,
  total: 0
})

const editForm = reactive({
  id: null,
  nlsql_task_id: null,
  question: '',
  sql: '',
  where_conditions_text: '',
  tables_text: '',
  is_enabled: true
})

const importForm = reactive({
  task_id: null,
  json_text: ''
})

const analyzeForm = reactive({
  llm_config_id: null
})

const formRules = {
  nlsql_task_id: [{ required: true, message: '请选择任务', trigger: 'change' }],
  question: [{ required: true, message: '请输入问题', trigger: 'blur' }],
  sql: [{ required: true, message: '请输入SQL', trigger: 'blur' }]
}

async function fetchTaskList() {
  try {
    const res = await getNlsqlTaskConfigList({ page: 1, page_size: 100 })
    taskList.value = res.items || res.data || []
  } catch (error) {
    console.error('获取任务列表失败:', error)
    ElMessage.error('获取任务列表失败')
  }
}

async function fetchLlmList() {
  try {
    const res = await getLlmConfigList({ page: 1, page_size: 100, status: 1 })
    llmList.value = res.data || res.items || []
  } catch (error) {
    console.error('获取LLM配置失败:', error)
    ElMessage.error('获取LLM配置失败')
  }
}

async function fetchList() {
  try {
    loading.value = true
    const params = {
      page: pagination.page,
      page_size: pagination.page_size
    }

    if (searchForm.task_id) {
      params.task_id = searchForm.task_id
    }
    if (searchForm.table_name) {
      params.question = searchForm.table_name
    }

    const res = await getQaEmbeddingList(params)
    qaList.value = res.data || res.items || []
    pagination.total = res.pagination?.total || res.total || 0

    selectedRows.value = []
    tableRef.value?.clearSelection()
  } catch (error) {
    console.error('获取问答样例列表失败:', error)
    ElMessage.error('获取问答样例列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  fetchList()
}

function handleReset() {
  searchForm.table_name = ''
  searchForm.task_id = null
  pagination.page = 1
  fetchList()
}

function handleTaskFilterChange() {
  pagination.page = 1
  fetchList()
}

function handleSelectionChange(selection) {
  selectedRows.value = selection
}

function handleSizeChange(size) {
  pagination.page_size = size
  pagination.page = 1
  fetchList()
}

function handleCurrentChange(page) {
  pagination.page = page
  fetchList()
}

async function refreshListAfterDelete() {
  await fetchList()
  if (qaList.value.length === 0 && pagination.page > 1) {
    pagination.page -= 1
    await fetchList()
  }
}

function handleCreate() {
  isEditing.value = false
  resetEditForm()
  if (searchForm.task_id) {
    editForm.nlsql_task_id = searchForm.task_id
  }
  showEditDialog.value = true
}

async function handleEdit(row) {
  try {
    isEditing.value = true
    const res = await getQaEmbedding(row.id)
    const data = res.data || res

    editForm.id = data.id
    editForm.nlsql_task_id = data.nlsql_task_id
    editForm.question = data.question || ''
    editForm.sql = data.sql || ''
    editForm.where_conditions_text = data.where_conditions ? JSON.stringify(data.where_conditions, null, 2) : ''
    editForm.tables_text = data.tables ? JSON.stringify(data.tables, null, 2) : ''
    editForm.is_enabled = data.is_enabled !== false

    showEditDialog.value = true
  } catch (error) {
    console.error('获取问答样例详情失败:', error)
    ElMessage.error('获取问答样例详情失败')
  }
}

async function handleView(row) {
  try {
    const res = await getQaEmbedding(row.id)
    viewDetail.value = res.data || res
    showViewDialog.value = true
  } catch (error) {
    console.error('获取问答样例详情失败:', error)
    ElMessage.error('获取问答样例详情失败')
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除问答样例 #${row.id} 吗？`, '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await deleteQaEmbedding(row.id)
    ElMessage.success('删除成功')
    await refreshListAfterDelete()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除问答样例失败:', error)
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

async function handleBatchDelete() {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请选择要删除的记录')
    return
  }

  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedRows.value.length} 条记录吗？`, '批量删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    const ids = selectedRows.value.map(item => item.id).filter(id => Number.isFinite(id))
    await batchDeleteQaEmbedding(ids)
    ElMessage.success('批量删除成功')
    await refreshListAfterDelete()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error(error.response?.data?.detail || '批量删除失败')
    }
  }
}

async function handleSave() {
  if (!formRef.value) {
    return
  }

  try {
    await formRef.value.validate()
    saveLoading.value = true

    const whereConditions = parseWhereConditionsText(editForm.where_conditions_text)
    const tables = parseTablesText(editForm.tables_text)
    if (isEditing.value) {
      await updateQaEmbedding(editForm.id, {
        question: editForm.question.trim(),
        sql: editForm.sql.trim(),
        where_conditions: whereConditions,
        tables: tables,
        is_enabled: editForm.is_enabled
      })
      ElMessage.success('更新成功')
    } else {
      await createQaEmbedding({
        question: editForm.question.trim(),
        nlsql_task_id: Number(editForm.nlsql_task_id),
        sql: editForm.sql.trim(),
        where_conditions: whereConditions,
        tables: tables,
        is_enabled: editForm.is_enabled
      })
      ElMessage.success('创建成功')
    }

    showEditDialog.value = false
    await fetchList()
  } catch (error) {
    console.error('保存问答样例失败:', error)
    ElMessage.error(error.response?.data?.detail || error.message || '保存失败')
  } finally {
    saveLoading.value = false
  }
}

function handleOpenImport() {
  resetImportForm()
  if (searchForm.task_id) {
    importForm.task_id = searchForm.task_id
  }
  showImportDialog.value = true
}

async function handleImport() {
  try {
    if (!importForm.task_id) {
      ElMessage.warning('请选择任务')
      return
    }

    const qaJson = parseImportJson(importForm.json_text)
    importLoading.value = true

    const res = await importQaEmbedding({
      task_id: Number(importForm.task_id),
      qa_json: qaJson
    })

    ElMessage.success(`导入成功，新增 ${res.data?.created_count ?? res.created_count ?? 0} 条`)
    showImportDialog.value = false
    pagination.page = 1
    await fetchList()
  } catch (error) {
    console.error('导入问答对失败:', error)
    ElMessage.error(error.response?.data?.detail || error.message || '导入失败')
  } finally {
    importLoading.value = false
  }
}

async function handleOpenAnalyze() {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请先选择要分析的问答对')
    return
  }

  resetAnalyzeForm()
  await fetchLlmList()
  showAnalyzeDialog.value = true
}

async function handleAnalyze() {
  try {
    if (!analyzeForm.llm_config_id) {
      ElMessage.warning('请选择LLM配置')
      return
    }

    analyzeLoading.value = true
    const payload = {
      qa_embedding_ids: selectedRows.value.map(item => item.id).filter(id => Number.isFinite(id)),
      llm_config_id: Number(analyzeForm.llm_config_id)
    }

    const res = await generateQaWhereConditions(payload)
    const data = res.data || res
    ElMessage.success(`分析完成：成功 ${data.success_count || 0} 条，失败 ${data.failed_count || 0} 条`)

    if (Array.isArray(data.failed_items) && data.failed_items.length > 0) {
      console.error('AI分析失败项:', data.failed_items)
    }

    showAnalyzeDialog.value = false
    await fetchList()
  } catch (error) {
    console.error('AI分析失败:', error)
    ElMessage.error(error.response?.data?.detail || error.message || 'AI分析失败')
  } finally {
    analyzeLoading.value = false
  }
}

async function handleExport() {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请选择要导出的记录')
    return
  }

  try {
    const ids = selectedRows.value.map(item => item.id).filter(id => Number.isFinite(id))
    const res = await exportQaEmbeddings(ids)
    const data = res.data || res

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    const timestamp = new Date().toISOString().slice(0, 10)
    link.download = `qa_export_${timestamp}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    ElMessage.success(`成功导出 ${data.length} 条问答对`)
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error(error.response?.data?.detail || error.message || '导出失败')
  }
}

function parseWhereConditionsText(text) {
  const raw = (text || '').trim()
  if (!raw) {
    return null
  }

  try {
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) {
      throw new Error('WHERE条件必须是JSON数组')
    }
    return parsed
  } catch (error) {
    throw new Error(`WHERE条件JSON格式不正确: ${error.message}`)
  }
}

function parseTablesText(text) {
  const raw = (text || '').trim()
  if (!raw) {
    return null
  }

  try {
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) {
      throw new Error('使用的表必须是JSON数组')
    }
    return parsed
  } catch (error) {
    throw new Error(`使用的表JSON格式不正确: ${error.message}`)
  }
}

function parseImportJson(text) {
  const raw = (text || '').trim()
  if (!raw) {
    throw new Error('请粘贴要导入的JSON内容')
  }

  let parsed
  try {
    parsed = JSON.parse(raw)
  } catch (error) {
    throw new Error(`JSON解析失败: ${error.message}`)
  }

  if (!Array.isArray(parsed) || parsed.length === 0) {
    throw new Error('导入内容必须是非空JSON数组')
  }

  parsed.forEach((item, index) => {
    if (!item || typeof item !== 'object') {
      throw new Error(`第 ${index + 1} 项必须是对象`) 
    }
    if (!item.question || typeof item.question !== 'string') {
      throw new Error(`第 ${index + 1} 项缺少 question`) 
    }
    if (!item.sql || typeof item.sql !== 'string') {
      throw new Error(`第 ${index + 1} 项缺少 sql`) 
    }
    if (item.where_conditions !== undefined && item.where_conditions !== null && !Array.isArray(item.where_conditions)) {
      throw new Error(`第 ${index + 1} 项 where_conditions 必须是数组`) 
    }
  })

  return parsed
}

function formatDate(value) {
  if (!value) {
    return '-'
  }
  return new Date(value).toLocaleString('zh-CN')
}

function formatConditionValue(value) {
  if (value === null || value === undefined) {
    return 'null'
  }
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  return String(value)
}

function resetEditForm() {
  editForm.id = null
  editForm.nlsql_task_id = null
  editForm.question = ''
  editForm.sql = ''
  editForm.where_conditions_text = ''
  editForm.tables_text = ''
  editForm.is_enabled = true

  if (formRef.value) {
    formRef.value.resetFields()
  }
}

function resetImportForm() {
  importForm.task_id = null
  importForm.json_text = ''
}

function resetAnalyzeForm() {
  analyzeForm.llm_config_id = null
}

onMounted(async () => {
  await fetchTaskList()
  await fetchList()
})
</script>

<style scoped>
.page-desc {
  color: var(--text-secondary);
  margin-bottom: 20px;
}

.search-card {
  margin-bottom: 16px;
}

.search-section {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
  padding: 12px 16px;
  background: linear-gradient(to right, #f8fafc, #ffffff);
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.search-input,
.task-select {
  width: 220px;
}

.card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  border: 1px solid #ebeef5;
  background: #fff;
}

.table-card {
  max-height: calc(100vh - 240px);
}

.table-container {
  flex: 1;
  overflow-y: auto;
  max-height: calc(100vh - 270px);
  min-height: 420px;
}

.compact-pagination {
  position: fixed;
  bottom: 20px;
  left: 260px;
  right: 20px;
  z-index: 1000;
  display: flex;
  justify-content: center;
}

.pagination-content {
  display: flex;
  align-items: center;
  gap: 20px;
  border: 1px solid #e4e7ed;
  border-radius: 20px;
  padding: 6px 16px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  background: rgba(255, 255, 255, 0.95);
}

.record-count {
  font-size: 12px;
  color: #909399;
  font-weight: 500;
  white-space: nowrap;
}

.view-detail-wrap {
  max-height: 70vh;
  overflow-y: auto;
}

.detail-section {
  margin-top: 16px;
}

.detail-section h4 {
  margin: 0 0 10px;
  font-size: 14px;
  color: #303133;
}

.code-block {
  margin: 0;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  background: #f8fafc;
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.6;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.table-tag {
  margin: 0;
}

.condition-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.condition-item {
  border: 1px solid #e6edf5;
  border-radius: 8px;
  padding: 8px 10px;
  background: #fbfdff;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.cond-field {
  color: #2d72d9;
  font-weight: 600;
}

.cond-op {
  color: #67c23a;
  font-weight: 600;
}

.cond-val {
  color: #303133;
}

.cond-desc {
  color: #909399;
}

.help-text,
.empty-text {
  color: #909399;
  font-size: 12px;
  margin-top: 6px;
}

@media (max-width: 1200px) {
  .search-section {
    gap: 8px;
    padding: 10px;
    flex-wrap: wrap;
  }
}

@media (max-width: 768px) {
  .compact-pagination {
    left: 20px;
    right: 20px;
    bottom: 15px;
  }

  .search-input,
  .task-select {
    width: 100%;
  }

  .search-section {
    flex-direction: column;
    align-items: stretch;
  }

  .table-card {
    max-height: calc(100vh - 330px);
  }

  .table-container {
    max-height: calc(100vh - 360px);
    min-height: 280px;
  }

  .pagination-content {
    flex-direction: column;
    gap: 10px;
    padding: 10px 12px;
  }
}
</style>
