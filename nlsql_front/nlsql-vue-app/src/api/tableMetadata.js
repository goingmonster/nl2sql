import request from './index'

// 扫描数据库表
export function scanTables(params) {
  return request({
    url: '/table-metadata/scan',
    method: 'post',
    data: params
  })
}

// 获取表元数据列表
export function getTableMetadataList(params) {
  return request({
    url: '/table-metadata/',
    method: 'get',
    params
  }).catch(error => {
    console.error('TableMetadata API Error:', error)
    throw error
  })
}

// 获取单个表元数据
export function getTableMetadata(id) {
  return request({
    url: `/table-metadata/${id}`,
    method: 'get'
  })
}

// 删除表元数据
export function deleteTableMetadata(id) {
  return request({
    url: `/table-metadata/${id}`,
    method: 'delete'
  })
}

// 批量删除表元数据（通过ID列表）
export function batchDeleteTableMetadata(ids) {
  return request({
    url: '/table-metadata/batch',
    method: 'delete',
    data: { ids }
  })
}

// 按条件批量删除表元数据
export function deleteTableMetadataByConditions(params) {
  return request({
    url: '/table-metadata/by-conditions',
    method: 'delete',
    data: params
  })
}
