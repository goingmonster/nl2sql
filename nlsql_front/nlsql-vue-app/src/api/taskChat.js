import request from './index'

// 任务问答
export function askTaskChat(data) {
  return request({
    url: '/task-chat/ask',
    method: 'post',
    data,
    timeout: 180000
  })
}

// 会话列表
export function getTaskChatSessions(params) {
  return request({
    url: '/task-chat/sessions',
    method: 'get',
    params
  })
}

// 获取会话详情
export function getTaskChatSession(sessionId) {
  return request({
    url: `/task-chat/sessions/${sessionId}`,
    method: 'get'
  })
}

// 删除会话
export function deleteTaskChatSession(sessionId) {
  return request({
    url: `/task-chat/sessions/${sessionId}`,
    method: 'delete'
  })
}

// 会话对话列表
export function getTaskChatConversations(sessionId, params) {
  return request({
    url: `/task-chat/sessions/${sessionId}/conversations`,
    method: 'get',
    params
  })
}

// 更新对话反馈
export function updateTaskChatConversationFeedback(conversationId, data) {
  return request({
    url: `/task-chat/conversations/${conversationId}/feedback`,
    method: 'patch',
    data
  })
}
