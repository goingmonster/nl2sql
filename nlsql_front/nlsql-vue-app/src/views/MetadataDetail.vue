<template>
  <div class="metadata-detail-container">
    <div class="metadata-detail-header">
      <div class="header-left">
        <h2>详细元数据管理</h2>
        <el-button
          v-if="selectedTables.length > 0"
          type="danger"
          @click="handleBatchDelete"
          :loading="batchDeleting"
          size="small"
        >
          批量删除 ({{ selectedTables.length }})
        </el-button>
      </div>
      <el-select
        v-model="selectedTaskId"
        placeholder="请选择任务ID"
        style="width: 300px"
        @change="handleTaskChange"
        clearable
      >
        <el-option
          v-for="task in taskList"
          :key="task.id"
          :label="`${task.id} - ${task.description || '无描述'}`"
          :value="task.id"
        />
      </el-select>
    </div>

    <div class="metadata-content" v-loading="loading">
      <!-- 空 -->
      <el-alert v-if="metadata && (!metadata.tables || metadata.tables.length === 0)"
                title="该任务没有元数据，请先执行元数据扫描" type="warning" />

      <!-- 任务基本信息 -->
      <el-card class="info-card" v-if="metadata && metadata.tables">
        <template #header>
          <div class="card-header">
            <span>任务基本信息</span>
            <el-tag :type="getTaskStatusTagType(metadata.status)">
              {{ getTaskStatusLabel(metadata.status) }}
            </el-tag>
          </div>
        </template>
        <el-descriptions :column="3" border>
          <el-descriptions-item label="任务ID">{{ metadata.task_id }}</el-descriptions-item>
          <el-descriptions-item label="数据库配置ID">{{ metadata.db_config_id }}</el-descriptions-item>
          <el-descriptions-item label="总表数">{{ metadata.total_tables }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 表元数据列表 -->
      <div class="card">
        <div class="table-container">
          <el-table
            :data="currentTables"
            style="width: 100%"
            @selection-change="handleSelectionChange"
          >
            <el-table-column type="selection" width="55" />
            <el-table-column label="表ID" width="80" prop="table_id" show-overflow-tooltip />
            <el-table-column label="Schema" width="120" prop="schema_name" show-overflow-tooltip />
            <el-table-column label="表名称" min-width="200" show-overflow-tooltip>
              <template #default="{ row }">
                <el-link type="primary" @click="handleViewTableDetail(row)">
                  {{ row.table_name }}
                </el-link>
              </template>
            </el-table-column>
            <el-table-column label="表类型" width="100">
              <template #default="{ row }">
                <el-tag :type="getTableTypeTagType(row.table_type)">
                  {{ row.table_type || 'TABLE' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="数据行数" width="120">
              <template #default="{ row }">
                <el-tag type="success" size="small">
                  {{ Number(row.table_row_count).toLocaleString() }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="table_description" label="描述" min-width="200" show-overflow-tooltip />
            <el-table-column label="创建时间" width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.created_at) }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

    <!-- 小巧的分页器 -->
    <div class="compact-pagination">
      <div class="pagination-content">
        <span class="record-count">{{ tablePagination.total }}</span>
        <el-pagination
          v-model:current-page="tablePagination.currentPage"
          v-model:page-size="tablePagination.pageSize"
          :page-sizes="[5, 10, 20, 50]"
          :total="tablePagination.total"
          size="small"
          layout="prev, pager, next, sizes"
          :background="false"
          @size-change="handleTableSizeChange"
          @current-change="handleTablePageChange"
        />
      </div>
    </div>
    </div>

    <!-- 表详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      :title="`${selectedTable?.schema_name}.${selectedTable?.table_name} - 详细信息`"
      width="90%"
      top="5vh"
      destroy-on-close
    >
      <div v-if="selectedTable" class="table-detail-content">
        <!-- 表统计信息 -->
        <el-row :gutter="20" style="margin-bottom: 20px;">
          <el-col :span="8">
            <el-statistic title="数据行数" :value="Number(selectedTable.table_row_count)" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="字段数量" :value="selectedTable.field_metadata?.length || 0" />
          </el-col>
          <el-col :span="8">
            <div class="statistic-display">
              <div class="statistic-title">表类型</div>
              <el-tag :type="getTableTypeTagType(selectedTable.table_type)" size="large">
                {{ selectedTable.table_type || 'TABLE' }}
              </el-tag>
            </div>
          </el-col>
        </el-row>

        <!-- 表描述 -->
        <el-form-item label="表描述" style="margin-bottom: 20px;">
          <div style="display: flex; gap: 10px; align-items: flex-start;">
            <el-input
              v-model="selectedTable.table_description"
              type="textarea"
              :rows="2"
              placeholder="请输入表描述"
              style="flex: 1;"
            />
            <el-button
              type="primary"
              @click="saveTableDescriptionOnly"
              :loading="tableDescriptionSaving"
              size="small"
            >
              保存表描述
            </el-button>
          </div>
        </el-form-item>

        <!-- DDL -->
        <el-form-item label="DDL" style="margin-bottom: 20px;">
          <el-input
            :model-value="selectedTable.table_ddl"
            type="textarea"
            :rows="8"
            readonly
          />
        </el-form-item>

        <!-- 示例数据 -->
        <el-form-item label="示例数据" v-if="getParsedSampleData(selectedTable)">
          <el-table
            :data="getParsedSampleData(selectedTable).slice(0, 10)"
            border
            max-height="300"
            style="width: 100%"
          >
            <el-table-column
              v-for="(value, key) in getParsedSampleData(selectedTable)[0]"
              :key="key"
              :prop="key"
              :label="key"
              show-overflow-tooltip
            />
          </el-table>
          <div style="margin-top: 10px; color: #909399;">
            显示前 10 条数据，共 {{ getParsedSampleData(selectedTable).length }} 条
          </div>
        </el-form-item>

        <!-- 字段信息 -->
        <el-form-item label="字段信息" v-if="selectedTable.field_metadata && selectedTable.field_metadata.length > 0">
          <el-table
            :data="selectedTable.field_metadata"
            border
            max-height="400"
            style="width: 100%"
          >
            <el-table-column prop="field_name" label="字段名" width="150" show-overflow-tooltip />
            <el-table-column prop="field_type" label="数据类型" width="150">
              <template #default="{ row }">
                <el-tag size="small" :type="getFieldTypeTagType(row.field_type)">
                  {{ row.field_type }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="null_rate" label="空值率" width="100">
              <template #default="{ row }">
                {{ (row.null_rate * 100).toFixed(2) }}%
              </template>
            </el-table-column>
            <el-table-column prop="unique_count" label="唯一值数" width="120">
              <template #default="{ row }">
                {{ formatNumber(row.unique_count) }}
              </template>
            </el-table-column>
            <el-table-column label="示例数据" min-width="300">
              <template #default="{ row }">
                <span v-if="getParsedFieldSampleData(row)">
                  {{ Array.from(getParsedFieldSampleData(row)).slice(0, 5).join(', ') }}
                  <span v-if="getParsedFieldSampleData(row).length > 5">...</span>
                </span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="字段描述" min-width="250">
              <template #default="{ row }">
                <div style="display: flex; gap: 8px; align-items: center;">
                  <el-input
                    v-model="row.field_description"
                    placeholder="请输入字段描述"
                    size="small"
                    style="flex: 1;"
                  />
                  <el-button
                    type="primary"
                    size="small"
                    @click="saveFieldDescription(row)"
                    :loading="fieldSavingStatus[row.field_id]"
                  >
                    保存
                  </el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </el-form-item>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="detailDialogVisible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Collection, Key } from '@element-plus/icons-vue'
import { getNlsqlTaskConfigList } from '@/api/nlsqlTaskConfig'
import {
  getMetadataByTaskId,
  updateTableDescription,
  updateFieldDescription,
  deleteTableMetadata,
  deleteTableMetadataBatch
} from '@/api/metadata'

// 状态管理
const loading = ref(false)
const selectedTaskId = ref(null)
const taskList = ref([])
const metadata = ref(null)
const selectedTable = ref(null)
const detailDialogVisible = ref(false)
const showAllTables = ref(false)
const tableDescriptionSaving = ref(false)
const fieldSavingStatus = ref({})
const selectedTables = ref([])
const batchDeleting = ref(false)

// 分页状态
const tablePagination = reactive({
  currentPage: 1,
  pageSize: 5,
  total: 0
})

// 获取任务列表
const fetchTasks = async () => {
  try {
    const response = await getNlsqlTaskConfigList({ page: 1, page_size: 100 })
    taskList.value = response.items || []
  } catch (error) {
    console.error('获取任务列表失败:', error)
    ElMessage.error('获取任务列表失败')
  }
}

// 任务改变时获取元数据
const handleTaskChange = async (taskId) => {
  if (!taskId) {
    metadata.value = null
    return
  }

  loading.value = true
  try {
    const response = await getMetadataByTaskId(taskId)

    // 从data字段中提取实际的元数据
    if (response && response.data) {
      metadata.value = response.data
    } else {
      metadata.value = response
    }

    // 重置分页
    tablePagination.currentPage = 1
    if (metadata.value && metadata.value.tables) {
      tablePagination.total = metadata.value.tables.length
    }
  } catch (error) {
    console.error('获取元数据失败:', error)
    ElMessage.error(error.response?.data?.detail || '获取元数据失败')
    metadata.value = null
  } finally {
    loading.value = false
  }
}

// 计算当前页的表数据
const currentTables = computed(() => {
  if (!metadata.value || !metadata.value.tables) return []

  const start = (tablePagination.currentPage - 1) * tablePagination.pageSize
  const end = start + tablePagination.pageSize
  return metadata.value.tables.slice(start, end)
})

// 处理分页变化
const handleTablePageChange = (page) => {
  tablePagination.currentPage = page
}

// 处理每页大小变化
const handleTableSizeChange = (size) => {
  tablePagination.pageSize = size
  tablePagination.currentPage = 1
}

// 查看表详情
const handleViewTableDetail = (table) => {
  selectedTable.value = JSON.parse(JSON.stringify(table)) // 深拷贝
  detailDialogVisible.value = true
}

// 只保存表描述
const saveTableDescriptionOnly = async () => {
  if (!selectedTable.value) return

  tableDescriptionSaving.value = true
  try {
    await updateTableDescription(selectedTable.value.table_id, selectedTable.value.table_description)
    ElMessage.success('表描述保存成功')

    // 更新原数据
    const originalTable = metadata.value.tables.find(t => t.table_id === selectedTable.value.table_id)
    if (originalTable) {
      originalTable.table_description = selectedTable.value.table_description
    }
  } catch (error) {
    ElMessage.error('表描述保存失败')
  } finally {
    tableDescriptionSaving.value = false
  }
}

// 保存单个字段描述
const saveFieldDescription = async (field) => {
  fieldSavingStatus.value[field.field_id] = true
  try {
    await updateFieldDescription(field.field_id, field.field_description)
    ElMessage.success(`字段 "${field.field_name}" 描述保存成功`)

    // 更新原数据
    const originalTable = metadata.value.tables.find(t => t.table_id === selectedTable.value.table_id)
    if (originalTable) {
      const originalField = originalTable.field_metadata.find(f => f.field_id === field.field_id)
      if (originalField) {
        originalField.field_description = field.field_description
      }
    }
  } catch (error) {
    ElMessage.error(`字段 "${field.field_name}" 描述保存失败`)
  } finally {
    fieldSavingStatus.value[field.field_id] = false
  }
}

// 处理表格选择变化
const handleSelectionChange = (selection) => {
  selectedTables.value = selection
}

// 批量删除表元数据
const handleBatchDelete = () => {
  if (selectedTables.value.length === 0) return

  const tableNames = selectedTables.value.map(t => `${t.schema_name}.${t.table_name}`).join(', ')
  ElMessageBox.confirm(
    `确定要删除以下 ${selectedTables.value.length} 个表的元数据吗？\n${tableNames}\n\n此操作将级联删除相关的样例数据和字段元数据，且不可恢复！`,
    '批量删除警告',
    {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning',
      dangerouslyUseHTMLString: true,
      customClass: 'batch-delete-dialog'
    }
  ).then(async () => {
    batchDeleting.value = true
    try {
      const tableIds = selectedTables.value.map(t => t.table_id)
      const response = await deleteTableMetadataBatch(tableIds)
      ElMessage.success(response.message || '批量删除成功')
      selectedTables.value = []
      handleTaskChange(selectedTaskId.value)
    } catch (error) {
      console.error('批量删除失败:', error)
      ElMessage.error(error.response?.data?.detail || '批量删除失败')
    } finally {
      batchDeleting.value = false
    }
  })
}

// 删除表元数据
const handleDeleteTable = (table) => {
  ElMessageBox.confirm(
    `确定要删除表 "${table.schema_name}.${table.table_name}" 的元数据吗？此操作将级联删除相关的样例数据和字段元数据，且不可恢复！`,
    '警告',
    {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deleteTableMetadata(table.table_id)
      ElMessage.success('表元数据删除成功')
      handleTaskChange(selectedTaskId.value)
    } catch (error) {
      ElMessage.error('删除表元数据失败')
    }
  })
}

// 解析示例数据
const getParsedSampleData = (table) => {
  if (!table.sample_data) return null
  try {
    return JSON.parse(table.sample_data)
  } catch (error) {
    return null
  }
}

// 解析字段示例数据
const getParsedFieldSampleData = (field) => {
  if (!field.sample_data || field.sample_data === '[]') return []
  try {
    const parsed = JSON.parse(field.sample_data)
    return Array.isArray(parsed) ? parsed : []
  } catch (error) {
    return []
  }
}

// 获取字段类型标签类型
const getFieldTypeTagType = (type) => {
  if (!type) return 'info'

  if (type.includes('String') || type.includes('string')) {
    return 'primary'
  } else if (type.includes('Int') || type.includes('UInt') || type.includes('int')) {
    return 'success'
  } else if (type.includes('Float') || type.includes('Decimal')) {
    return 'warning'
  } else if (type.includes('DateTime') || type.includes('Date') || type.includes('Time')) {
    return 'danger'
  } else if (type.includes('Nullable')) {
    return 'info'
  } else if (type.includes('Array')) {
    return 'warning'
  } else {
    return 'info'
  }
}

// 格式化数字
const formatNumber = (num) => {
  if (!num && num !== 0) return 0
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toString()
}

// 获取任务状态标签类型
const getTaskStatusTagType = (status) => {
  const statusMap = {
    1: 'info',     // 初始化
    2: 'warning',  // 提取元数据
    3: 'primary',  // 生成表提示词
    4: 'success',  // 生成字段提示词
    5: 'success'   // 完成
  }
  return statusMap[status] || 'info'
}

// 获取任务状态标签文本
const getTaskStatusLabel = (status) => {
  const statusMap = {
    1: '初始化',
    2: '提取元数据',
    3: '生成表提示词',
    4: '生成字段提示词',
    5: '完成'
  }
  return statusMap[status] || '未知状态'
}

// 获取表类型标签类型
const getTableTypeTagType = (type) => {
  const typeMap = {
    'TABLE': 'primary',
    'VIEW': 'success',
    'LOG': 'warning',
    'FACT': 'info',
    'mergetree': 'primary',
    'MergeTree': 'primary',
    'distributed': 'warning'
  }
  return typeMap[type] || 'primary'
}

// 格式化日期时间
const formatDateTime = (dateTimeStr) => {
  if (!dateTimeStr) return '-'
  const date = new Date(dateTimeStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

onMounted(() => {
  fetchTasks()
})
</script>

<style scoped>
.metadata-detail-container {
  padding: 4px;
  min-height: calc(100vh - 90px);
  box-sizing: border-box;
}

/* 表格卡片包含分页的整体优化 */
.card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 8px 22px rgba(13, 52, 88, 0.1);
  border-radius: 14px;
  border: 1px solid #dbe6f0;
  margin-bottom: 14px;
}

/* 表格容器高度调整 - 固定高度只显示5行 */
.table-container {
  background: white;
  min-height: 260px;
  max-height: calc(100vh - 380px);
  overflow-y: auto;
}

.metadata-detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  position: sticky;
  top: 0;
  background: #fff;
  padding: 0 0 20px 0;
  z-index: 10;
}

.metadata-detail-header h2 {
  margin: 0;
  color: #303133;
}

.metadata-content {
  margin-top: 20px;
  max-width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.table-title {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}

.table-icon {
  margin-right: 8px;
}

.table-name {
  font-weight: bold;
  font-size: 14px;
}

/* 小巧的分页器 */
.compact-pagination {
  margin-top: 6px;
  z-index: 20;
  display: flex;
  justify-content: center;
}

.pagination-content {
  display: flex;
  align-items: center;
  gap: 12px;
  background: white;
  border: 1px solid #dbe6f0;
  border-radius: 20px;
  padding: 8px 14px;
  box-shadow: 0 8px 22px rgba(13, 52, 88, 0.14);
  backdrop-filter: blur(10px);
  background: rgba(255, 255, 255, 0.97);
}

.record-count {
  font-size: 12px;
  color: #909399;
  font-weight: 500;
  white-space: nowrap;
}

/* 自定义分页器样式 */
.compact-pagination .el-pagination {
  display: flex;
  align-items: center;
}

.compact-pagination .el-pagination .btn-prev,
.compact-pagination .el-pagination .btn-next {
  min-width: 28px;
  height: 28px;
  border-radius: 14px;
  font-size: 12px;
  border: 1px solid #e4e7ed;
  background: white;
  margin: 0 2px;
}

.compact-pagination .el-pagination .el-pager li {
  min-width: 28px;
  height: 28px;
  border-radius: 14px;
  font-size: 12px;
  margin: 0 2px;
  line-height: 28px;
  border: 1px solid #e4e7ed;
}

.compact-pagination .el-pagination .el-pager li.active {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

.compact-pagination .el-pagination .el-pagination__sizes {
  margin-left: 12px;
}

.compact-pagination .el-pagination .el-select .el-input {
  width: 80px;
}

.compact-pagination .el-pagination .el-select .el-input .el-input__wrapper {
  border-radius: 12px;
  font-size: 12px;
  height: 24px;
}

.table-detail-content {
  max-height: 70vh;
  overflow-y: auto;
  padding-right: 10px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* 优化滚动条样式 */
.table-detail-content::-webkit-scrollbar {
  width: 8px;
}

.table-detail-content::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.table-detail-content::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.table-detail-content::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* 自定义统计显示样式 */
.statistic-display {
  text-align: center;
  padding: 10px 8px;
}

.statistic-display .statistic-title {
  color: #556678;
  font-size: 13px;
  margin-bottom: 8px;
}

.statistic-display .el-tag {
  font-weight: 600;
  min-width: 100px;
}

@media (max-width: 860px) {
  .metadata-detail-container {
    padding: 0;
  }

  .metadata-detail-header {
    position: static;
  }

  .table-container {
    max-height: calc(100vh - 280px);
  }

  .pagination-content {
    flex-direction: column;
    gap: 10px;
    padding: 12px;
  }
}
</style>
