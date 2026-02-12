import request from './index'

// 获取表级别提示词列表（支持分页和筛选）
export function getTableLevelPromptList(params) {
  return request({
    url: '/table-level-prompt/',
    method: 'get',
    params
  })
}

// 获取单个表级别提示词详情
export function getTableLevelPrompt(id) {
  return request({
    url: `/table-level-prompt/${id}`,
    method: 'get'
  })
}

// 创建表级别提示词
export function createTableLevelPrompt(data) {
  return request({
    url: '/table-level-prompt/',
    method: 'post',
    data
  })
}

// 更新表级别提示词
export function updateTableLevelPrompt(id, data) {
  return request({
    url: `/table-level-prompt/${id}`,
    method: 'put',
    data
  })
}

// 删除表级别提示词
export function deleteTableLevelPrompt(id) {
  return request({
    url: `/table-level-prompt/${id}`,
    method: 'delete'
  })
}

// 批量删除表级别提示词
export function batchDeleteTableLevelPrompt(ids) {
  return request({
    url: '/table-level-prompt/batch-delete',
    method: 'post',
    data: { ids }
  })
}

// 生成表级别提示词
export function generateTableLevelPrompt(taskId) {
  return request({
    url: '/table-level-prompt/generate',
    method: 'post',
    data: { task_id: taskId },
    timeout: 180000
  })
}
