<template>
  <div class="table-metadata-view">
    <div class="card search-card">
      <h2 class="card-title">字段提示词管理</h2>
      <p class="page-desc">支持按表名和任务筛选，提供字段提示词分页查询、新增、修改、单删与批量删除</p>

      <div class="search-section">
        <el-input
          v-model="searchForm.table_name"
          placeholder="搜索表名"
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
        <el-button type="danger" :disabled="selectedRows.length === 0" @click="handleBatchDelete">
          批量删除 ({{ selectedRows.length }})
        </el-button>
      </div>
    </div>

    <div class="card table-card">
      <div class="table-container">
        <el-table
          ref="tableRef"
          v-loading="loading"
          :data="promptList"
          style="width: 100%"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="55" />
          <el-table-column prop="id" label="ID" width="90" />
          <el-table-column prop="table_name" label="表名" min-width="180" show-overflow-tooltip />
          <el-table-column prop="nlsql_task_id" label="任务ID" width="100" />
          <el-table-column prop="field_name" label="字段名" min-width="160" show-overflow-tooltip />
          <el-table-column prop="business_meaning" label="业务含义" min-width="180" show-overflow-tooltip />
          <el-table-column prop="field_type" label="字段类型" width="120" show-overflow-tooltip />
          <el-table-column prop="updated_at" label="更新时间" width="180">
            <template #default="scope">
              {{ formatDate(scope.row.updated_at) }}
            </template>
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
      :title="isEditing ? '编辑字段提示词' : '新增字段提示词'"
      width="920px"
      @close="resetForm"
    >
      <el-form ref="formRef" :model="editForm" :rules="formRules" label-width="140px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="任务ID" prop="nlsql_task_id">
              <el-select
                v-model="editForm.nlsql_task_id"
                placeholder="请选择任务"
                style="width: 100%"
                :disabled="isEditing"
                @change="handleTaskSelectorChange"
              >
                <el-option
                  v-for="task in taskList"
                  :key="task.id"
                  :label="`${task.id} - ${task.description || '无描述'}`"
                  :value="task.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="表级提示词ID" prop="table_level_prompt_id">
              <el-select
                v-model="editForm.table_level_prompt_id"
                placeholder="可选：关联表级提示词"
                clearable
                filterable
                style="width: 100%"
                :disabled="isEditing"
              >
                <el-option
                  v-for="item in tablePromptOptions"
                  :key="item.id"
                  :label="`${item.table_name || '未知表'} (#${item.id})`"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="字段名" prop="field_name">
          <el-input v-model="editForm.field_name" :disabled="isEditing" placeholder="例如：order_id" />
        </el-form-item>
        <el-form-item label="业务含义" prop="business_meaning">
          <el-input v-model="editForm.business_meaning" placeholder="请输入业务含义" />
        </el-form-item>
        <el-form-item label="数据格式" prop="data_format">
          <el-input v-model="editForm.data_format" placeholder="例如：YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="字段描述" prop="field_description">
          <el-input v-model="editForm.field_description" type="textarea" :rows="2" placeholder="请输入字段描述" />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="字段类型" prop="field_type">
              <el-input v-model="editForm.field_type" placeholder="例如：varchar" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="空值率" prop="null_rate">
              <el-input v-model="editForm.null_rate" placeholder="例如：0.12" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="唯一值数量" prop="unique_count">
          <el-input-number
            v-model="editForm.unique_count"
            :min="0"
            :step="1"
            :controls="false"
            style="width: 100%"
            placeholder="可选"
          />
        </el-form-item>

        <el-form-item label="查询场景(JSON)">
          <el-input
            v-model="editForm.query_scenarios"
            type="textarea"
            :rows="3"
            placeholder='可输入JSON数组字符串，如 ["按用户查订单"]'
          />
        </el-form-item>
        <el-form-item label="聚合场景(JSON)">
          <el-input
            v-model="editForm.aggregation_scenarios"
            type="textarea"
            :rows="3"
            placeholder='可输入JSON数组字符串，如 ["按月统计"]'
          />
        </el-form-item>
        <el-form-item label="规则(JSON)">
          <el-input
            v-model="editForm.rules"
            type="textarea"
            :rows="3"
            placeholder='可输入JSON数组字符串，如 ["金额>=0"]'
          />
        </el-form-item>
        <el-form-item label="数据库使用方式(JSON)">
          <el-input
            v-model="editForm.database_usage"
            type="textarea"
            :rows="3"
            placeholder='可输入JSON数组字符串，如 ["作为过滤条件"]'
          />
        </el-form-item>
        <el-form-item label="样例值(JSON数组)">
          <el-input
            v-model="editForm.sample_values_text"
            type="textarea"
            :rows="3"
            placeholder='可输入JSON数组，如 ["A001", "A002"]；也支持每行一个值'
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" :loading="saveLoading" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="showViewDialog"
      title="字段提示词详情"
      width="980px"
    >
      <div v-if="viewDetail" class="view-detail-wrap">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="ID">{{ viewDetail.id }}</el-descriptions-item>
          <el-descriptions-item label="表名">{{ viewDetail.table_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="任务ID">{{ viewDetail.nlsql_task_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="表级提示词ID">{{ viewDetail.table_level_prompt_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="字段名">{{ viewDetail.field_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="字段类型">{{ viewDetail.field_type || '-' }}</el-descriptions-item>
          <el-descriptions-item label="空值率">{{ viewDetail.null_rate || '-' }}</el-descriptions-item>
          <el-descriptions-item label="唯一值数量">{{ viewDetail.unique_count ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDate(viewDetail.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatDate(viewDetail.updated_at) }}</el-descriptions-item>
          <el-descriptions-item label="业务含义" :span="2">{{ viewDetail.business_meaning || '-' }}</el-descriptions-item>
          <el-descriptions-item label="数据格式" :span="2">{{ viewDetail.data_format || '-' }}</el-descriptions-item>
          <el-descriptions-item label="字段描述" :span="2">{{ viewDetail.field_description || '-' }}</el-descriptions-item>
        </el-descriptions>

        <div class="view-section">
          <h4>查询场景</h4>
          <div class="tag-list" v-if="getVisualItems(viewDetail.query_scenarios).length">
            <el-tag v-for="item in getVisualItems(viewDetail.query_scenarios)" :key="`q-${item}`" class="tag-item">{{ item }}</el-tag>
          </div>
          <div v-else class="empty-text">暂无</div>
        </div>

        <div class="view-section">
          <h4>聚合场景</h4>
          <div class="tag-list" v-if="getVisualItems(viewDetail.aggregation_scenarios).length">
            <el-tag v-for="item in getVisualItems(viewDetail.aggregation_scenarios)" :key="`a-${item}`" type="success" class="tag-item">{{ item }}</el-tag>
          </div>
          <div v-else class="empty-text">暂无</div>
        </div>

        <div class="view-section">
          <h4>规则</h4>
          <div class="tag-list" v-if="getVisualItems(viewDetail.rules).length">
            <el-tag v-for="item in getVisualItems(viewDetail.rules)" :key="`r-${item}`" type="warning" class="tag-item">{{ item }}</el-tag>
          </div>
          <div v-else class="empty-text">暂无</div>
        </div>

        <div class="view-section">
          <h4>数据库使用方式</h4>
          <div class="tag-list" v-if="getVisualItems(viewDetail.database_usage).length">
            <el-tag v-for="item in getVisualItems(viewDetail.database_usage)" :key="`d-${item}`" type="info" class="tag-item">{{ item }}</el-tag>
          </div>
          <div v-else class="empty-text">暂无</div>
        </div>

        <div class="view-section">
          <h4>样例值</h4>
          <div class="sample-block" v-if="getSampleVisualItems(viewDetail.sample_values).length">
            <el-tag v-for="item in getSampleVisualItems(viewDetail.sample_values)" :key="`s-${item}`" effect="plain" class="tag-item">{{ item }}</el-tag>
          </div>
          <div v-else class="empty-text">暂无</div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showViewDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  batchDeleteTableFieldPrompt,
  createTableFieldPrompt,
  deleteTableFieldPrompt,
  getTableFieldPrompt,
  getTableFieldPromptList,
  updateTableFieldPrompt
} from '@/api/tableFieldPrompt'
import { getTableLevelPromptList } from '@/api/tableLevelPrompt'
import { getNlsqlTaskConfigList } from '@/api/nlsqlTaskConfig'

const loading = ref(false)
const saveLoading = ref(false)
const promptList = ref([])
const taskList = ref([])
const tablePromptOptions = ref([])
const selectedRows = ref([])
const tableRef = ref(null)

const showEditDialog = ref(false)
const showViewDialog = ref(false)
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
  table_level_prompt_id: null,
  field_name: '',
  business_meaning: '',
  data_format: '',
  field_description: '',
  query_scenarios: '',
  aggregation_scenarios: '',
  rules: '',
  database_usage: '',
  field_type: '',
  null_rate: '',
  unique_count: null,
  sample_values_text: ''
})

const formRules = {
  nlsql_task_id: [{ required: true, message: '请选择任务', trigger: 'change' }],
  field_name: [{ required: true, message: '请输入字段名', trigger: 'blur' }]
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

async function fetchTablePromptOptions(taskId) {
  if (!taskId) {
    tablePromptOptions.value = []
    return
  }

  try {
    const res = await getTableLevelPromptList({ page: 1, page_size: 100, task_id: taskId })
    tablePromptOptions.value = res.data || res.items || []
  } catch (error) {
    console.error('获取表级提示词选项失败:', error)
    tablePromptOptions.value = []
  }
}

async function fetchList() {
  try {
    loading.value = true
    const params = {
      page: pagination.page,
      page_size: pagination.page_size
    }

    if (searchForm.table_name) {
      params.table_name = searchForm.table_name
    }
    if (searchForm.task_id) {
      params.task_id = searchForm.task_id
    }

    const res = await getTableFieldPromptList(params)
    promptList.value = res.data || res.items || []
    pagination.total = res.pagination?.total || res.total || 0

    selectedRows.value = []
    tableRef.value?.clearSelection()
  } catch (error) {
    console.error('获取字段提示词列表失败:', error)
    ElMessage.error('获取字段提示词列表失败')
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
  if (promptList.value.length === 0 && pagination.page > 1) {
    pagination.page -= 1
    await fetchList()
  }
}

function handleCreate() {
  isEditing.value = false
  resetForm()
  fetchTablePromptOptions(searchForm.task_id)
  if (searchForm.task_id) {
    editForm.nlsql_task_id = searchForm.task_id
  }
  showEditDialog.value = true
}

async function handleEdit(row) {
  try {
    isEditing.value = true
    const res = await getTableFieldPrompt(row.id)
    const data = res.data || res

    editForm.id = data.id
    editForm.nlsql_task_id = data.nlsql_task_id
    editForm.table_level_prompt_id = data.table_level_prompt_id
    editForm.field_name = data.field_name || ''
    editForm.business_meaning = data.business_meaning || ''
    editForm.data_format = data.data_format || ''
    editForm.field_description = data.field_description || ''
    editForm.query_scenarios = toDisplayJsonText(data.query_scenarios)
    editForm.aggregation_scenarios = toDisplayJsonText(data.aggregation_scenarios)
    editForm.rules = toDisplayJsonText(data.rules)
    editForm.database_usage = toDisplayJsonText(data.database_usage)
    editForm.field_type = data.field_type || ''
    editForm.null_rate = data.null_rate || ''
    editForm.unique_count = Number.isInteger(data.unique_count) ? data.unique_count : null
    editForm.sample_values_text = toDisplaySampleText(data.sample_values)

    await fetchTablePromptOptions(data.nlsql_task_id)
    showEditDialog.value = true
  } catch (error) {
    console.error('获取字段提示词详情失败:', error)
    ElMessage.error('获取字段提示词详情失败')
  }
}

async function handleView(row) {
  try {
    const res = await getTableFieldPrompt(row.id)
    viewDetail.value = res.data || res
    showViewDialog.value = true
  } catch (error) {
    console.error('获取字段提示词详情失败:', error)
    ElMessage.error('获取字段提示词详情失败')
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除字段提示词 #${row.id}（${row.field_name}）吗？`, '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await deleteTableFieldPrompt(row.id)
    ElMessage.success('删除成功')
    await refreshListAfterDelete()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除字段提示词失败:', error)
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
    await batchDeleteTableFieldPrompt(ids)
    ElMessage.success('批量删除成功')
    await refreshListAfterDelete()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error(error.response?.data?.detail || '批量删除失败')
    }
  }
}

async function handleTaskSelectorChange(taskId) {
  editForm.table_level_prompt_id = null
  await fetchTablePromptOptions(taskId)
}

async function handleSave() {
  if (!formRef.value) {
    return
  }

  try {
    await formRef.value.validate()
    saveLoading.value = true

    if (isEditing.value) {
      const payload = buildUpdatePayload()
      await updateTableFieldPrompt(editForm.id, payload)
      ElMessage.success('更新成功')
    } else {
      const payload = buildCreatePayload()
      await createTableFieldPrompt(payload)
      ElMessage.success('创建成功')
    }

    showEditDialog.value = false
    await fetchList()
  } catch (error) {
    console.error('保存字段提示词失败:', error)
    ElMessage.error(error.response?.data?.detail || error.message || '保存失败')
  } finally {
    saveLoading.value = false
  }
}

function buildCreatePayload() {
  return {
    nlsql_task_id: Number(editForm.nlsql_task_id),
    table_level_prompt_id: editForm.table_level_prompt_id ? Number(editForm.table_level_prompt_id) : null,
    field_name: editForm.field_name.trim(),
    business_meaning: normalizeOptionalText(editForm.business_meaning),
    data_format: normalizeOptionalText(editForm.data_format),
    field_description: normalizeOptionalText(editForm.field_description),
    query_scenarios: normalizeJsonString(editForm.query_scenarios),
    aggregation_scenarios: normalizeJsonString(editForm.aggregation_scenarios),
    rules: normalizeJsonString(editForm.rules),
    database_usage: normalizeJsonString(editForm.database_usage),
    field_type: normalizeOptionalText(editForm.field_type),
    null_rate: normalizeOptionalText(editForm.null_rate),
    unique_count: editForm.unique_count === null ? null : Number(editForm.unique_count),
    sample_values: parseSampleValues(editForm.sample_values_text)
  }
}

function buildUpdatePayload() {
  return {
    business_meaning: normalizeOptionalText(editForm.business_meaning),
    data_format: normalizeOptionalText(editForm.data_format),
    field_description: normalizeOptionalText(editForm.field_description),
    query_scenarios: normalizeJsonString(editForm.query_scenarios),
    aggregation_scenarios: normalizeJsonString(editForm.aggregation_scenarios),
    rules: normalizeJsonString(editForm.rules),
    database_usage: normalizeJsonString(editForm.database_usage),
    field_type: normalizeOptionalText(editForm.field_type),
    null_rate: normalizeOptionalText(editForm.null_rate),
    unique_count: editForm.unique_count === null ? null : Number(editForm.unique_count),
    sample_values: parseSampleValues(editForm.sample_values_text)
  }
}

function normalizeOptionalText(value) {
  const text = (value || '').trim()
  return text || null
}

function normalizeJsonString(value) {
  const text = (value || '').trim()
  if (!text) {
    return null
  }

  try {
    const parsed = JSON.parse(text)
    return JSON.stringify(parsed)
  } catch (_error) {
    const lines = text.split('\n').map(item => item.trim()).filter(Boolean)
    return lines.length > 0 ? JSON.stringify(lines) : null
  }
}

function parseSampleValues(value) {
  const text = (value || '').trim()
  if (!text) {
    return []
  }

  try {
    const parsed = JSON.parse(text)
    if (Array.isArray(parsed)) {
      return parsed
    }
    return [parsed]
  } catch (_error) {
    return text.split('\n').map(item => item.trim()).filter(Boolean)
  }
}

function toDisplayJsonText(value) {
  if (value === null || value === undefined || value === '') {
    return ''
  }

  if (typeof value !== 'string') {
    return JSON.stringify(value, null, 2)
  }

  try {
    const parsed = JSON.parse(value)
    return JSON.stringify(parsed, null, 2)
  } catch (_error) {
    return value
  }
}

function toDisplaySampleText(value) {
  if (!value) {
    return ''
  }
  return JSON.stringify(value, null, 2)
}

function getVisualItems(value) {
  if (value === null || value === undefined || value === '') {
    return []
  }

  if (Array.isArray(value)) {
    return value.map(item => String(item)).filter(Boolean)
  }

  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)
      if (Array.isArray(parsed)) {
        return parsed.map(item => String(item)).filter(Boolean)
      }
      if (parsed && typeof parsed === 'object') {
        return [JSON.stringify(parsed)]
      }
      return [String(parsed)]
    } catch (_error) {
      return value.split('\n').map(item => item.trim()).filter(Boolean)
    }
  }

  if (typeof value === 'object') {
    return [JSON.stringify(value)]
  }

  return [String(value)]
}

function getSampleVisualItems(value) {
  if (!value) {
    return []
  }
  if (Array.isArray(value)) {
    return value.map(item => String(item)).filter(Boolean)
  }
  return getVisualItems(value)
}

function resetForm() {
  editForm.id = null
  editForm.nlsql_task_id = null
  editForm.table_level_prompt_id = null
  editForm.field_name = ''
  editForm.business_meaning = ''
  editForm.data_format = ''
  editForm.field_description = ''
  editForm.query_scenarios = ''
  editForm.aggregation_scenarios = ''
  editForm.rules = ''
  editForm.database_usage = ''
  editForm.field_type = ''
  editForm.null_rate = ''
  editForm.unique_count = null
  editForm.sample_values_text = ''

  if (formRef.value) {
    formRef.value.resetFields()
  }
}

function formatDate(value) {
  if (!value) {
    return '-'
  }
  return new Date(value).toLocaleString('zh-CN')
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

.search-input {
  width: 220px;
}

.task-select {
  width: 220px;
}

.table-card {
  max-height: calc(100vh - 240px);
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

.view-section {
  margin-top: 18px;
}

.view-section h4 {
  margin: 0 0 10px;
  font-size: 14px;
  color: #303133;
}

.tag-list,
.sample-block {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-item {
  max-width: 100%;
}

.empty-text {
  color: #909399;
  font-size: 13px;
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
