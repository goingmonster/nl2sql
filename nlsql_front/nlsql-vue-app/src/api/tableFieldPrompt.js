import request from './index'

// 获取字段提示词列表（支持分页和筛选）
export function getTableFieldPromptList(params) {
  return request({
    url: '/table-field-prompt/',
    method: 'get',
    params
  })
}

// 获取单个字段提示词详情
export function getTableFieldPrompt(id) {
  return request({
    url: `/table-field-prompt/${id}`,
    method: 'get'
  })
}

// 创建字段提示词
export function createTableFieldPrompt(data) {
  return request({
    url: '/table-field-prompt/',
    method: 'post',
    data
  })
}

// 更新字段提示词
export function updateTableFieldPrompt(id, data) {
  return request({
    url: `/table-field-prompt/${id}`,
    method: 'put',
    data
  })
}

// 删除字段提示词
export function deleteTableFieldPrompt(id) {
  return request({
    url: `/table-field-prompt/${id}`,
    method: 'delete'
  })
}

// 批量删除字段提示词
export function batchDeleteTableFieldPrompt(ids) {
  return request({
    url: '/table-field-prompt/batch-delete',
    method: 'post',
    data: { ids }
  })
}

// 按任务生成字段提示词
export function generateTableFieldPrompt(taskId) {
  return request({
    url: '/table-field-prompt/generate',
    method: 'post',
    data: { task_id: taskId },
    timeout: 180000
  })
}
