<template>
  <div class="table-metadata-view">
    <div class="card search-card">
      <h2 class="card-title">实体关系</h2>
      <p class="page-desc">管理两张表之间的字段关联关系，支持按表名和任务筛选、分页查询、增删改查</p>

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
          :data="relationList"
          style="width: 100%"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="55" />
          <el-table-column prop="id" label="ID" width="90" />
          <el-table-column prop="source_table_name" label="源表" min-width="140" show-overflow-tooltip />
          <el-table-column prop="source_field_name" label="源字段" min-width="140" show-overflow-tooltip />
          <el-table-column prop="target_table_name" label="目标表" min-width="140" show-overflow-tooltip />
          <el-table-column prop="target_field_name" label="目标字段" min-width="140" show-overflow-tooltip />
          <el-table-column prop="relation_type" label="关联类型" width="120" show-overflow-tooltip />
          <el-table-column label="置信度" width="120">
            <template #default="scope">
              <el-tag type="success" effect="plain">{{ formatConfidence(scope.row.confidence) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="scope">
              {{ formatDate(scope.row.created_at) }}
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
      :title="isEditing ? '编辑实体关系' : '新增实体关系'"
      width="960px"
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
            <el-form-item label="关联类型" prop="relation_type">
              <el-input v-model="editForm.relation_type" placeholder="例如：foreign_key / business_key" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="源表名" prop="source_table_name">
              <el-input v-model="editForm.source_table_name" placeholder="例如：orders" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="源字段名" prop="source_field_name">
              <el-input v-model="editForm.source_field_name" placeholder="例如：user_id" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="目标表名" prop="target_table_name">
              <el-input v-model="editForm.target_table_name" placeholder="例如：users" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目标字段名" prop="target_field_name">
              <el-input v-model="editForm.target_field_name" placeholder="例如：id" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="置信度(0-1)">
              <el-input v-model="editForm.confidence" placeholder="例如：0.85" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="源表提示词ID">
              <el-input-number v-model="editForm.source_table_level_prompt_id" :min="1" :controls="false" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="目标表提示词ID">
              <el-input-number v-model="editForm.target_table_level_prompt_id" :min="1" :controls="false" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="源字段提示词ID">
              <el-input-number v-model="editForm.source_table_field_prompt_id" :min="1" :controls="false" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="目标字段提示词ID">
              <el-input-number v-model="editForm.target_table_field_prompt_id" :min="1" :controls="false" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12" />
        </el-row>

        <el-form-item label="关联描述">
          <el-input
            v-model="editForm.relation_description"
            type="textarea"
            :rows="3"
            placeholder="请输入两张表字段之间的关联说明"
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
      title="实体关系可视化"
      width="980px"
    >
      <div v-if="viewDetail" class="view-detail-wrap">
        <div class="relation-summary">
          <el-tag type="primary" effect="dark">任务 {{ viewDetail.nlsql_task_id }}</el-tag>
          <el-tag type="success" effect="plain">{{ viewDetail.relation_type || '未定义类型' }}</el-tag>
          <el-tag type="warning" effect="plain">置信度 {{ formatConfidence(viewDetail.confidence) }}</el-tag>
        </div>

        <div class="relation-visual-panel">
          <div class="table-box source-box">
            <div class="table-title">源表</div>
            <div class="table-name">{{ viewDetail.source_table_name || '-' }}</div>
            <div class="field-chip">{{ viewDetail.source_field_name || '-' }}</div>
          </div>

          <div class="relation-bridge">
            <div class="relation-type-pill">{{ viewDetail.relation_type || 'relation' }}</div>
            <div class="relation-line">
              <span class="line" />
              <span class="arrow">→</span>
            </div>
          </div>

          <div class="table-box target-box">
            <div class="table-title">目标表</div>
            <div class="table-name">{{ viewDetail.target_table_name || '-' }}</div>
            <div class="field-chip">{{ viewDetail.target_field_name || '-' }}</div>
          </div>
        </div>

        <div class="description-card">
          <div class="description-title">关系说明</div>
          <div class="description-content">{{ viewDetail.relation_description || '暂无关系说明' }}</div>
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
  batchDeleteTableFieldRelation,
  createTableFieldRelation,
  deleteTableFieldRelation,
  getTableFieldRelation,
  getTableFieldRelationList,
  updateTableFieldRelation
} from '@/api/tableFieldRelation'
import { getNlsqlTaskConfigList } from '@/api/nlsqlTaskConfig'

const loading = ref(false)
const saveLoading = ref(false)
const relationList = ref([])
const taskList = ref([])
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
  source_table_field_prompt_id: null,
  source_table_level_prompt_id: null,
  source_table_name: '',
  source_field_name: '',
  target_table_field_prompt_id: null,
  target_table_level_prompt_id: null,
  target_table_name: '',
  target_field_name: '',
  relation_type: '',
  relation_description: '',
  confidence: ''
})

const formRules = {
  nlsql_task_id: [{ required: true, message: '请选择任务', trigger: 'change' }],
  relation_type: [{ required: true, message: '请输入关联类型', trigger: 'blur' }],
  source_table_name: [{ required: true, message: '请输入源表名', trigger: 'blur' }],
  source_field_name: [{ required: true, message: '请输入源字段名', trigger: 'blur' }],
  target_table_name: [{ required: true, message: '请输入目标表名', trigger: 'blur' }],
  target_field_name: [{ required: true, message: '请输入目标字段名', trigger: 'blur' }]
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

    const res = await getTableFieldRelationList(params)
    relationList.value = res.data || res.items || []
    pagination.total = res.pagination?.total || res.total || 0

    selectedRows.value = []
    tableRef.value?.clearSelection()
  } catch (error) {
    console.error('获取实体关系列表失败:', error)
    ElMessage.error('获取实体关系列表失败')
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
  if (relationList.value.length === 0 && pagination.page > 1) {
    pagination.page -= 1
    await fetchList()
  }
}

function handleCreate() {
  isEditing.value = false
  resetForm()
  if (searchForm.task_id) {
    editForm.nlsql_task_id = searchForm.task_id
  }
  showEditDialog.value = true
}

async function handleEdit(row) {
  try {
    isEditing.value = true
    const res = await getTableFieldRelation(row.id)
    const data = res.data || res

    editForm.id = data.id
    editForm.nlsql_task_id = data.nlsql_task_id
    editForm.source_table_field_prompt_id = data.source_table_field_prompt_id || null
    editForm.source_table_level_prompt_id = data.source_table_level_prompt_id || null
    editForm.source_table_name = data.source_table_name || ''
    editForm.source_field_name = data.source_field_name || ''
    editForm.target_table_field_prompt_id = data.target_table_field_prompt_id || null
    editForm.target_table_level_prompt_id = data.target_table_level_prompt_id || null
    editForm.target_table_name = data.target_table_name || ''
    editForm.target_field_name = data.target_field_name || ''
    editForm.relation_type = data.relation_type || ''
    editForm.relation_description = data.relation_description || ''
    editForm.confidence = data.confidence || ''

    showEditDialog.value = true
  } catch (error) {
    console.error('获取实体关系详情失败:', error)
    ElMessage.error('获取实体关系详情失败')
  }
}

async function handleView(row) {
  try {
    const res = await getTableFieldRelation(row.id)
    viewDetail.value = res.data || res
    showViewDialog.value = true
  } catch (error) {
    console.error('获取实体关系详情失败:', error)
    ElMessage.error('获取实体关系详情失败')
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除实体关系 #${row.id} 吗？`, '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await deleteTableFieldRelation(row.id)
    ElMessage.success('删除成功')
    await refreshListAfterDelete()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除实体关系失败:', error)
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
    await batchDeleteTableFieldRelation(ids)
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

    if (isEditing.value) {
      const payload = buildUpdatePayload()
      await updateTableFieldRelation(editForm.id, payload)
      ElMessage.success('更新成功')
    } else {
      const payload = buildCreatePayload()
      await createTableFieldRelation(payload)
      ElMessage.success('创建成功')
    }

    showEditDialog.value = false
    await fetchList()
  } catch (error) {
    console.error('保存实体关系失败:', error)
    ElMessage.error(error.response?.data?.detail || error.message || '保存失败')
  } finally {
    saveLoading.value = false
  }
}

function buildCreatePayload() {
  return {
    nlsql_task_id: Number(editForm.nlsql_task_id),
    source_table_field_prompt_id: normalizeOptionalNumber(editForm.source_table_field_prompt_id),
    source_table_level_prompt_id: normalizeOptionalNumber(editForm.source_table_level_prompt_id),
    source_table_name: normalizeOptionalText(editForm.source_table_name),
    source_field_name: normalizeOptionalText(editForm.source_field_name),
    target_table_field_prompt_id: normalizeOptionalNumber(editForm.target_table_field_prompt_id),
    target_table_level_prompt_id: normalizeOptionalNumber(editForm.target_table_level_prompt_id),
    target_table_name: normalizeOptionalText(editForm.target_table_name),
    target_field_name: normalizeOptionalText(editForm.target_field_name),
    relation_type: normalizeOptionalText(editForm.relation_type),
    relation_description: normalizeOptionalText(editForm.relation_description),
    confidence: normalizeConfidence(editForm.confidence)
  }
}

function buildUpdatePayload() {
  return {
    source_table_field_prompt_id: normalizeOptionalNumber(editForm.source_table_field_prompt_id),
    source_table_level_prompt_id: normalizeOptionalNumber(editForm.source_table_level_prompt_id),
    source_table_name: normalizeOptionalText(editForm.source_table_name),
    source_field_name: normalizeOptionalText(editForm.source_field_name),
    target_table_field_prompt_id: normalizeOptionalNumber(editForm.target_table_field_prompt_id),
    target_table_level_prompt_id: normalizeOptionalNumber(editForm.target_table_level_prompt_id),
    target_table_name: normalizeOptionalText(editForm.target_table_name),
    target_field_name: normalizeOptionalText(editForm.target_field_name),
    relation_type: normalizeOptionalText(editForm.relation_type),
    relation_description: normalizeOptionalText(editForm.relation_description),
    confidence: normalizeConfidence(editForm.confidence)
  }
}

function normalizeOptionalText(value) {
  const text = (value || '').trim()
  return text || null
}

function normalizeOptionalNumber(value) {
  if (value === null || value === undefined || value === '') {
    return null
  }
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

function normalizeConfidence(value) {
  const text = (value || '').toString().trim()
  if (!text) {
    return null
  }
  const number = Number(text)
  if (!Number.isFinite(number)) {
    return text
  }
  if (number < 0) {
    return '0'
  }
  if (number > 1) {
    return '1'
  }
  return number.toString()
}

function formatConfidence(value) {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const number = Number(value)
  if (!Number.isFinite(number)) {
    return String(value)
  }
  return `${Math.round(number * 100)}%`
}

function resetForm() {
  editForm.id = null
  editForm.nlsql_task_id = null
  editForm.source_table_field_prompt_id = null
  editForm.source_table_level_prompt_id = null
  editForm.source_table_name = ''
  editForm.source_field_name = ''
  editForm.target_table_field_prompt_id = null
  editForm.target_table_level_prompt_id = null
  editForm.target_table_name = ''
  editForm.target_field_name = ''
  editForm.relation_type = ''
  editForm.relation_description = ''
  editForm.confidence = ''

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

.relation-summary {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.relation-visual-panel {
  display: grid;
  grid-template-columns: 1fr 220px 1fr;
  gap: 14px;
  align-items: center;
  background: linear-gradient(135deg, #f8fbff, #fdfefe);
  border: 1px solid #e7eef7;
  border-radius: 12px;
  padding: 18px;
}

.table-box {
  border-radius: 10px;
  padding: 14px;
  background: #fff;
  border: 1px solid #e5eaf3;
  box-shadow: 0 6px 16px rgba(41, 89, 142, 0.08);
}

.source-box {
  border-left: 4px solid #409eff;
}

.target-box {
  border-left: 4px solid #67c23a;
}

.table-title {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}

.table-name {
  font-size: 17px;
  color: #303133;
  font-weight: 600;
  margin-bottom: 8px;
  word-break: break-all;
}

.field-chip {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  background: #f3f8ff;
  color: #3a78c1;
  font-size: 13px;
  word-break: break-all;
}

.relation-bridge {
  text-align: center;
}

.relation-type-pill {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  color: #fff;
  background: linear-gradient(90deg, #409eff, #36cfc9);
  margin-bottom: 10px;
}

.relation-line {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.relation-line .line {
  display: inline-block;
  width: 120px;
  height: 2px;
  background: linear-gradient(90deg, #409eff, #67c23a);
}

.relation-line .arrow {
  color: #67c23a;
  font-size: 18px;
  font-weight: 600;
}

.description-card {
  margin-top: 16px;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  padding: 14px;
  background: #fff;
}

.description-title {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
}

.description-content {
  color: #303133;
  line-height: 1.7;
  white-space: pre-wrap;
}

@media (max-width: 1200px) {
  .search-section {
    gap: 8px;
    padding: 10px;
    flex-wrap: wrap;
  }
}

@media (max-width: 900px) {
  .relation-visual-panel {
    grid-template-columns: 1fr;
  }

  .relation-line .line {
    width: 100px;
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
