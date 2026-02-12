import request from './index'

// 获取NLSQL任务配置列表（带分页和筛选）
export function getNlsqlTaskConfigList(params) {
  return request({
    url: '/nlsql-task-config/',
    method: 'get',
    params
  })
}

// 搜索NLSQL任务配置
export function searchNlsqlTaskConfig(params) {
  return request({
    url: '/nlsql-task-config/search',
    method: 'get',
    params
  })
}

// 获取单个NLSQL任务配置
export function getNlsqlTaskConfig(id) {
  return request({
    url: `/nlsql-task-config/${id}`,
    method: 'get'
  })
}

// 创建NLSQL任务配置
export function createNlsqlTaskConfig(data) {
  return request({
    url: '/nlsql-task-config/',
    method: 'post',
    data
  })
}

// 更新NLSQL任务配置
export function updateNlsqlTaskConfig(id, data) {
  return request({
    url: `/nlsql-task-config/${id}`,
    method: 'put',
    data
  })
}

// 删除NLSQL任务配置
export function deleteNlsqlTaskConfig(id) {
  return request({
    url: `/nlsql-task-config/${id}`,
    method: 'delete'
  })
}

// 批量删除NLSQL任务配置
export function batchDeleteNlsqlTaskConfig(ids) {
  // 确保 ids 是一个整数数组
  const idArray = Array.isArray(ids) ? ids : []
  const integerIds = idArray.map(id => parseInt(id, 10)).filter(id => !isNaN(id))

  if (integerIds.length === 0) {
    return Promise.reject(new Error('没有有效的ID可删除'))
  }

  console.log('API 请求 - 批量删除 NLSQL 任务配置 IDs:', integerIds)

  return request({
    url: '/nlsql-task-config/batch',
    method: 'delete',
    data: { ids: integerIds },
    // 明确指定 DELETE 请求也要发送 body
    transformRequest: [(data, headers) => {
      headers['Content-Type'] = 'application/json'
      return JSON.stringify(data)
    }]
  })
}