import request from './index'

// 获取数据库配置列表
export function getDbConfigList(params) {
  return request({
    url: '/db-config/',
    method: 'get',
    params
  })
}

// 搜索数据库配置
export function searchDbConfig(params) {
  return request({
    url: '/db-config/search',
    method: 'get',
    params
  })
}

// 获取单个数据库配置
export function getDbConfig(id) {
  return request({
    url: `/db-config/${id}`,
    method: 'get'
  })
}

// 创建数据库配置
export function createDbConfig(data) {
  return request({
    url: '/db-config/',
    method: 'post',
    data
  })
}

// 更新数据库配置
export function updateDbConfig(id, data) {
  return request({
    url: `/db-config/${id}`,
    method: 'put',
    data
  })
}

// 删除数据库配置
export function deleteDbConfig(id) {
  return request({
    url: `/db-config/${id}`,
    method: 'delete'
  })
}

// 批量删除数据库配置
export function batchDeleteDbConfig(ids) {
  // 确保 ids 是一个整数数组
  const idArray = Array.isArray(ids) ? ids : []
  const integerIds = idArray.map(id => parseInt(id, 10)).filter(id => !isNaN(id))

  if (integerIds.length === 0) {
    return Promise.reject(new Error('没有有效的ID可删除'))
  }

  console.log('API 请求 - 批量删除 IDs:', integerIds) // 调试日志

  return request({
    url: '/db-config/batch',
    method: 'delete',
    data: { ids: integerIds },
    // 明确指定 DELETE 请求也要发送 body
    transformRequest: [(data, headers) => {
      headers['Content-Type'] = 'application/json'
      return JSON.stringify(data)
    }]
  })
}