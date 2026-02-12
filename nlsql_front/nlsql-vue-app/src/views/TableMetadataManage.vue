<template>
  <div class="table-metadata-container">
    <div class="table-metadata-header">
      <h2>表元数据管理</h2>
      <div class="header-actions">
        <el-button type="primary" @click="handleScan">
          <el-icon><Refresh /></el-icon>
          扫描表元数据
        </el-button>
        <el-button type="danger" :disabled="selectedIds.length === 0" @click="handleBatchDelete">
          <el-icon><Delete /></el-icon>
          批量删除
        </el-button>
      </div>
    </div>

    <!-- 筛选和搜索 -->
    <div class="filter-section">
      <el-form :model="filterForm" :inline="true">
        <el-form-item label="数据库配置">
          <el-select v-model="filterForm.db_config_id" placeholder="选择数据库配置" clearable style="width: 200px">
            <el-option
              v-for="db in dbConfigs"
              :key="db.id"
              :label="`${db.database_name} (${db.type})`"
              :value="db.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="表名">
          <el-input v-model="filterForm.table_name" placeholder="搜索表名" clearable style="width: 200px" />
        </el-form-item>
        <el-form-item label="表类型">
          <el-select v-model="filterForm.table_type" placeholder="选择表类型" clearable style="width: 150px">
            <el-option label="TABLE" value="TABLE" />
            <el-option label="VIEW" value="VIEW" />
            <el-option label="LOG" value="LOG" />
            <el-option label="FACT" value="FACT" />
          </el-select>
        </el-form-item>
        <el-form-item label="行数范围">
          <el-input-number v-model="filterForm.min_row_count" placeholder="最小行数" :min="0" style="width: 120px" />
          <span style="margin: 0 10px;">-</span>
          <el-input-number v-model="filterForm.max_row_count" placeholder="最大行数" :min="filterForm.min_row_count" style="width: 120px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchTableMetadata">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="resetFilter">
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 表格 -->
    <div class="table-section">
      <el-table
        :data="tableList"
        v-loading="loading"
        @selection-change="handleSelectionChange"
        style="width: 100%"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="table_name" label="表名" min-width="150" show-overflow-tooltip />
        <el-table-column prop="table_description" label="表描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="table_row_count" label="行数" width="100" sortable />
        <el-table-column prop="table_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getTableTypeTagType(row.table_type)" size="small">
              {{ row.table_type || 'TABLE' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleViewDetail(row)">
              详情
            </el-button>
            <el-button type="danger" size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          :current-page="currentPage"
          :page-size="pagination.limit"
          :page-sizes="[20, 50, 100, 200]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>

    <!-- 扫描对话框 -->
    <el-dialog v-model="scanDialogVisible" title="扫描表元数据" width="400px">
      <el-form :model="scanForm" label-width="120px">
        <el-form-item label="数据库配置" required>
          <el-select v-model="scanForm.db_config_id" placeholder="选择数据库配置" style="width: 100%">
            <el-option
              v-for="db in dbConfigs"
              :key="db.id"
              :label="`${db.database_name} (${db.type})`"
              :value="db.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="scanDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmScan" :loading="scanLoading">
          开始扫描
        </el-button>
      </template>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="表元数据详情" width="800px">
      <div v-if="selectedTable">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="ID">{{ selectedTable.id }}</el-descriptions-item>
          <el-descriptions-item label="数据库配置ID">{{ selectedTable.db_config_id }}</el-descriptions-item>
          <el-descriptions-item label="表名">{{ selectedTable.table_name }}</el-descriptions-item>
          <el-descriptions-item label="表类型">{{ selectedTable.table_type || 'TABLE' }}</el-descriptions-item>
          <el-descriptions-item label="行数">{{ selectedTable.table_row_count || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDateTime(selectedTable.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatDateTime(selectedTable.updated_at) }}</el-descriptions-item>
        </el-descriptions>

        <div class="table-ddl" v-if="selectedTable.table_ddl">
          <h4 style="margin-top: 20px; margin-bottom: 10px;">表结构 DDL</h4>
          <el-input
            :model-value="selectedTable.table_ddl"
            type="textarea"
            :rows="10"
            readonly
          />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Delete, Search } from '@element-plus/icons-vue'
import { getDbConfigList } from '@/api/dbConfig'
import {
  getTableMetadataList,
  scanTables,
  deleteTableMetadata as deleteTable,
  batchDeleteTableMetadata,
  deleteTableMetadataByConditions
} from '@/api/tableMetadata'

// 状态管理
const loading = ref(false)
const scanLoading = ref(false)
const scanDialogVisible = ref(false)
const detailDialogVisible = ref(false)
const selectedTable = ref(null)
const selectedIds = ref([])
const dbConfigs = ref([])
const tableList = ref([])

// 筛选表单
const filterForm = reactive({
  db_config_id: null,
  table_name: '',
  table_type: '',
  min_row_count: null,
  max_row_count: null,
  order_by: 'created_at',
  order_direction: 'desc'
})

// 扫描表单
const scanForm = reactive({
  db_config_id: null
})

// 分页
const pagination = reactive({
  skip: 0,
  limit: 20,
  total: 0
})

// 计算当前页码
const currentPage = computed(() => {
  return Math.floor(pagination.skip / pagination.limit) + 1
})

// 获取数据库配置列表
const fetchDbConfigs = async () => {
  try {
    const response = await getDbConfigList({ page: 1, page_size: 100 })
    dbConfigs.value = response.items || []
  } catch (error) {
    console.error('获取数据库配置失败:', error)
    ElMessage.error('获取数据库配置失败')
  }
}

// 获取表元数据列表
const fetchTableMetadata = async () => {
  loading.value = true
  try {
    const params = {
      ...filterForm,
      skip: pagination.skip,
      limit: pagination.limit
    }

    // 清理空值
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null || params[key] === undefined) {
        delete params[key]
      }
    })

    const response = await getTableMetadataList(params)
    tableList.value = response.items || []
    pagination.total = response.total || 0
  } catch (error) {
    console.error('获取表元数据失败:', error)
    ElMessage.error('获取表元数据失败')
  } finally {
    loading.value = false
  }
}

// 选择变化
const handleSelectionChange = (selection) => {
  selectedIds.value = selection.map(item => item.id)
}

// 打开扫描对话框
const handleScan = () => {
  scanForm.db_config_id = null
  scanDialogVisible.value = true
}

// 确认扫描
const confirmScan = async () => {
  if (!scanForm.db_config_id) {
    ElMessage.error('请选择数据库配置')
    return
  }

  scanLoading.value = true
  try {
    await scanTables({ db_config_id: scanForm.db_config_id })
    ElMessage.success('表元数据扫描成功')
    scanDialogVisible.value = false
    fetchTableMetadata()
  } catch (error) {
    console.error('扫描表元数据失败:', error)
    ElMessage.error('扫描表元数据失败')
  } finally {
    scanLoading.value = false
  }
}

// 查看详情
const handleViewDetail = (row) => {
  selectedTable.value = row
  detailDialogVisible.value = true
}

// 删除单条
const handleDelete = (row) => {
  ElMessageBox.confirm(
    `确定要删除表 "${row.table_name}" 的元数据吗？`,
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deleteTable(row.id)
      ElMessage.success('删除成功')
      fetchTableMetadata()
    } catch (error) {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  })
}

// 批量删除
const handleBatchDelete = () => {
  ElMessageBox.confirm(
    `确定要删除选中的 ${selectedIds.value.length} 条表元数据吗？`,
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await batchDeleteTableMetadata({ ids: selectedIds.value })
      ElMessage.success('批量删除成功')
      selectedIds.value = []
      fetchTableMetadata()
    } catch (error) {
      console.error('批量删除失败:', error)
      ElMessage.error('批量删除失败')
    }
  })
}

// 重置筛选
const resetFilter = () => {
  Object.assign(filterForm, {
    db_config_id: null,
    table_name: '',
    table_type: '',
    min_row_count: null,
    max_row_count: null,
    order_by: 'created_at',
    order_direction: 'desc'
  })
  pagination.skip = 0
  fetchTableMetadata()
}

// 分页处理
const handleSizeChange = (val) => {
  pagination.limit = val
  pagination.skip = 0
  fetchTableMetadata()
}

const handleCurrentChange = (val) => {
  pagination.skip = (val - 1) * pagination.limit
  fetchTableMetadata()
}

// 获取表类型标签类型
const getTableTypeTagType = (type) => {
  const typeMap = {
    'TABLE': 'primary',
    'VIEW': 'success',
    'LOG': 'warning',
    'FACT': 'info'
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
  fetchDbConfigs()
  fetchTableMetadata()
})
</script>

<style scoped>
.table-metadata-container {
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.table-metadata-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.table-metadata-header h2 {
  margin: 0;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.filter-section {
  margin-bottom: 20px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
}

.table-section {
  background: #fff;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.table-ddl {
  margin-top: 20px;
}

:deep(.el-form-item) {
  margin-bottom: 15px;
}

:deep(.el-input-number) {
  width: 100%;
}
</style>