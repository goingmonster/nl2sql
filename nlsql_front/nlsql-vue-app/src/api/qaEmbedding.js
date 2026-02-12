import request from './index'

// 获取问答向量列表（支持分页和筛选）
export function getQaEmbeddingList(params) {
  return request({
    url: '/qa-embedding/',
    method: 'get',
    params
  })
}

// 获取单个问答向量详情
export function getQaEmbedding(id) {
  return request({
    url: `/qa-embedding/${id}`,
    method: 'get'
  })
}

// 创建问答向量
export function createQaEmbedding(data) {
  return request({
    url: '/qa-embedding/',
    method: 'post',
    data
  })
}

// 更新问答向量
export function updateQaEmbedding(id, data) {
  return request({
    url: `/qa-embedding/${id}`,
    method: 'put',
    data
  })
}

// 删除问答向量
export function deleteQaEmbedding(id) {
  return request({
    url: `/qa-embedding/${id}`,
    method: 'delete'
  })
}

// 批量删除问答向量
export function batchDeleteQaEmbedding(ids) {
  return request({
    url: '/qa-embedding/batch-delete',
    method: 'post',
    data: { ids }
  })
}

// 导入问答对
export function importQaEmbedding(data) {
  return request({
    url: '/qa-embedding/import',
    method: 'post',
    data
  })
}

// AI 生成 where 条件
export function generateQaWhereConditions(data) {
  return request({
    url: '/qa-embedding/generate-where-conditions',
    method: 'post',
    data,
    timeout: 180000
  })
}

export function exportQaEmbeddings(ids) {
  return request({
    url: '/qa-embedding/export',
    method: 'post',
    data: { ids }
  })
}
