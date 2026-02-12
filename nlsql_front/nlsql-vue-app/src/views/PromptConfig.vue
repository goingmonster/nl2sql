<template>
  <div class="prompt-config-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>提示词生成配置</h2>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        新建配置
      </el-button>
    </div>

    <!-- 配置列表 -->
    <el-card class="config-list">
      <el-table
        :data="configList"
        v-loading="loading"
        style="width: 100%"
      >
        <el-table-column prop="config_name" label="配置名称" width="200" />
        <el-table-column prop="config_type" label="配置类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getConfigTypeTag(row.config_type)">
              {{ getConfigTypeName(row.config_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="system_config" label="系统描述" show-overflow-tooltip />
        <el-table-column label="表描述数量" width="120">
          <template #default="{ row }">
            {{ row.table_notes ? row.table_notes.length : 0 }}
          </template>
        </el-table-column>
        <el-table-column label="字段描述数量" width="120">
          <template #default="{ row }">
            {{ row.field_notes ? row.field_notes.length : 0 }}
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>

    <!-- 创建/编辑配置对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingConfig ? '编辑配置' : '新建配置'"
      width="80%"
      top="5vh"
      class="config-dialog"
    >
      <el-form
        ref="configFormRef"
        :model="configForm"
        :rules="configRules"
        label-width="140px"
      >
        <el-form-item label="配置名称" prop="config_name">
          <el-input v-model="configForm.config_name" placeholder="请输入配置名称" />
        </el-form-item>

        <el-form-item label="配置类型" prop="config_type">
          <el-select v-model="configForm.config_type" placeholder="请选择配置类型">
            <el-option label="默认" :value="1" />
            <el-option label="自定义" :value="2" />
            <el-option label="系统预制" :value="3" />
          </el-select>
        </el-form-item>

        <el-form-item label="系统级别描述">
          <el-input
            v-model="configForm.system_config"
            type="textarea"
            :rows="3"
            placeholder="请输入系统级别的描述"
          />
        </el-form-item>

        <!-- 表需要注意的地方 -->
        <el-form-item label="表描述规则">
          <el-button type="primary" plain @click="addTableNote">
            <el-icon><Plus /></el-icon>
            添加表描述
          </el-button>

          <!-- 预设选项 -->
          <div class="preset-options" style="margin-top: 10px;">
            <span class="preset-label">快速添加预设：</span>
            <el-button
              v-for="preset in tableNotePresets"
              :key="preset"
              size="small"
              plain
              @click="addTableNoteWithText(preset)"
            >
              {{ preset }}
            </el-button>
          </div>

          <!-- 表描述列表 -->
          <div class="notes-list" v-if="configForm.table_notes.length > 0" style="margin-top: 15px;">
            <div
              v-for="(note, index) in configForm.table_notes"
              :key="index"
              class="note-item"
            >
              <el-input
                v-model="configForm.table_notes[index]"
                placeholder="请输入表描述规则"
                style="margin-bottom: 10px;"
              />
              <el-button
                size="small"
                type="danger"
                plain
                @click="removeTableNote(index)"
                style="margin-bottom: 10px;"
              >
                删除
              </el-button>
            </div>
          </div>
        </el-form-item>

        <!-- 字段需要注意的使用方式 -->
        <el-form-item label="字段描述规则">
          <el-button type="primary" plain @click="addFieldNote">
            <el-icon><Plus /></el-icon>
            添加字段描述
          </el-button>

          <!-- 预设选项 -->
          <div class="preset-options" style="margin-top: 10px;">
            <span class="preset-label">快速添加预设：</span>
            <el-button
              v-for="preset in fieldNotePresets"
              :key="preset"
              size="small"
              plain
              @click="addFieldNoteWithText(preset)"
            >
              {{ preset }}
            </el-button>
          </div>

          <!-- 字段描述列表 -->
          <div class="notes-list" v-if="configForm.field_notes.length > 0" style="margin-top: 15px;">
            <div
              v-for="(note, index) in configForm.field_notes"
              :key="index"
              class="note-item"
            >
              <el-input
                v-model="configForm.field_notes[index]"
                placeholder="请输入字段描述规则"
                style="margin-bottom: 10px;"
              />
              <el-button
                size="small"
                type="danger"
                plain
                @click="removeFieldNote(index)"
                style="margin-bottom: 10px;"
              >
                删除
              </el-button>
            </div>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleDialogCancel">取消</el-button>
          <el-button type="primary" @click="handleSaveConfig" :loading="saving">
            保存
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  getPromptConfigList,
  createPromptConfig,
  updatePromptConfig,
  deletePromptConfig
} from '@/api/promptConfig'

// 基础数据
const loading = ref(false)
const saving = ref(false)
const showCreateDialog = ref(false)
const editingConfig = ref(null)
const configFormRef = ref(null)

// 分页数据
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 配置列表
const configList = ref([])

// 表单数据
const configForm = reactive({
  config_name: '',
  config_type: 1,
  system_config: '',
  table_notes: [],
  field_notes: []
})

// 表单验证规则
const configRules = {
  config_name: [
    { required: true, message: '请输入配置名称', trigger: 'blur' }
  ],
  config_type: [
    { required: true, message: '请选择配置类型', trigger: 'change' }
  ]
}

// 表描述预设选项
const tableNotePresets = [
  '可以用来查询...',
  '可以用来统计分析',
  '可以用来进行',
  '简洁明了地描述表的用途',
  '结合表特定信息（如果有）'
]

// 字段描述预设选项
const fieldNotePresets = [
  '字段名称和类型：明确说明字段的数据类型',
  '字段描述和用途：用通俗易懂的语言解释',
  '空值率和使用建议：给出具体数值和使用建议',
  '样例数据：提供实际的数据样本',
  '枚举值情况：如果是枚举字段且枚举少于10个，使用【】列出5个枚举值',
  '是否需要简繁体转化：明确说明是否需要进行简繁体转换',
  '是否需要数字汉字泛化查询：明确说明是否需要数字和汉字的泛化查询'
]

// 获取配置类型标签样式
const getConfigTypeTag = (type) => {
  const types = {
    1: '',
    2: 'success',
    3: 'warning'
  }
  return types[type] || ''
}

// 获取配置类型名称
const getConfigTypeName = (type) => {
  const types = {
    1: '默认',
    2: '自定义',
    3: '系统预制'
  }
  return types[type] || '未知'
}

// 格式化日期时间
const formatDateTime = (dateTime) => {
  if (!dateTime) return ''
  return new Date(dateTime).toLocaleString('zh-CN')
}

// 获取配置列表
const fetchConfigList = async () => {
  loading.value = true
  try {
    const response = await getPromptConfigList({
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value
    })
    configList.value = response.data || []
    total.value = response.total || 0
  } catch (error) {
    ElMessage.error('获取配置列表失败：' + error.message)
  } finally {
    loading.value = false
  }
}

// 处理页码变化
const handlePageChange = (page) => {
  currentPage.value = page
  fetchConfigList()
}

// 处理每页条数变化
const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  fetchConfigList()
}

// 添加表描述
const addTableNote = () => {
  configForm.table_notes.push('')
}

// 添加预设表描述
const addTableNoteWithText = (text) => {
  configForm.table_notes.push(text)
}

// 删除表描述
const removeTableNote = (index) => {
  configForm.table_notes.splice(index, 1)
}

// 添加字段描述
const addFieldNote = () => {
  configForm.field_notes.push('')
}

// 添加预设字段描述
const addFieldNoteWithText = (text) => {
  configForm.field_notes.push(text)
}

// 删除字段描述
const removeFieldNote = (index) => {
  configForm.field_notes.splice(index, 1)
}

// 处理编辑
const handleEdit = (row) => {
  editingConfig.value = row
  configForm.config_name = row.config_name
  configForm.config_type = row.config_type
  configForm.system_config = row.system_config || ''
  configForm.table_notes = [...(row.table_notes || [])]
  configForm.field_notes = [...(row.field_notes || [])]
  showCreateDialog.value = true
}

// 处理删除
const handleDelete = (row) => {
  ElMessageBox.confirm(
    `确定要删除配置"${row.config_name}"吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deletePromptConfig(row.id)
      ElMessage.success('删除成功')
      fetchConfigList()
    } catch (error) {
      ElMessage.error('删除失败：' + error.message)
    }
  })
}

// 处理对话框取消
const handleDialogCancel = () => {
  showCreateDialog.value = false
  editingConfig.value = null
  resetForm()
}

// 重置表单
const resetForm = () => {
  configForm.config_name = ''
  configForm.config_type = 1
  configForm.system_config = ''
  configForm.table_notes = []
  configForm.field_notes = []
  if (configFormRef.value) {
    configFormRef.value.clearValidate()
  }
}

// 保存配置
const handleSaveConfig = async () => {
  if (!configFormRef.value) return

  try {
    await configFormRef.value.validate()
  } catch (error) {
    return
  }

  saving.value = true
  try {
    const data = {
      config_name: configForm.config_name,
      config_type: configForm.config_type,
      system_config: configForm.system_config,
      table_notes: configForm.table_notes.filter(item => item.trim()),
      field_notes: configForm.field_notes.filter(item => item.trim())
    }

    if (editingConfig.value) {
      await updatePromptConfig(editingConfig.value.id, data)
      ElMessage.success('更新配置成功')
    } else {
      await createPromptConfig(data)
      ElMessage.success('创建配置成功')
    }

    showCreateDialog.value = false
    editingConfig.value = null
    resetForm()
    fetchConfigList()
  } catch (error) {
    ElMessage.error('保存失败：' + error.message)
  } finally {
    saving.value = false
  }
}

// 组件挂载时获取数据
onMounted(() => {
  fetchConfigList()
})
</script>

<style scoped>
.prompt-config-container {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: calc(100vh - 120px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.page-header h2 {
  margin: 0;
  color: #303133;
  font-size: 24px;
}

.config-list {
  margin-bottom: 20px;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.preset-options {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.preset-label {
  font-size: 14px;
  color: #606266;
}

.notes-list {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 15px;
  background-color: #fafafa;
}

.note-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.config-dialog .el-dialog__body {
  padding: 20px;
  max-height: 70vh;
  overflow-y: auto;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>