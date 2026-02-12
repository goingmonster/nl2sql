<template>
  <div class="model-view">
    <div class="card">
      <h2 class="card-title">模型管理</h2>
      <p class="page-desc">管理LLM配置，支持多种提供商，仅支持OPENAI</p>

      <div class="table-header">
        <el-select
          v-model="filterProvider"
          placeholder="筛选供应商"
          clearable
          @change="handleFilter"
          style="width: 150px; margin-right: 20px;"
        >
          <el-option label="OpenAI" value="OpenAI" />
          <el-option label="Azure" value="Azure" />
          <el-option label="Anthropic" value="Anthropic" />
          <el-option label="百度" value="Baidu" />
          <el-option label="阿里云" value="Aliyun" />
        </el-select>

        <el-button type="primary" class="btn-gradient" @click="showAddDialog = true">
          <el-icon><Plus /></el-icon>
          添加模型
        </el-button>
      </div>
    </div>

    <div class="card">
      <el-table
        v-loading="loading"
        :data="modelList"
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="provider" label="供应商" width="150">
          <template #default="scope">
            <el-tag>{{ scope.row.provider }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="model_name" label="模型名称" width="180" />
        <el-table-column prop="base_url" label="API地址" min-width="250" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="max_tokens" label="最大Token" width="120" />
        <el-table-column prop="temperature" label="温度" width="80" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.status === 1 ? 'success' : 'danger'">
              {{ scope.row.status === 1 ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button link type="primary" @click="handleEdit(scope.row)">编辑</el-button>
            <el-button
              link
              :type="scope.row.status === 1 ? 'warning' : 'success'"
              @click="handleToggleStatus(scope.row)"
            >
              {{ scope.row.status === 1 ? '禁用' : '启用' }}
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
      :title="isEdit ? '编辑模型配置' : '添加模型配置'"
      width="600px"
      @close="handleDialogClose"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="120px"
      >
        <el-form-item label="供应商" prop="provider">
          <el-select v-model="formData.provider" placeholder="选择供应商" style="width: 100%">
            <el-option label="OpenAI" value="OpenAI" />
            <el-option label="Azure" value="Azure" />
            <el-option label="Anthropic" value="Anthropic" />
            <el-option label="百度" value="Baidu" />
            <el-option label="阿里云" value="Aliyun" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型名称" prop="model_name">
          <el-input v-model="formData.model_name" placeholder="请输入模型名称，如：gpt-3.5-turbo" />
        </el-form-item>
        <el-form-item label="API地址" prop="base_url">
          <el-input v-model="formData.base_url" placeholder="请输入 API 地址" />
        </el-form-item>
        <el-form-item label="API密钥" prop="api_key">
          <el-input
            v-model="formData.api_key"
            type="password"
            placeholder="请输入 API 密钥"
            show-password
          />
        </el-form-item>
        <el-form-item label="最大Token" prop="max_tokens">
          <el-input-number
            v-model="formData.max_tokens"
            :min="1"
            :max="100000"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="温度参数" prop="temperature">
          <el-input-number
            v-model="formData.temperature"
            :min="0"
            :max="2"
            :step="0.1"
            :precision="1"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="formData.status">
            <el-radio :label="1">启用</el-radio>
            <el-radio :label="2">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="请输入描述信息"
          />
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
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getLlmConfigList,
  createLlmConfig,
  updateLlmConfig,
  deleteLlmConfig,
  batchDeleteLlmConfigs,
  enableLlmConfig,
  disableLlmConfig
} from '@/api/llmConfig'

// 响应式数据
const loading = ref(false)
const submitting = ref(false)
const showAddDialog = ref(false)
const isEdit = ref(false)
const filterProvider = ref('')
const modelList = ref([])
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
  provider: '',
  model_name: '',
  base_url: '',
  api_key: '',
  max_tokens: 4096,
  temperature: 0.7,
  status: 1,
  description: ''
})

// 表单验证规则
const formRules = {
  provider: [
    { required: true, message: '请选择供应商', trigger: 'change' }
  ],
  model_name: [
    { required: true, message: '请输入模型名称', trigger: 'blur' },
    { min: 1, max: 100, message: '模型名称长度应在 1-100 个字符之间', trigger: 'blur' }
  ],
  base_url: [
    { required: true, message: '请输入 API 地址', trigger: 'blur' },
    { type: 'url', message: '请输入正确的 URL 格式', trigger: 'blur' }
  ],
  api_key: [
    { required: true, message: '请输入 API 密钥', trigger: 'blur' }
  ],
  max_tokens: [
    { required: true, message: '请输入最大 Token 数', trigger: 'blur' },
    { type: 'number', min: 1, max: 100000, message: 'Token 数范围应在 1-100000 之间', trigger: 'blur' }
  ],
  temperature: [
    { required: true, message: '请输入温度参数', trigger: 'blur' },
    { type: 'number', min: 0, max: 2, message: '温度参数应在 0-2 之间', trigger: 'blur' }
  ],
  status: [
    { required: true, message: '请选择状态', trigger: 'change' }
  ]
}

// 获取模型配置列表
async function fetchList() {
  try {
    loading.value = true
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize
    }

    // 添加筛选条件
    if (filterProvider.value) {
      params.provider = filterProvider.value
    }

    const res = await getLlmConfigList(params)

    modelList.value = res.data || []
    pagination.total = res.pagination?.total || 0
  } catch (error) {
    console.error('获取模型配置列表失败:', error)
    ElMessage.error('获取模型配置列表失败')
  } finally {
    loading.value = false
  }
}

// 筛选处理
function handleFilter() {
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

// 重置表单
function resetForm() {
  formData.value = {
    provider: '',
    model_name: '',
    base_url: '',
    api_key: '',
    max_tokens: 4096,
    temperature: 0.7,
    status: 1,
    description: ''
  }
  isEdit.value = false
  formRef.value?.clearValidate()
}

// 处理编辑
function handleEdit(row) {
  isEdit.value = true
  formData.value = {
    id: row.id,
    provider: row.provider,
    model_name: row.model_name,
    base_url: row.base_url,
    api_key: row.api_key,
    max_tokens: row.max_tokens,
    temperature: row.temperature,
    status: row.status,
    description: row.description
  }
  showAddDialog.value = true
}

// 处理删除
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除模型配置 ${row.provider} 吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await deleteLlmConfig(row.id)
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
    await batchDeleteLlmConfigs(ids)
    ElMessage.success('批量删除成功')
    fetchList()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error('批量删除失败')
    }
  }
}

// 切换状态
async function handleToggleStatus(row) {
  try {
    if (row.status === 1) {
      await disableLlmConfig(row.id)
      ElMessage.success('禁用成功')
    } else {
      await enableLlmConfig(row.id)
      ElMessage.success('启用成功')
    }
    fetchList()
  } catch (error) {
    console.error('状态切换失败:', error)
    ElMessage.error('状态切换失败')
  }
}

// 提交表单
async function handleSubmit() {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    submitting.value = true

    const data = { ...formData.value }
    delete data.id // 删除 id 字段，避免传递给后端

    if (isEdit.value) {
      await updateLlmConfig(formData.value.id, data)
      ElMessage.success('更新成功')
    } else {
      await createLlmConfig(data)
      ElMessage.success('添加成功')
    }

    showAddDialog.value = false
    resetForm()
    fetchList()
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
.page-desc {
  color: var(--text-secondary);
  margin-bottom: 20px;
}

.table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.batch-actions {
  margin-top: 20px;
}
</style>