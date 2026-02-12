import request from './index'

// 获取提示词配置列表
export function getPromptConfigList(params) {
  return request({
    url: '/user-prompt-config/',
    method: 'get',
    params
  })
}

// 搜索提示词配置
export function searchPromptConfig(params) {
  return request({
    url: '/user-prompt-config/search',
    method: 'get',
    params
  })
}

// 获取单个提示词配置
export function getPromptConfig(id) {
  return request({
    url: `/user-prompt-config/${id}`,
    method: 'get'
  })
}

// 创建提示词配置
export function createPromptConfig(data) {
  return request({
    url: '/user-prompt-config/',
    method: 'post',
    data
  })
}

// 更新提示词配置
export function updatePromptConfig(id, data) {
  return request({
    url: `/user-prompt-config/${id}`,
    method: 'put',
    data
  })
}

// 删除提示词配置
export function deletePromptConfig(id) {
  return request({
    url: `/user-prompt-config/${id}`,
    method: 'delete'
  })
}

// 批量删除提示词配置
export function batchDeletePromptConfig(ids) {
  return request({
    url: '/user-prompt-config/batch-delete',
    method: 'post',
    data: { ids }
  })
}

// 根据名称获取配置
export function getPromptConfigByName(name) {
  return request({
    url: `/user-prompt-config/name/${name}`,
    method: 'get'
  })
}

// 根据类型获取配置
export function getPromptConfigByType(type) {
  return request({
    url: `/user-prompt-config/type/${type}`,
    method: 'get'
  })
}
