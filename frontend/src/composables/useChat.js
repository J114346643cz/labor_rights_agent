import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  listSessions,
  createSession,
  deleteSession,
  getMessages,
} from '../api/sessions'
import { streamChat } from '../api/chatStream'

/**
 * 聊天状态机:统一管理会话列表、消息列表与 SSE 流式收发。
 *
 * 消息结构(前端内部):
 * { id, role: "user"|"assistant", content, sources: [], toolCalls: [], streaming: false }
 * - sources: 法条引用列表(来自 done 事件 / 历史消息)
 * - toolCalls: 调用过的工具名列表(显示徽标)
 * - streaming: 是否还在流式生成(控制打字机动画)
 */
export function useChat() {
  const sessions = ref([]) // 会话列表(侧栏展示)
  const activeSessionId = ref(null) // 当前选中的会话 ID
  const messages = ref([]) // 当前会话的消息列表
  const streaming = ref(false) // 是否正在流式生成(控制"停止"按钮显隐)
  const controller = ref(null) // 当前流的 AbortController(停止生成用)

  // 当前会话对象(顶部标题栏展示标题)
  const activeSession = computed(
    () => sessions.value.find((s) => s.id === activeSessionId.value) || null,
  )

  // 加载会话列表(页面初始化 / 新建 / 删除后调用)
  async function loadSessions() {
    const { data } = await listSessions()
    sessions.value = data
    // 若当前选中的会话已被删除(如被其他操作清理),自动取消选中
    if (
      activeSessionId.value &&
      !sessions.value.some((s) => s.id === activeSessionId.value)
    ) {
      activeSessionId.value = null
      messages.value = []
    }
  }

  // 新建会话并选中(标题暂用后端默认,首条消息后自动生成)
  async function handleCreate() {
    const { data } = await createSession()
    sessions.value.unshift(data) // 插到列表最前(后端按创建时间倒序,新建的在最前)
    await selectSession(data.id) // 新建后直接进入该会话
  }

  // 切换会话:加载该会话的历史消息,恢复对话上下文
  async function selectSession(sessionId) {
    // 若正在生成,先停止,避免后台继续收流
    if (streaming.value) stopStream()
    activeSessionId.value = sessionId
    const { data } = await getMessages(sessionId)
    // 后端历史消息转成前端消息结构(sources 反序列化,工具列表从 calc_result 取)
    messages.value = data.map((m) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      sources: m.sources || [],
      toolCalls: m.calc_result?.tools || [],
      streaming: false,
    }))
  }

  // 删除会话(父组件已弹确认框,这里只调接口 + 刷新列表)
  async function handleDelete(sessionId) {
    await deleteSession(sessionId)
    // 刷新列表:若删的是当前会话,loadSessions 里会自动取消选中
    await loadSessions()
  }

  // 停止生成:中断 fetch 流,把流式占位消息标记为完成
  function stopStream() {
    controller.value?.abort() // 中断后端流
    controller.value = null
    streaming.value = false
    // 保留已收到的部分内容,去掉打字机动画
    const last = messages.value[messages.value.length - 1]
    if (last?.streaming) last.streaming = false
  }

  // 发送消息:本地立即插入占位,再发起 SSE 流式请求逐字填充
  async function sendMessage(text) {
    const content = text.trim()
    // 空消息或正在生成时忽略(防止连发)
    if (!content || streaming.value) return

    // 1. 本地插入用户消息 + 空的助手占位消息(流式期间持续填充内容)
    messages.value.push({
      id: `local-${Date.now()}`,
      role: 'user',
      content,
      sources: [],
      toolCalls: [],
      streaming: false,
    })
    messages.value.push({
      id: `local-stream-${Date.now()}`,
      role: 'assistant',
      content: '',
      sources: [],
      toolCalls: [],
      streaming: true,
    })
    // 记录助手占位消息在数组里的索引:
    // 回调里必须通过 messages.value[assistantIdx] 操作(Vue 响应式代理),
    // 不能持有原始对象引用——直接改原始对象不会触发视图更新(打字机不动的根因)
    const assistantIdx = messages.value.length - 1
    streaming.value = true

    // 2. 发起 SSE 流式请求(handlers 更新本地占位消息)
    controller.value = new AbortController()
    streamChat({
      sessionId: activeSessionId.value, // 首条消息时为 null,后端会新建会话
      message: content,
      signal: controller.value.signal,
      handlers: {
        // session 事件:首次发送时后端返回新会话 ID,刷新侧栏并选中它
        onSession(payload) {
          if (!activeSessionId.value) {
            activeSessionId.value = payload.session_id
            loadSessions() // 侧栏出现新会话(首条消息自动生成标题)
          }
        },
        // tool 事件:记录调用过的工具名(显示徽标)
        onTool(payload) {
          messages.value[assistantIdx].toolCalls.push(payload.name)
        },
        // delta 事件:逐字追加回答内容(打字机效果)
        onDelta(payload) {
          messages.value[assistantIdx].content += payload.text
        },
        // done 事件:填上法条来源,结束流式状态
        onDone(payload) {
          messages.value[assistantIdx].sources = payload.sources || []
          messages.value[assistantIdx].streaming = false
          streaming.value = false
          controller.value = null
        },
        // error 事件:提示错误;若还没收到任何内容,占位消息直接换成错误文案
        onError(message) {
          messages.value[assistantIdx].streaming = false
          streaming.value = false
          controller.value = null
          if (!messages.value[assistantIdx].content) {
            messages.value[assistantIdx].content = `⚠️ ${message}`
          } else {
            // 已收到部分内容:保留内容,只弹错误提示
            ElMessage.error(message)
          }
        },
      },
    })
  }

  // 对外暴露状态与操作方法(App.vue 注入各组件)
  return {
    sessions,
    activeSessionId,
    activeSession,
    messages,
    streaming,
    loadSessions,
    handleCreate,
    selectSession,
    handleDelete,
    sendMessage,
    stopStream,
  }
}
