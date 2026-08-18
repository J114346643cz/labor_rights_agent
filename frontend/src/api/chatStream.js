// SSE 流式聊天:用 fetch + ReadableStream 消费后端的 text/event-stream 响应
// 为什么不用浏览器原生 EventSource:EventSource 只支持 GET,而聊天请求需要 POST body

/**
 * 解析一条 SSE 事件原文,拆出事件名与负载数据。
 * SSE 事件格式:"event: delta\ndata: {...}"(事件名缺省为 message)
 *
 * 参数:
 * - raw: 一条事件原文(不含结尾空行),如 'event: delta\ndata: {"text":"你"}'
 * 返回:
 * - { event: "delta", data: {text: "你"} }
 */
function parseEvent(raw) {
  // 逐行解析:event 行取事件名,data 行拼接负载(规范允许 data 多行)
  let event = 'message' // SSE 规范:未声明 event 时的默认事件名
  let dataText = ''
  for (const line of raw.split('\n')) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataText += line.slice(5).trim()
    }
  }
  // data 为空的事件(如心跳注释)没有意义,跳过
  if (!dataText) return null
  // 后端 data 一律是 JSON,直接解析
  return { event, data: JSON.parse(dataText) }
}

/**
 * 发起 SSE 流式聊天请求,按事件类型调用对应回调。
 *
 * 参数:
 * - sessionId: 会话 ID(首次发送传 null,后端会新建会话并在 session 事件里返回)
 * - message: 用户消息文本
 * - signal: AbortController 的 signal(调用方用它实现"停止生成")
 * - handlers: 事件回调 { onSession, onTool, onDelta, onDone, onError }
 */
export function streamChat({ sessionId, message, signal, handlers }) {
  // 发起 POST 请求,后端以 text/event-stream 分块返回
  fetch('/api/agent/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message }),
    signal, // 挂上 AbortController 信号,支持中途取消
  })
    .then(async (response) => {
      // 非 2xx:解析后端 detail 作为错误信息抛出
      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || `请求失败(${response.status})`)
      }
      // 逐块读取响应体字节流,解析出完整 SSE 事件后分发
      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = '' // 跨 chunk 残留的文本(一条事件可能被拆到两个网络 chunk)
      for (;;) {
        const { done, value } = await reader.read()
        if (done) break // 流已结束(收到 done 事件后后端正常关闭)
        buffer += decoder.decode(value, { stream: true })
        // 事件之间用空行(\n\n)分隔:每次取出完整事件,剩余留在 buffer
        let sepIndex
        while ((sepIndex = buffer.indexOf('\n\n')) !== -1) {
          const rawEvent = buffer.slice(0, sepIndex) // 一条事件原文
          buffer = buffer.slice(sepIndex + 2)
          const parsed = parseEvent(rawEvent)
          if (parsed) dispatch(parsed, handlers) // 解析成功则分发
        }
      }
    })
    .catch((error) => {
      // 主动停止生成(abort)不算错误,静默返回
      if (error.name === 'AbortError') return
      // 网络异常:通知调用方
      handlers.onError?.(error.message || '网络错误,请稍后重试')
    })
}

// 按事件类型分发到 handlers 里对应的回调(未注册的回调自动忽略)
function dispatch({ event, data }, handlers) {
  const callback = {
    session: handlers.onSession, // 会话信息(session_id / rewrite_query)
    tool: handlers.onTool, // 调用了某工具
    delta: handlers.onDelta, // 回答文本增量(打字机)
    done: handlers.onDone, // 生成结束(法条来源 + 工具列表)
    error: handlers.onError, // 后端出错
  }[event]
  callback?.(data)
}
