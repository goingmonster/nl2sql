<template>
  <div class="table-metadata-view">
    <div class="card">
      <h2 class="card-title">表级别提示词管理</h2>
      <p class="page-desc">管理表级别提示词信息，支持按表名和任务ID筛选，可进行增删改查操作</p>

      <!-- 搜索筛选区域 -->
      <div class="search-section">
        <el-input
          v-model="searchForm.table_name"
          placeholder="搜索表名称"
          clearable
          @input="handleSearch"
          class="search-input"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-select
          v-model="searchForm.task_id"
          placeholder="选择任务ID"
          clearable
          @change="handleTaskChange"
          class="task-select"
        >
          <el-option
            v-for="task in taskList"
            :key="task.id"
            :label="`${task.id} - ${task.description || '无描述'}`"
            :value="task.id"
          />
        </el-select>

        <el-button type="primary" @click="handleCreate" class="create-btn">
          <el-icon><Plus /></el-icon>
          新增提示词
        </el-button>

        <el-button type="danger" @click="handleBatchDelete" :disabled="selectedRows.length === 0" class="batch-delete-btn">
          批量删除 ({{ selectedRows.length }})
        </el-button>
      </div>

    <div class="card">
      <div class="table-container">
        <el-table
          v-loading="loading"
          :data="promptList"
          style="width: 100%"
          @selection-change="handleSelectionChange"
        >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="table_name" label="表名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="task_id" label="任务ID" width="100">
          <template #default="scope">
            <el-link type="primary" @click="handleViewTask(scope.row.task_id)">
              {{ scope.row.task_id }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="table_description" label="表描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.is_active ? 'success' : 'info'">
              {{ scope.row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="scope">
            <el-link type="primary" @click="handleViewDetails(scope.row)">查看</el-link>
            <el-divider direction="vertical" />
            <el-link type="primary" @click="handleEdit(scope.row)">编辑</el-link>
            <el-divider direction="vertical" />
            <el-link type="danger" @click="handleDelete(scope.row)">删除</el-link>
          </template>
        </el-table-column>
      </el-table>
      </div>

      </div>
    </div>

    <!-- 分页 -->
    <div class="compact-pagination">
      <div class="pagination-content">
        <span class="record-count">{{ pagination.total }}</span>
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          size="small"
          layout="prev, pager, next, sizes"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
          :background="false"
        />
      </div>
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="showEditDialog"
      :title="isEditing ? '编辑表级别提示词' : '新增表级别提示词'"
      width="900px"
      @close="resetForm"
    >
      <el-form :model="editForm" :rules="formRules" ref="formRef" label-width="120px">
        <el-form-item label="表名称" prop="table_name">
          <el-input v-model="editForm.table_name" placeholder="请输入表名称" />
        </el-form-item>
        <el-form-item label="任务ID" prop="task_id">
          <el-select v-model="editForm.task_id" placeholder="请选择任务" style="width: 100%">
            <el-option
              v-for="task in taskList"
              :key="task.id"
              :label="`${task.id} - ${task.description || '无描述'}`"
              :value="task.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="表描述" prop="table_description">
          <el-input
            v-model="editForm.table_description"
            type="textarea"
            :rows="3"
            placeholder="请输入表描述"
          />
        </el-form-item>
        <el-form-item label="查询场景">
          <el-input
            v-model="queryScenariosText"
            type="textarea"
            :rows="3"
            placeholder="每行输入一个查询场景"
          />
          <div class="help-text">每行输入一个查询场景，保存时会自动转换为数组</div>
        </el-form-item>
        <el-form-item label="聚合场景">
          <el-input
            v-model="aggregationScenariosText"
            type="textarea"
            :rows="3"
            placeholder="每行输入一个聚合场景"
          />
          <div class="help-text">每行输入一个聚合场景，保存时会自动转换为数组</div>
        </el-form-item>
        <el-form-item label="数据角色">
          <el-input
            v-model="dataRoleText"
            type="textarea"
            :rows="2"
            placeholder="每行输入一个数据角色"
          />
          <div class="help-text">每行输入一个数据角色，保存时会自动转换为数组</div>
        </el-form-item>
        <el-form-item label="使用例外">
          <el-input
            v-model="usageNotScenariosText"
            type="textarea"
            :rows="2"
            placeholder="每行输入一个使用例外"
          />
          <div class="help-text">每行输入一个使用例外，保存时会自动转换为数组</div>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch
            v-model="editForm.is_active"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saveLoading">保存</el-button>
      </template>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-dialog
      v-model="showDetailsDialog"
      title="表级别提示词详情"
      width="900px"
    >
      <div v-if="selectedPrompt" class="prompt-details">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="ID">{{ selectedPrompt.id }}</el-descriptions-item>
          <el-descriptions-item label="表名称">{{ selectedPrompt.table_name }}</el-descriptions-item>
          <el-descriptions-item label="任务ID">
            <el-link type="primary" @click="handleViewTask(selectedPrompt.task_id)">
              {{ selectedPrompt.task_id }}
            </el-link>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="selectedPrompt.is_active ? 'success' : 'info'">
              {{ selectedPrompt.is_active ? '启用' : '禁用' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间" span="2">{{ formatDate(selectedPrompt.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间" span="2">{{ formatDate(selectedPrompt.updated_at) }}</el-descriptions-item>
          <el-descriptions-item label="表描述" span="2">{{ selectedPrompt.table_description || '暂无描述' }}</el-descriptions-item>
        </el-descriptions>

        <div v-if="selectedPrompt.query_scenarios && selectedPrompt.query_scenarios.length > 0" style="margin-top: 20px;">
          <h4>查询场景：</h4>
          <el-tag v-for="item in selectedPrompt.query_scenarios" :key="item" style="margin-right: 10px; margin-bottom: 10px;">
            {{ item }}
          </el-tag>
        </div>

        <div v-if="selectedPrompt.aggregation_scenarios && selectedPrompt.aggregation_scenarios.length > 0" style="margin-top: 20px;">
          <h4>聚合场景：</h4>
          <el-tag v-for="item in selectedPrompt.aggregation_scenarios" :key="item" style="margin-right: 10px; margin-bottom: 10px;">
            {{ item }}
          </el-tag>
        </div>

        <div v-if="selectedPrompt.data_role && selectedPrompt.data_role.length > 0" style="margin-top: 20px;">
          <h4>数据角色：</h4>
          <el-tag v-for="item in selectedPrompt.data_role" :key="item" style="margin-right: 10px; margin-bottom: 10px;">
            {{ item }}
          </el-tag>
        </div>

        <div v-if="selectedPrompt.usage_not_scenarios && selectedPrompt.usage_not_scenarios.length > 0" style="margin-top: 20px;">
          <h4>使用例外：</h4>
          <el-tag v-for="item in selectedPrompt.usage_not_scenarios" :key="item" style="margin-right: 10px; margin-bottom: 10px;">
            {{ item }}
          </el-tag>
        </div>

        <div v-if="selectedPrompt.system_config" style="margin-top: 20px;">
          <h4>系统配置：</h4>
          <el-input
            v-model="selectedPrompt.system_config"
            type="textarea"
            :rows="4"
            readonly
          />
        </div>

        <div v-if="selectedPrompt.table_notes && selectedPrompt.table_notes.length > 0" style="margin-top: 20px;">
          <h4>表注释：</h4>
          <el-tag v-for="item in selectedPrompt.table_notes" :key="item" style="margin-right: 10px; margin-bottom: 10px;">
            {{ item }}
          </el-tag>
        </div>
      </div>
      <template #footer>
        <el-button @click="showDetailsDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive, computed } from 'vue'
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getTableLevelPromptList,
  deleteTableLevelPrompt,
  batchDeleteTableLevelPrompt,
  createTableLevelPrompt,
  updateTableLevelPrompt,
  getTableLevelPrompt
} from '@/api/tableLevelPrompt'
import { getNlsqlTaskConfigList } from '@/api/nlsqlTaskConfig'

// 响应式数据
const loading = ref(false)
const saveLoading = ref(false)
const promptList = ref([])
const taskList = ref([])
const selectedRows = ref([])
const showDetailsDialog = ref(false)
const showEditDialog = ref(false)
const selectedPrompt = ref(null)
const isEditing = ref(false)
const formRef = ref(null)

// 搜索表单
const searchForm = reactive({
  table_name: '',
  task_id: null
})

// 编辑表单
const editForm = reactive({
  id: null,
  table_name: '',
  task_id: null,
  table_description: '',
  is_active: true
})

// 分页信息
const pagination = reactive({
  page: 1,
  page_size: 10,
  total: 0
})

// 表单验证规则
const formRules = {
  table_name: [
    { required: true, message: '请输入表名称', trigger: 'blur' }
  ],
  task_id: [
    { required: true, message: '请选择任务', trigger: 'change' }
  ]
}

// 文本字段（用于数组字段的编辑）
const queryScenariosText = ref('')
const aggregationScenariosText = ref('')
const dataRoleText = ref('')
const usageNotScenariosText = ref('')

// 获取任务列表
async function fetchTaskList() {
  try {
    const res = await getNlsqlTaskConfigList({ page: 1, page_size: 100 })
    taskList.value = res.items || []
  } catch (error) {
    console.error('获取任务列表失败:', error)
    ElMessage.error('获取任务列表失败')
  }
}

// 获取提示词列表
async function fetchList() {
  try {
    loading.value = true
    const params = {
      page: pagination.page,
      page_size: pagination.page_size
    }

    // 只有在有值的情况下才添加筛选参数
    if (searchForm.table_name) {
      params.table_name = searchForm.table_name
    }
    if (searchForm.task_id) {
      params.task_id = searchForm.task_id
    }

    console.log('发送的参数:', params)
    const res = await getTableLevelPromptList(params)
    promptList.value = res.data || res.items || []
    pagination.total = res.pagination?.total || res.total || 0
  } catch (error) {
    console.error('获取提示词列表失败:', error)
    console.error('错误详情:', error.response?.data)
    ElMessage.error('获取提示词列表失败')
  } finally {
    loading.value = false
  }
}

// 搜索处理（防抖）
let searchTimer = null
function handleSearch() {
  if (searchTimer) {
    clearTimeout(searchTimer)
  }
  searchTimer = setTimeout(() => {
    pagination.page = 1
    fetchList()
  }, 500)
}

// 任务选择变化
function handleTaskChange() {
  pagination.page = 1
  fetchList()
}

// 表格选择变化
function handleSelectionChange(selection) {
  selectedRows.value = selection
}

// 分页处理
function handleSizeChange(size) {
  pagination.page_size = size
  pagination.page = 1
  fetchList()
}

function handleCurrentChange(page) {
  pagination.page = page
  fetchList()
}

// 查看详情
async function handleViewDetails(row) {
  try {
    const res = await getTableLevelPrompt(row.id)
    selectedPrompt.value = res.data || res
    showDetailsDialog.value = true
  } catch (error) {
    console.error('获取详情失败:', error)
    ElMessage.error('获取详情失败')
  }
}

// 新增
function handleCreate() {
  isEditing.value = false
  resetForm()
  showEditDialog.value = true
}

// 编辑
async function handleEdit(row) {
  try {
    isEditing.value = true
    const res = await getTableLevelPrompt(row.id)
    const data = res.data || res

    // 填充表单
    editForm.id = data.id
    editForm.table_name = data.table_name
    editForm.task_id = data.task_id
    editForm.table_description = data.table_description
    editForm.is_active = data.is_active

    // 填充数组字段为文本
    queryScenariosText.value = (data.query_scenarios || []).join('\n')
    aggregationScenariosText.value = (data.aggregation_scenarios || []).join('\n')
    dataRoleText.value = (data.data_role || []).join('\n')
    usageNotScenariosText.value = (data.usage_not_scenarios || []).join('\n')

    showEditDialog.value = true
  } catch (error) {
    console.error('获取编辑数据失败:', error)
    ElMessage.error('获取编辑数据失败')
  }
}

// 保存
async function handleSave() {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    saveLoading.value = true

    // 准备提交数据
    const submitData = {
      table_name: editForm.table_name,
      task_id: parseInt(editForm.task_id, 10),
      table_description: editForm.table_description,
      query_scenarios: queryScenariosText.value.split('\n').filter(item => item.trim()),
      aggregation_scenarios: aggregationScenariosText.value.split('\n').filter(item => item.trim()),
      data_role: dataRoleText.value.split('\n').filter(item => item.trim()),
      usage_not_scenarios: usageNotScenariosText.value.split('\n').filter(item => item.trim()),
      is_active: editForm.is_active,
      system_config: selectedPrompt.value?.system_config || '',
      table_notes: selectedPrompt.value?.table_notes || []
    }

    if (isEditing.value) {
      await updateTableLevelPrompt(editForm.id, submitData)
      ElMessage.success('更新成功')
    } else {
      await createTableLevelPrompt(submitData)
      ElMessage.success('创建成功')
    }

    showEditDialog.value = false
    fetchList()
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error(error.response?.data?.detail || '保存失败')
  } finally {
    saveLoading.value = false
  }
}

// 删除
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除表 ${row.table_name} 的提示词吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await deleteTableLevelPrompt(row.id)
    ElMessage.success('删除成功')
    fetchList()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

// 批量删除
async function handleBatchDelete() {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请选择要删除的记录')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedRows.value.length} 条记录吗？`,
      '批量删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const ids = selectedRows.value.map(item => item.id)
    await batchDeleteTableLevelPrompt(ids)
    ElMessage.success('批量删除成功')
    fetchList()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error('批量删除失败')
    }
  }
}

// 查看任务详情
function handleViewTask(taskId) {
  // 这里可以跳转到任务详情页面或打开任务对话框
  ElMessage.info(`查看任务 ID: ${taskId}`)
}

// 重置表单
function resetForm() {
  editForm.id = null
  editForm.table_name = ''
  editForm.task_id = null
  editForm.table_description = ''
  editForm.is_active = true

  queryScenariosText.value = ''
  aggregationScenariosText.value = ''
  dataRoleText.value = ''
  usageNotScenariosText.value = ''

  if (formRef.value) {
    formRef.value.resetFields()
  }
}

// 格式化日期
function formatDate(dateString) {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

// 组件挂载时获取数据
onMounted(() => {
  fetchTaskList()
  fetchList()
})
</script>

<style scoped>
.page-desc {
  color: var(--text-secondary);
  margin-bottom: 20px;
}

/* 搜索区域样式 */
.search-section {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  padding: 12px 16px;
  background: linear-gradient(to right, #f8fafc, #ffffff);
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.search-input {
  flex: 1;
  max-width: 200px;
}

.task-select {
  width: 200px;
}

.create-btn {
  flex-shrink: 0;
}

.batch-delete-btn {
  flex-shrink: 0;
  min-width: 100px;
}

/* 响应式搜索区域 */
@media (max-width: 1200px) {
  .search-section {
    gap: 8px;
    padding: 10px;
  }

  .search-input {
    max-width: 160px;
  }

  .task-select {
    width: 160px;
  }
}

@media (max-width: 768px) {
  .search-section {
    flex-direction: column;
    gap: 10px;
  }

  .search-input,
  .task-select,
  .create-btn,
  .batch-delete-btn {
    width: 100%;
    max-width: none;
  }
}

/* 表格样式 */
.card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  border: 1px solid #ebeef5;
  margin-bottom: 20px;
  max-height: calc(100vh - 200px);
}

.table-container {
  flex: 1;
  overflow-y: auto;
  max-height: calc(100vh - 120px);
  background: white;
  min-height: 400px;
}

/* 分页器样式 */
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
  background: white;
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

/* 详情对话框样式 */
.prompt-details {
  max-height: 600px;
  overflow-y: auto;
}

.help-text {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

/* 第一个卡片特殊样式 */
.card:first-child {
  background: transparent;
  border: none;
  box-shadow: none;
  margin-bottom: 0;
}

/* 响应式设计 */
@media (max-height: 800px) {
  .table-container {
    max-height: calc(100vh - 100px);
    min-height: 300px;
  }

  .compact-pagination {
    bottom: 15px;
  }
}

@media (max-height: 600px) {
  .table-container {
    max-height: calc(100vh - 90px);
    min-height: 200px;
  }

  .compact-pagination {
    bottom: 10px;
  }

  .pagination-content {
    padding: 4px 10px;
  }
}

@media (max-width: 768px) {
  .compact-pagination {
    left: 20px;
    right: 20px;
    bottom: 15px;
  }

  .card {
    max-height: calc(100vh - 180px);
  }

  .table-container {
    max-height: calc(100vh - 120px);
    min-height: 200px;
  }

  .pagination-content {
    flex-direction: column;
    gap: 10px;
    align-items: center;
    padding: 15px;
  }

  .el-pagination {
    justify-content: center;
  }
}
</style>