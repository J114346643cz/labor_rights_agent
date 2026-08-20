import http from './http'

// 合同体检:直接提交合同文本,后端返回体检报告 JSON
// 注意:体检含 LLM 逐条检查,耗时较长,必须单独设 120s 超时(默认 15s 会超时报网络错误)
export function checkContractText(text, sessionId) {
  return http.post('/contract/check-text', { text, session_id: sessionId }, {
    timeout: 120000,
  })
}

// 合同体检:上传合同文件(txt/md/pdf/docx),后端解析后返回体检报告 JSON
export function checkContractFile(file, sessionId) {
  // 用 FormData 传 multipart(与后端 UploadFile 参数对应)
  const formData = new FormData()
  formData.append('file', file)
  if (sessionId) formData.append('session_id', sessionId)
  return http.post('/contract/check', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000, // 体检含 LLM 检查,给足 2 分钟
  })
}

// 获取某会话的历史体检报告(带 session_id 时报告会入库,这里暂未使用)
export function listContractReports(sessionId) {
  return http.get(`/contract/reports/${sessionId}`)
}

// 下载 Word 版体检报告(把报告 JSON 发回后端渲染成 docx,返回 Blob)
export function downloadReportDocx(report) {
  return http.post(
    '/contract/report-docx',
    { report },
    { responseType: 'blob', timeout: 30000 },
  )
}

// 把已生成的报告绑定到指定会话(报告入库 + 写摘要消息,供聊天继续追问)
export function bindReportToSession(sessionId, report) {
  return http.post('/contract/report-bind', { session_id: sessionId, report })
}
