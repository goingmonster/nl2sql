import request from './index'

// 获取LLM配置列表（支持分页和筛选）
export function getLlmConfigList(params) {
  return request({
    url: '/llm-config/',
    method: 'get',
    params
  })
}

// 获取单个LLM配置
export function getLlmConfig(id) {
  return request({
    url: `/llm-config/${id}`,
    method: 'get'
  })
}

// 创建LLM配置
export function createLlmConfig(data) {
  return request({
    url: '/llm-config/',
    method: 'post',
    data
  })
}

// 更新LLM配置
export function updateLlmConfig(id, data) {
  return request({
    url: `/llm-config/${id}`,
    method: 'put',
    data
  })
}

// 删除LLM配置
export function deleteLlmConfig(id) {
  return request({
    url: `/llm-config/${id}`,
    method: 'delete'
  })
}

// 批量删除LLM配置
export function batchDeleteLlmConfigs(ids) {
  // 确保 ids 是一个整数数组
  const idArray = Array.isArray(ids) ? ids : []
  const integerIds = idArray.map(id => parseInt(id, 10)).filter(id => !isNaN(id))

  if (integerIds.length === 0) {
    return Promise.reject(new Error('没有有效的ID可删除'))
  }

  console.log('API 请求 - 批量删除 LLM 配置 IDs:', integerIds)

  // 构建查询参数，使用数组格式 ids[]=4&ids[]=5&ids[]=6
  const params = new URLSearchParams()
  integerIds.forEach(id => {
    params.append('ids', id.toString())
  })

  return request({
    url: `/llm-config/batch/bulk?${params.toString()}`,
    method: 'delete'
  })
}

// 根据供应商获取LLM配置列表
export function getLlmConfigsByProvider(provider) {
  return request({
    url: `/llm-config/provider/${provider}`,
    method: 'get'
  })
}

// 启用LLM配置
export function enableLlmConfig(id) {
  return request({
    url: `/llm-config/${id}/enable`,
    method: 'post'
  })
}

// 禁用LLM配置
export function disableLlmConfig(id) {
  return request({
    url: `/llm-config/${id}/disable`,
    method: 'post'
  })
}