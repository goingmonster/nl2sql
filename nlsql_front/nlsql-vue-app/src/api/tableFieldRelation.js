import request from './index'

// 获取实体关系列表（支持分页和筛选）
export function getTableFieldRelationList(params) {
  return request({
    url: '/table-field-relation/',
    method: 'get',
    params
  })
}

// 获取单个实体关系详情
export function getTableFieldRelation(id) {
  return request({
    url: `/table-field-relation/${id}`,
    method: 'get'
  })
}

// 创建实体关系
export function createTableFieldRelation(data) {
  return request({
    url: '/table-field-relation/',
    method: 'post',
    data
  })
}

// 更新实体关系
export function updateTableFieldRelation(id, data) {
  return request({
    url: `/table-field-relation/${id}`,
    method: 'put',
    data
  })
}

// 删除实体关系
export function deleteTableFieldRelation(id) {
  return request({
    url: `/table-field-relation/${id}`,
    method: 'delete'
  })
}

// 批量删除实体关系
export function batchDeleteTableFieldRelation(ids) {
  return request({
    url: '/table-field-relation/batch-delete',
    method: 'post',
    data: { ids }
  })
}

// 生成关联关系提示词
export function generateTableFieldRelation(taskId) {
  return request({
    url: '/table-field-relation/generate',
    method: 'post',
    data: { task_id: taskId },
    timeout: 180000
  })
}
