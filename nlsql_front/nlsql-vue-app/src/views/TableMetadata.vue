<template>
  <div class="table-metadata-view">
    <div class="card">
      <h2 class="card-title">基础数据</h2>
      <p class="page-desc">管理数据库表的基础元数据信息，包括表结构、DDL等详细内容</p>

      <!-- 搜索筛选区域 -->
      <div class="search-section">
        <el-input
          v-model="searchKeyword"
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
          v-model="selectedDbConfigId"
          placeholder="选择数据库"
          clearable
          @change="handleDbConfigChange"
          class="db-select"
        >
          <el-option
            v-for="db in dbConfigList"
            :key="db.id"
            :label="db.database_name"
            :value="db.id"
          />
        </el-select>

        <el-select
          v-model="selectedTableType"
          placeholder="选择表类型"
          clearable
          @change="handleTableTypeChange"
          class="type-select"
        >
          <el-option label="TABLE" value="TABLE" />
          <el-option label="VIEW" value="VIEW" />
          <el-option label="FACT" value="FACT" />
          <el-option label="DIMENSION" value="DIMENSION" />
          <el-option label="LOG" value="LOG" />
        </el-select>

        <el-button type="danger" @click="handleBatchDelete" :disabled="selectedRows.length === 0" class="batch-delete-btn">
          批量删除 ({{ selectedRows.length }})
        </el-button>
      </div>

    <div class="card">
      <div class="table-container">
        <el-table
          v-loading="loading"
          :data="tableMetadataList"
          style="width: 100%"
          @selection-change="handleSelectionChange"
        >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="table_name" label="表名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="database_name" label="数据库名称" width="150">
          <template #default="scope">
            {{ getDbConfigName(scope.row.db_config_id) }}
          </template>
        </el-table-column>
        <el-table-column prop="table_type" label="表类型" width="100">
          <template #default="scope">
            <el-tag :type="getTableTypeColor(scope.row.table_type)">
              {{ scope.row.table_type || 'TABLE' }}
            </el-tag>
          </template>
        </el-table-column>
                <el-table-column prop="table_description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="scope">
            <el-link type="primary" @click="handleViewDetails(scope.row)">查看</el-link>
            <el-divider direction="vertical" />
            <el-link type="danger" @click="handleDelete(scope.row)">删除</el-link>
          </template>
        </el-table-column>
      </el-table>
      </div>

      </div>
    </div>

    <!-- 小巧的固定分页器 -->
    <div class="compact-pagination">
      <div class="pagination-content">
        <span class="record-count">{{ pagination.total }}</span>
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
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

    <!-- 详情对话框 -->
    <el-dialog
      v-model="showDetailsDialog"
      title="基础数据详情"
      width="800px"
    >
      <div v-if="selectedTable" class="table-details">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="ID">{{ selectedTable.id }}</el-descriptions-item>
          <el-descriptions-item label="表名称">{{ selectedTable.table_name }}</el-descriptions-item>
          <el-descriptions-item label="数据库名称">{{ getDbConfigName(selectedTable.db_config_id) }}</el-descriptions-item>
          <el-descriptions-item label="表类型">
            <el-tag :type="getTableTypeColor(selectedTable.table_type)">
              {{ selectedTable.table_type || 'TABLE' }}
            </el-tag>
          </el-descriptions-item>
                    <el-descriptions-item label="创建时间" span="2">{{ formatDate(selectedTable.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="表描述" span="2">{{ selectedTable.table_description || '暂无描述' }}</el-descriptions-item>
        </el-descriptions>

        <div style="margin-top: 20px;">
          <h4>DDL 语句：</h4>
          <el-input
            v-model="selectedTable.table_ddl"
            type="textarea"
            :rows="10"
            readonly
            style="font-family: monospace;"
          />
        </div>
      </div>
      <template #footer>
        <el-button @click="showDetailsDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getTableMetadataList,
  deleteTableMetadata,
  batchDeleteTableMetadata
} from '@/api/tableMetadata'
import { getDbConfigList } from '@/api/dbConfig'

// 响应式数据
const loading = ref(false)
const searchKeyword = ref('')
const selectedDbConfigId = ref(null)
const selectedTableType = ref('')
const tableMetadataList = ref([])
const dbConfigList = ref([])
const selectedRows = ref([])
const showDetailsDialog = ref(false)
const selectedTable = ref(null)

// 分页信息
const pagination = reactive({
  page: 1,
  pageSize: 10,  // 改为默认10条，确保分页组件可见
  total: 0
})

// 获取数据库配置列表
async function fetchDbConfigList() {
  try {
    const res = await getDbConfigList({ page: 1, page_size: 100 })
    dbConfigList.value = res.items || []
  } catch (error) {
    console.error('获取数据库配置列表失败:', error)
    ElMessage.error('获取数据库配置列表失败')
  }
}

// 获取表元数据列表
async function fetchList() {
  try {
    loading.value = true

    const params = {
      skip: (pagination.page - 1) * pagination.pageSize,
      limit: pagination.pageSize
    }

    // 复原过滤功能
    if (searchKeyword.value) {
      params.table_name = searchKeyword.value
    }
    if (selectedDbConfigId.value) {
      params.db_config_id = selectedDbConfigId.value
    }
    if (selectedTableType.value) {
      params.table_type = selectedTableType.value
    }

    console.log('发送的参数:', params) // 调试日志
    const res = await getTableMetadataList(params)
    tableMetadataList.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('获取表元数据列表失败:', error)
    ElMessage.error('获取表元数据列表失败')
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

// 数据库选择变化
function handleDbConfigChange() {
  pagination.page = 1
  fetchList()
}

// 表类型选择变化
function handleTableTypeChange() {
  pagination.page = 1
  fetchList()
}

// 表格选择变化
function handleSelectionChange(selection) {
  selectedRows.value = selection
}

// 分页大小变化
function handleSizeChange(size) {
  pagination.pageSize = size
  pagination.page = 1
  fetchList()
}

// 当前页变化
function handleCurrentChange(page) {
  pagination.page = page
  fetchList()
}

// 查看详情
function handleViewDetails(row) {
  selectedTable.value = row
  showDetailsDialog.value = true
}

// 处理删除
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除表 ${row.table_name} 的元数据吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await deleteTableMetadata(row.id)
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
    await batchDeleteTableMetadata({ ids })
    ElMessage.success('批量删除成功')
    fetchList()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error('批量删除失败')
    }
  }
}

// 获取数据库名称
function getDbConfigName(dbConfigId) {
  const db = dbConfigList.value.find(item => item.id === dbConfigId)
  return db ? db.database_name : '未知数据库'
}

// 获取表类型标签颜色
function getTableTypeColor(type) {
  const colorMap = {
    'TABLE': 'primary',
    'VIEW': 'success',
    'FACT': 'warning',
    'DIMENSION': 'info',
    'LOG': 'danger'
  }
  return colorMap[type] || 'primary'
}


// 格式化日期
function formatDate(dateString) {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

// 组件挂载时获取数据
onMounted(() => {
  fetchDbConfigList()
  fetchList()
})
</script>

<style scoped>
.page-desc {
  color: var(--text-secondary);
  margin-bottom: 14px;
}

/* 全新搜索区域样式 - 现代化设计 */
.search-section {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
  padding: 12px;
  background: linear-gradient(90deg, #f6f9fd, #ffffff);
  border: 1px solid #dde7f1;
  border-radius: 12px;
}

.search-input {
  flex: 1;
  max-width: 200px;
}

.db-select {
  width: 140px;
}

.type-select {
  width: 100px;
}

.batch-delete-btn {
  flex-shrink: 0;
  min-width: 120px;
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

  .db-select {
    width: 120px;
  }

  .type-select {
    width: 80px;
  }
}

@media (max-width: 768px) {
  .search-section {
    flex-direction: column;
    gap: 10px;
  }

  .search-input,
  .db-select,
  .type-select,
  .batch-delete-btn {
    width: 100%;
    max-width: none;
  }
}

/* 表格卡片包含分页的整体优化 */
.card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 6px 20px rgba(13, 52, 88, 0.1);
  border-radius: 14px;
  border: 1px solid #dbe6f0;
  margin-bottom: 20px;
  max-height: none;
}

/* 表格容器高度调整 - 分页器固定后可以充分利用空间 */
.table-container {
  flex: 1;
  overflow-y: auto;
  max-height: calc(100vh - 320px);
  background: white;
  min-height: 360px;
}

/* 表格样式优化 */
.el-table {
  height: auto;
}

/* 小巧的固定分页器 */
.compact-pagination {
  position: sticky;
  bottom: 10px;
  margin-top: 8px;
  z-index: 30;
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
  color: #5f6b79;
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

/* 第一个卡片（搜索区域）特殊样式 */
.card:first-child {
  background: transparent;
  border: none;
  box-shadow: none;
  margin-bottom: 0;
}

.table-details {
  max-height: 600px;
  overflow-y: auto;
}

/* 简化的响应式设计 */
@media (max-height: 800px) {
  .table-container {
    max-height: calc(100vh - 300px);
    min-height: 260px;
  }

  .compact-pagination {
    bottom: 8px;
  }
}

@media (max-height: 600px) {
  .table-container {
    max-height: calc(100vh - 240px);
    min-height: 180px;
  }

  .compact-pagination {
    bottom: 10px;
  }

  .pagination-content {
    padding: 4px 10px;
  }
}

/* 移动端适配 */
@media (max-width: 768px) {
  .compact-pagination {
    bottom: 15px;
  }

  .card {
    max-height: none;
  }

  .table-container {
    max-height: calc(100vh - 280px);
    min-height: 200px;
  }

  .compact-pagination {
    bottom: 10px;
  }

  .pagination-content {
    padding: 4px 10px;
    gap: 12px;
  }

  .record-count {
    font-size: 11px;
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
