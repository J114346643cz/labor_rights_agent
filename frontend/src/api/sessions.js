import http from './http'

// 获取所有会话列表(侧栏用,后端按创建时间倒序返回)
export function listSessions() {
  return http.get('/sessions')
}

// 新建会话(标题可选,不传则后端默认"新对话",并会在首条消息后自动生成标题)
export function createSession(title) {
  return http.post('/sessions', { title })
}

// 删除会话(连同其全部历史消息,后端级联删除)
export function deleteSession(sessionId) {
  return http.delete(`/sessions/${sessionId}`)
}

// 获取某会话的历史消息(刷新页面 / 切换会话时恢复对话用)
export function getMessages(sessionId) {
  return http.get(`/sessions/${sessionId}/messages`)
}
