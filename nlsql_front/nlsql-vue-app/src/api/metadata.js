import request from './index'

// 通过任务ID获取元数据
export const getMetadataByTaskId = (taskId) => {
  return request({
    url: `/metadata/task/${taskId}`,
    method: 'get'
  })
}

// 获取表元数据详情
export const getTableMetadataDetail = (tableMetadataId) => {
  return request({
    url: `/metadata/table/${tableMetadataId}`,
    method: 'get'
  })
}

// 更新表描述
export const updateTableDescription = (tableMetadataId, description) => {
  return request({
    url: `/metadata/table/${tableMetadataId}/description`,
    method: 'put',
    data: { description }
  })
}

// 更新字段描述
export const updateFieldDescription = (fieldMetadataId, description) => {
  return request({
    url: `/metadata/field/${fieldMetadataId}/description`,
    method: 'put',
    data: { description }
  })
}

// 删除表元数据
export const deleteTableMetadata = (tableMetadataId) => {
  return request({
    url: `/metadata/table/${tableMetadataId}`,
    method: 'delete'
  })
}

// 批量删除表元数据
export const deleteTableMetadataBatch = (tableIds) => {
  return request({
    url: `/metadata/table/batch`,
    method: 'delete',
    data: tableIds
  })
}