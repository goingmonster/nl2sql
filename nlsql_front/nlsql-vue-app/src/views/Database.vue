<template>
  <div class="database-view">
    <div class="card">
      <h2 class="card-title">数据库管理</h2>
      <p class="page-desc">管理您的数据源连接，支持多种数据库类型</p>

      <div class="table-header">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索数据库名称或用户名"
          clearable
          @input="handleSearch"
          style="width: 300px; margin-right: 20px;"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-button type="primary" class="btn-gradient" @click="showAddDialog = true">
          <el-icon><Plus /></el-icon>
          添加数据库
        </el-button>
      </div>
    </div>

    <div class="card">
      <el-table
        v-loading="loading"
        :data="databaseList"
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="database_name" label="数据库名称" width="150" />
        <el-table-column prop="ip" label="主机地址" />
        <el-table-column prop="port" label="端口" width="100" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="schema_name" label="Schema" width="120" />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="scope">
            <el-tag>{{ scope.row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240">
          <template #default="scope">
            <el-button link type="primary" @click="handleEdit(scope.row)">编辑</el-button>
            <el-button link type="warning" @click="handleScan(scope.row)" :loading="scope.row.scanning">
              <el-icon><Refresh /></el-icon>
              扫描
            </el-button>
            <el-button link type="danger" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>

      <!-- 批量删除按钮 -->
      <div v-if="selectedRows.length > 0" class="batch-actions">
        <el-button type="danger" @click="handleBatchDelete">
          删除选中的 {{ selectedRows.length }} 条记录
        </el-button>
      </div>
    </div>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="showAddDialog"
      :title="isEdit ? '编辑数据库配置' : '添加数据库配置'"
      width="500px"
      @close="handleDialogClose"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="数据库名称" prop="database_name">
          <el-input v-model="formData.database_name" placeholder="请输入数据库名称" />
        </el-form-item>
        <el-form-item label="数据库类型" prop="type">
          <el-select v-model="formData.type" placeholder="选择数据库类型" style="width: 100%">
            <el-option label="PostgreSQL" value="PG" />
            <el-option label="ClickHouse" value="CK" />
            <el-option label="MySQL" value="MYSQL" />
          </el-select>
        </el-form-item>
        <el-form-item label="主机地址" prop="ip">
          <el-input v-model="formData.ip" placeholder="请输入 IP 地址" />
        </el-form-item>
        <el-form-item label="端口" prop="port">
          <el-input-number
            v-model="formData.port"
            :min="1"
            :max="65535"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="formData.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="formData.password"
            type="password"
            placeholder="请输入密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="Schema" prop="schema_name">
          <el-input v-model="formData.schema_name" placeholder="请输入 Schema 名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getDbConfigList,
  searchDbConfig,
  createDbConfig,
  updateDbConfig,
  deleteDbConfig,
  batchDeleteDbConfig
} from '@/api/dbConfig'
import { scanTables } from '@/api/tableMetadata'

// 响应式数据
const loading = ref(false)
const submitting = ref(false)
const showAddDialog = ref(false)
const isEdit = ref(false)
const searchKeyword = ref('')
const databaseList = ref([])
const selectedRows = ref([])
const formRef = ref()

// 分页信息
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 表单数据
const formData = ref({
  database_name: '',
  type: '',
  ip: '',
  port: 5432,
  username: '',
  password: '',
  schema_name: 'public'
})

// 表单验证规则
const formRules = {
  database_name: [
    { required: true, message: '请输入数据库名称', trigger: 'blur' },
    { max: 100, message: '数据库名称长度不能超过 100 个字符', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择数据库类型', trigger: 'change' }
  ],
  ip: [
    { required: true, message: '请输入 IP 地址', trigger: 'blur' },
    { pattern: /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/, message: '请输入正确的 IP 地址格式', trigger: 'blur' }
  ],
  port: [
    { required: true, message: '请输入端口号', trigger: 'blur' },
    { type: 'number', min: 1, max: 65535, message: '端口范围应在 1-65535 之间', trigger: 'blur' }
  ],
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少 6 位', trigger: 'blur' }
  ],
  schema_name: [
    { required: true, message: '请输入 Schema 名称', trigger: 'blur' }
  ]
}

// 获取数据库配置列表
async function fetchList(keyword = '') {
  try {
    loading.value = true
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize
    }

    let res
    if (keyword) {
      // 使用搜索接口
      res = await searchDbConfig({ ...params, keyword })
    } else {
      // 使用列表接口
      res = await getDbConfigList(params)
    }

    databaseList.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('获取数据库配置列表失败:', error)
    ElMessage.error('获取数据库配置列表失败')
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
    fetchList(searchKeyword.value)
  }, 500)
}

// 表格选择变化
function handleSelectionChange(selection) {
  selectedRows.value = selection
}

// 分页大小变化
function handleSizeChange(size) {
  pagination.pageSize = size
  pagination.page = 1
  fetchList(searchKeyword.value)
}

// 当前页变化
function handleCurrentChange(page) {
  pagination.page = page
  fetchList(searchKeyword.value)
}

// 重置表单
function resetForm() {
  formData.value = {
    database_name: '',
    type: '',
    ip: '',
    port: 5432,
    username: '',
    password: '',
    schema_name: 'public'
  }
  isEdit.value = false
  formRef.value?.clearValidate()
}

// 处理编辑
function handleEdit(row) {
  isEdit.value = true
  formData.value = {
    id: row.id,
    database_name: row.database_name,
    type: row.type,
    ip: row.ip,
    port: row.port,
    username: row.username,
    password: row.password,
    schema_name: row.schema_name
  }
  showAddDialog.value = true
}

// 处理扫描
async function handleScan(row) {
  try {
    // 设置该行的扫描状态
    const index = databaseList.value.findIndex(item => item.id === row.id)
    if (index !== -1) {
      databaseList.value[index].scanning = true
    }

    await ElMessageBox.confirm(
      `确定要扫描数据库 ${row.database_name} 的表结构吗？`,
      '扫描确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    const result = await scanTables({ db_config_id: row.id })
    if (result.success) {
      ElMessage.success(result.message || '扫描成功')
    } else {
      ElMessage.error(result.message || '扫描失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('扫描失败:', error)
      ElMessage.error(error.response?.data?.detail || '扫描失败')
    }
  } finally {
    // 重置该行的扫描状态
    const index = databaseList.value.findIndex(item => item.id === row.id)
    if (index !== -1) {
      databaseList.value[index].scanning = false
    }
  }
}

// 处理删除
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除数据库配置 ${row.username}@${row.ip}:${row.port} 吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await deleteDbConfig(row.id)
    ElMessage.success('删除成功')
    fetchList(searchKeyword.value)
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
    console.log('要删除的 IDs:', ids) // 调试日志

    const result = await batchDeleteDbConfig(ids)
    console.log('批量删除结果:', result) // 调试日志

    ElMessage.success('批量删除成功')
    fetchList(searchKeyword.value)
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      console.error('错误详情:', error.response?.data) // 添加错误详情日志
      ElMessage.error(error.response?.data?.detail || '批量删除失败')
    }
  }
}

// 提交表单
async function handleSubmit() {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    submitting.value = true

    const data = { ...formData.value }

    // 编辑时不传密码（如果密码为空）
    if (isEdit.value && !data.password) {
      delete data.password
    }

    if (isEdit.value) {
      await updateDbConfig(data.id, data)
      ElMessage.success('更新成功')
    } else {
      await createDbConfig(data)
      ElMessage.success('添加成功')
    }

    showAddDialog.value = false
    resetForm()
    fetchList(searchKeyword.value)
  } catch (error) {
    console.error(isEdit.value ? '更新失败:' : '添加失败:', error)
    ElMessage.error(isEdit.value ? '更新失败' : '添加失败')
  } finally {
    submitting.value = false
  }
}

// 格式化日期
function formatDate(dateString) {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

// 监听对话框关闭
function handleDialogClose() {
  resetForm()
}

// 组件挂载时获取数据
onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.database-view {
  display: grid;
  gap: 14px;
}

.page-desc {
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 10px;
}

.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}

.batch-actions {
  margin-top: 14px;
}

:deep(.el-table) {
  border-radius: 12px;
  overflow: hidden;
}

:deep(.el-table th.el-table__cell) {
  background-color: var(--table-head-bg);
  color: var(--primary-color);
}

:deep(.el-dialog) {
  border-radius: 14px;
}

@media (max-width: 860px) {
  .table-header {
    align-items: stretch;
  }

  :deep(.table-header .el-input) {
    width: 100% !important;
    margin-right: 0 !important;
  }

  :deep(.table-header .el-button) {
    width: 100%;
  }
}
</style>
