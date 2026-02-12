<template>
  <div class="task-container">
    <div class="task-header">
      <h2>NLSQL 任务管理</h2>
      <el-button type="primary" @click="handleCreateTask">
        <el-icon><Plus /></el-icon>
        创建任务
      </el-button>
    </div>

    <!-- 筛选和搜索 -->
    <div class="filter-section">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-select v-model="filter.status" placeholder="任务状态" clearable @change="fetchTasks">
            <el-option label="全部" value="" />
            <el-option label="初始化" :value="1" />
            <el-option label="提取元数据" :value="2" />
            <el-option label="生成表提示词" :value="3" />
            <el-option label="生成字段提示词" :value="4" />
            <el-option label="完成" :value="5" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="filter.llm_config_id" placeholder="LLM配置" clearable @change="fetchTasks">
            <el-option label="全部" value="" />
            <el-option
              v-for="llm in llmConfigs"
              :key="llm.id"
              :label="llm.provider || `LLM-${llm.id}`"
              :value="llm.id"
            />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="filter.db_config_id" placeholder="数据库配置" clearable @change="fetchTasks">
            <el-option label="全部" value="" />
            <el-option
              v-for="db in dbConfigs"
              :key="db.id"
              :label="db.database_name || `DB-${db.id}`"
              :value="db.id"
            />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-input v-model="filter.description" placeholder="搜索任务描述..." clearable @change="fetchTasks">
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-col>
      </el-row>
    </div>

    <!-- 任务列表 -->
    <div class="task-table">
      <el-table :data="taskList" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="任务ID" width="80" />
        <el-table-column prop="description" label="任务描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="llm_config_name" label="LLM配置" width="150" />
        <el-table-column prop="db_config_name" label="数据库配置" width="150" />
        <el-table-column prop="user_prompt_config_name" label="提示词配置" width="150" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)">
              {{ getStatusLabel(row.status) }}
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
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-dropdown trigger="click" @command="(command) => handleCommand(command, row)">
              <el-button type="primary" size="small" :loading="scanLoading.includes(row.id)" text>
                <el-icon><MoreFilled /></el-icon>
                操作
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="view">
                    <el-icon><View /></el-icon>
                    详情
                  </el-dropdown-item>
                  <el-dropdown-item command="scan" :disabled="scanLoading.includes(row.id)">
                    <el-icon><Upload /></el-icon>
                    提取元数据
                  </el-dropdown-item>
                  <el-dropdown-item command="generateTablePrompt" :disabled="scanLoading.includes(row.id)">
                    <el-icon><Document /></el-icon>
                    生成表级别提示词
                  </el-dropdown-item>
                  <el-dropdown-item command="generateFieldPrompt" :disabled="scanLoading.includes(row.id)">
                    <el-icon><Collection /></el-icon>
                    生成字段提示词
                  </el-dropdown-item>
                  <el-dropdown-item command="generateRelationPrompt" :disabled="scanLoading.includes(row.id)">
                    <el-icon><Connection /></el-icon>
                    生成关联关系提示词
                  </el-dropdown-item>
                  <el-dropdown-item command="edit">
                    <el-icon><Edit /></el-icon>
                    编辑
                  </el-dropdown-item>
                  <el-dropdown-item command="delete" divided>
                    <el-icon><Delete /></el-icon>
                    删除
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>

    <!-- 创建/编辑任务对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? '编辑NLSQL任务' : '创建NLSQL任务'"
      width="800px"
      @open="fetchConfigs"
      >
      <el-form :model="taskForm" :rules="taskRules" ref="taskFormRef" label-width="120px">
        <el-form-item label="任务描述" prop="description">
          <el-input
            v-model="taskForm.description"
            placeholder="请输入任务描述"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="数据库连接" prop="db_config_id">
          <el-select
            v-model="taskForm.db_config_id"
            placeholder="请选择数据库连接"
            style="width: 100%"
            @change="onDbConfigChange"
          >
            <el-option
              v-for="db in dbConfigs"
              :key="db.id"
              :label="`${db.database_name} (${db.type})`"
              :value="db.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="选择表" prop="select_tables" v-if="taskForm.db_config_id">
          <el-select
            v-model="taskForm.select_tables"
            placeholder="搜索并选择要使用的表"
            style="width: 100%"
            multiple
            filterable
            remote
            :remote-method="searchTables"
            :loading="tableSearchLoading"
            clearable
          >
            <el-option
              v-for="table in tableList"
              :key="table.id"
              :label="table.table_name"
              :value="table.id"
            />
          </el-select>
          <div style="margin-top: 5px; color: #909399; font-size: 12px;">
            可搜索表名称并选择多个表，用于NLSQL查询
          </div>
        </el-form-item>

        <el-form-item label="LLM配置" prop="llm_config_id">
          <el-select
            v-model="taskForm.llm_config_id"
            placeholder="请选择LLM配置"
            style="width: 100%"
          >
            <el-option
              v-for="llm in llmConfigs"
              :key="llm.id"
              :label="`${llm.provider} - ${llm.base_url}`"
              :value="llm.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="提示词配置" prop="user_prompt_config_id">
          <el-select
            v-model="taskForm.user_prompt_config_id"
            placeholder="请选择提示词配置"
            style="width: 100%"
          >
            <el-option
              v-for="prompt in promptConfigs"
              :key="prompt.id"
              :label="prompt.config_name"
              :value="prompt.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreateSubmit" :loading="submitLoading">
          {{ isEditing ? '更新' : '确定' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 任务详情对话框 -->
    <el-dialog v-model="detailVisible" title="任务详情" width="900px">
      <div class="task-detail" v-if="selectedTask">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务ID">{{ selectedTask.id }}</el-descriptions-item>
          <el-descriptions-item label="任务描述">{{ selectedTask.description || '-' }}</el-descriptions-item>
          <el-descriptions-item label="LLM配置">{{ selectedTask.llm_config_name }}</el-descriptions-item>
          <el-descriptions-item label="数据库配置">{{ selectedTask.db_config_name }}</el-descriptions-item>
          <el-descriptions-item label="提示词配置">{{ selectedTask.user_prompt_config_name }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusTagType(selectedTask.status)">
              {{ getStatusLabel(selectedTask.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDateTime(selectedTask.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatDateTime(selectedTask.updated_at) }}</el-descriptions-item>
        </el-descriptions>

        <div class="selected-tables" v-if="selectedTask.select_tables && selectedTask.select_tables.length > 0">
          <h4 style="margin-top: 20px; margin-bottom: 10px;">选中的表</h4>
          <el-tag
            v-for="tableId in selectedTask.select_tables"
            :key="tableId"
            style="margin-right: 10px; margin-bottom: 10px;"
          >
            表ID: {{ tableId }}
          </el-tag>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, MoreFilled, View, Upload, Edit, Delete, Document, Collection, Connection } from '@element-plus/icons-vue'
import {
  getNlsqlTaskConfigList,
  createNlsqlTaskConfig,
  updateNlsqlTaskConfig,
  deleteNlsqlTaskConfig,
  batchDeleteNlsqlTaskConfig
} from '@/api/nlsqlTaskConfig'
import { getDbConfigList } from '@/api/dbConfig'
import { getLlmConfigList } from '@/api/llmConfig'
import { getPromptConfigList } from '@/api/promptConfig'
import { getTableMetadataList } from '@/api/tableMetadata'
import { scanMetadata } from '@/api/metadataScan'
import { generateTableLevelPrompt } from '@/api/tableLevelPrompt'
import { generateTableFieldPrompt } from '@/api/tableFieldPrompt'
import { generateTableFieldRelation } from '@/api/tableFieldRelation'

// 状态管理
const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)
const detailVisible = ref(false)
const taskFormRef = ref(null)
const selectedTask = ref(null)
const isEditing = ref(false)
const tableSearchLoading = ref(false)
const scanLoading = ref([])

// 数据列表
const taskList = ref([])
const dbConfigs = ref([])
const llmConfigs = ref([])
const promptConfigs = ref([])
const tableList = ref([])

// 筛选条件
const filter = reactive({
  status: '',
  llm_config_id: '',
  db_config_id: '',
  description: ''
})

// 分页
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

// 任务表单
const taskForm = reactive({
  id: null,
  db_config_id: null,
  llm_config_id: null,
  user_prompt_config_id: null,
  select_tables: [],
  description: ''
})

// 表单验证规则
const taskRules = {
  db_config_id: [
    { required: true, message: '请选择数据库连接', trigger: 'change' }
  ],
  llm_config_id: [
    { required: true, message: '请选择LLM配置', trigger: 'change' }
  ],
  user_prompt_config_id: [
    { required: true, message: '请选择提示词配置', trigger: 'change' }
  ]
}

// 获取状态标签颜色
const getStatusTagType = (status) => {
  const statusMap = {
    1: 'info',     // 初始化
    2: 'warning',  // 提取元数据
    3: 'primary',  // 生成表提示词
    4: 'success',  // 生成字段提示词
    5: 'success'   // 完成
  }
  return statusMap[status] || 'info'
}

// 获取状态标签文本
const getStatusLabel = (status) => {
  const statusMap = {
    1: '初始化',
    2: '提取元数据',
    3: '生成表提示词',
    4: '生成字段提示词',
    5: '完成'
  }
  return statusMap[status] || '未知状态'
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

// 获取任务列表
const fetchTasks = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size,
      ...filter
    }
    // 清理空值
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null || params[key] === undefined) {
        delete params[key]
      }
    })

    const response = await getNlsqlTaskConfigList(params)
    taskList.value = response.items || []
    pagination.total = response.total || 0
  } catch (error) {
    console.error('获取任务列表失败:', error)
    ElMessage.error('获取任务列表失败')
  } finally {
    loading.value = false
  }
}

// 获取所有配置
const fetchConfigs = async () => {
  try {
    // Database config - 使用 page/page_size 参数格式
    const dbRes = await getDbConfigList({
      page: 1,
      page_size: 50
    })

    // LLM config - 使用 page/page_size 参数格式
    const llmRes = await getLlmConfigList({
      page: 1,
      page_size: 50
    })

    // Prompt config - 使用 page/page_size 参数格式
    const promptRes = await getPromptConfigList({
      page: 1,
      page_size: 50
    })

    // 根据不同的响应格式处理数据
    dbConfigs.value = dbRes.items || []    // Database config 返回在 res.items 中
    llmConfigs.value = llmRes.data || []   // LLM config 返回在 res.data 中
    promptConfigs.value = promptRes.data || []  // Prompt config 返回在 res.data 中，不是 items

    // 调试日志
    console.log('Database configs:', dbConfigs.value.length)
    console.log('LLM configs:', llmConfigs.value.length)
    console.log('Prompt configs:', promptConfigs.value.length)
  } catch (error) {
    console.error('获取配置失败:', error)
    ElMessage.error('获取配置失败')
  }
}

// 数据库配置改变时获取表列表
const onDbConfigChange = async (dbConfigId) => {
  if (!dbConfigId) {
    tableList.value = []
    taskForm.select_tables = []
    return
  }

  try {
    const response = await getTableMetadataList({
      db_config_id: dbConfigId,
      page: 1,
      page_size: 50
    })
    tableList.value = response.items || []
    // 只有在创建任务时才清空选择，编辑时不清空
    if (!isEditing.value) {
      taskForm.select_tables = []
    }
  } catch (error) {
    console.error('获取表列表失败:', error)
    ElMessage.error('获取表列表失败')
  }
}

// 搜索表的方法
const searchTables = async (query) => {
  if (!taskForm.db_config_id) {
    tableList.value = []
    return
  }

  try {
    tableSearchLoading.value = true
    const params = {
      db_config_id: taskForm.db_config_id,
      page: 1,
      page_size: 50
    }

    // 只有在输入搜索内容时才添加 table_name 参数
    if (query) {
      params.table_name = query
    }

    const response = await getTableMetadataList(params)
    tableList.value = response.items || []
  } catch (error) {
    console.error('搜索表列表失败:', error)
    ElMessage.error('搜索表列表失败')
  } finally {
    tableSearchLoading.value = false
  }
}

// 加载已选择表的完整信息（用于编辑时确保表能被正确显示）
const loadSelectedTablesInfo = async () => {
  if (!taskForm.select_tables || taskForm.select_tables.length === 0 || !taskForm.db_config_id) {
    return
  }

  try {
    // 获取所有表的数据，确保包含已选择的表
    const response = await getTableMetadataList({
      db_config_id: taskForm.db_config_id,
      page: 1,
      page_size: 200
    })

    const allTables = response.items || []
    const currentTableIds = new Set(allTables.map(table => table.id))
    const missingTableIds = taskForm.select_tables.filter(id => !currentTableIds.has(id))

    // 如果有缺失的表，需要通过ID分别查询
    if (missingTableIds.length > 0) {
      console.log('有已选择的表不在当前列表中，需要单独查询:', missingTableIds)
      // 这里可以根据需要实现通过ID查询单个表的逻辑
      // 或者简单地增加页面大小确保包含更多表
    }

    // 确保表列表包含所有已选择的表
    tableList.value = allTables
  } catch (error) {
    console.error('加载已选择表信息失败:', error)
  }
}

// 创建任务
const handleCreateTask = () => {
  isEditing.value = false
  // 重置表单
  Object.assign(taskForm, {
    id: null,
    db_config_id: null,
    llm_config_id: null,
    user_prompt_config_id: null,
    select_tables: [],
    description: ''
  })
  dialogVisible.value = true
}

// 编辑任务
const handleEditTask = async (task) => {
  isEditing.value = true

  try {
    // 设置表单数据
    taskForm.id = task.id
    taskForm.db_config_id = task.db_config_id
    taskForm.llm_config_id = task.llm_config_id
    taskForm.user_prompt_config_id = task.user_prompt_config_id
    taskForm.select_tables = task.select_tables || []
    taskForm.description = task.description || ''

    // 如果有数据库配置，加载对应的表列表
    if (taskForm.db_config_id) {
      await onDbConfigChange(taskForm.db_config_id)
      // 确保已选择的表在列表中能被找到
      await loadSelectedTablesInfo()
    }

    dialogVisible.value = true
  } catch (error) {
    console.error('准备编辑任务失败:', error)
    ElMessage.error('准备编辑任务失败')
  }
}

// 提交创建/更新任务
const handleCreateSubmit = async () => {
  if (!taskFormRef.value) return

  try {
    await taskFormRef.value.validate()
    submitLoading.value = true

    // 准备提交的数据，确保数据类型正确
    const submitData = {
      db_config_id: parseInt(taskForm.db_config_id, 10),
      llm_config_id: parseInt(taskForm.llm_config_id, 10),
      user_prompt_config_id: parseInt(taskForm.user_prompt_config_id, 10),
      select_tables: taskForm.select_tables.map(id => parseInt(id, 10)),
      description: taskForm.description || null
    }

    // 确保必填字段不为空
    if (!submitData.db_config_id || !submitData.llm_config_id || !submitData.user_prompt_config_id) {
      ElMessage.error('请选择所有必填的配置')
      return
    }

    console.log('提交的数据:', submitData)

    if (isEditing.value) {
      // 更新任务
      await updateNlsqlTaskConfig(taskForm.id, submitData)
      ElMessage.success('任务更新成功')
    } else {
      // 创建任务
      await createNlsqlTaskConfig(submitData)
      ElMessage.success('任务创建成功')
    }

    dialogVisible.value = false

    // 重置表单
    Object.assign(taskForm, {
      id: null,
      db_config_id: null,
      llm_config_id: null,
      user_prompt_config_id: null,
      select_tables: [],
      description: ''
    })

    // 刷新任务列表
    fetchTasks()
  } catch (error) {
    console.error(`${isEditing.value ? '更新' : '创建'}任务失败:`, error)
    console.error('错误详情:', error.response?.data)
    ElMessage.error(error.response?.data?.detail || `${isEditing.value ? '更新' : '创建'}任务失败`)
  } finally {
    submitLoading.value = false
  }
}

// 查看任务详情
const handleViewDetail = (task) => {
  selectedTask.value = task
  detailVisible.value = true
}

// 处理下拉菜单操作
const handleCommand = (command, task) => {
  switch (command) {
    case 'view':
      handleViewDetail(task)
      break
    case 'scan':
      handleScanMetadata(task)
      break
    case 'generateTablePrompt':
      handleGenerateTablePrompt(task)
      break
    case 'generateFieldPrompt':
      handleGenerateFieldPrompt(task)
      break
    case 'generateRelationPrompt':
      handleGenerateRelationPrompt(task)
      break
    case 'edit':
      handleEditTask(task)
      break
    case 'delete':
      handleDeleteTask(task)
      break
  }
}

// 扫描元数据
const handleScanMetadata = async (task) => {
  try {
    // 添加到加载状态
    scanLoading.value = [...scanLoading.value, task.id]

    ElMessage.info(`任务 ${task.id} 正在提取元数据，耗时可能较长，请稍候...`)

    const response = await scanMetadata(task.id)
    ElMessage.success(response.message || `任务 ${task.id} 元数据扫描成功`)

    // 刷新任务列表以更新状态
    fetchTasks()
  } catch (error) {
    console.error('扫描元数据失败:', error)
    if (error.code === 'ECONNABORTED') {
      ElMessage.error(`任务 ${task.id} 提取元数据超时，请稍后查看任务状态或重试`)
      return
    }
    ElMessage.error(error.response?.data?.detail || `扫描任务 ${task.id} 元数据失败`)
  } finally {
    // 从加载状态中移除
    scanLoading.value = scanLoading.value.filter(id => id !== task.id)
  }
}

// 生成表级别提示词
const handleGenerateTablePrompt = async (task) => {
  try {
    // 添加到加载状态
    scanLoading.value = [...scanLoading.value, task.id]

    ElMessage.info(`任务 ${task.id} 正在生成表级别提示词，耗时可能较长，请稍候...`)

    const response = await generateTableLevelPrompt(task.id)
    ElMessage.success(response.message || `任务 ${task.id} 生成表级别提示词成功`)

    // 刷新任务列表以更新状态
    fetchTasks()
  } catch (error) {
    console.error('生成表级别提示词失败:', error)
    if (error.code === 'ECONNABORTED') {
      ElMessage.error(`任务 ${task.id} 生成表级别提示词超时，请稍后查看任务状态或重试`)
      return
    }
    ElMessage.error(error.response?.data?.detail || `任务 ${task.id} 生成表级别提示词失败`)
  } finally {
    // 从加载状态中移除
    scanLoading.value = scanLoading.value.filter(id => id !== task.id)
  }
}

// 生成字段提示词
const handleGenerateFieldPrompt = async (task) => {
  try {
    // 添加到加载状态
    scanLoading.value = [...scanLoading.value, task.id]

    ElMessage.info(`任务 ${task.id} 正在生成字段提示词，耗时可能较长，请稍候...`)

    const response = await generateTableFieldPrompt(task.id)
    ElMessage.success(response.message || `任务 ${task.id} 生成字段提示词成功`)

    // 刷新任务列表以更新状态
    fetchTasks()
  } catch (error) {
    console.error('生成字段提示词失败:', error)
    if (error.code === 'ECONNABORTED') {
      ElMessage.error(`任务 ${task.id} 生成字段提示词超时，请稍后查看任务状态或重试`)
      return
    }
    ElMessage.error(error.response?.data?.detail || `任务 ${task.id} 生成字段提示词失败`)
  } finally {
    // 从加载状态中移除
    scanLoading.value = scanLoading.value.filter(id => id !== task.id)
  }
}

// 生成关联关系提示词
const handleGenerateRelationPrompt = async (task) => {
  try {
    // 添加到加载状态
    scanLoading.value = [...scanLoading.value, task.id]

    ElMessage.info(`任务 ${task.id} 正在生成关联关系提示词，耗时可能较长，请稍候...`)

    const response = await generateTableFieldRelation(task.id)
    ElMessage.success(response.message || `任务 ${task.id} 生成关联关系提示词成功`)

    // 刷新任务列表以更新状态
    fetchTasks()
  } catch (error) {
    console.error('生成关联关系提示词失败:', error)
    if (error.code === 'ECONNABORTED') {
      ElMessage.error(`任务 ${task.id} 生成关联关系提示词超时，请稍后查看任务状态或重试`)
      return
    }
    ElMessage.error(error.response?.data?.detail || `任务 ${task.id} 生成关联关系提示词失败`)
  } finally {
    // 从加载状态中移除
    scanLoading.value = scanLoading.value.filter(id => id !== task.id)
  }
}

// 删除任务
const handleDeleteTask = (task) => {
  ElMessageBox.confirm(
    `确定要删除ID为 "${task.id}" 的任务吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deleteNlsqlTaskConfig(task.id)
      ElMessage.success('任务删除成功')
      fetchTasks()
    } catch (error) {
      console.error('删除任务失败:', error)
      ElMessage.error('删除任务失败')
    }
  })
}

// 分页处理
const handleSizeChange = (val) => {
  pagination.page_size = val
  pagination.page = 1
  fetchTasks()
}

const handleCurrentChange = (val) => {
  pagination.page = val
  fetchTasks()
}

onMounted(() => {
  fetchTasks()
  fetchConfigs()
})
</script>

<style scoped>
.task-container {
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.task-header h2 {
  margin: 0;
  color: #303133;
}

.filter-section {
  margin-bottom: 20px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
}

.task-table {
  background: #fff;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.task-detail {
  max-height: 600px;
  overflow-y: auto;
}

.selected-tables {
  margin-top: 20px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
}

.selected-tables h4 {
  margin: 0 0 10px 0;
  color: #303133;
  font-size: 14px;
}

:deep(.el-table) {
  font-size: 14px;
}

:deep(.el-descriptions) {
  margin-top: 20px;
}

:deep(.el-select) {
  width: 100%;
}

:deep(.el-tag) {
  margin: 2px;
}
</style>
