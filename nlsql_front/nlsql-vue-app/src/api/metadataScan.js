import request from './index'

// 扫描任务元数据
export const scanMetadata = (taskId) => {
  return request({
    url: `/metadata/scan/${taskId}`,
    method: 'post',
    timeout: 180000
  })
}
