<script setup>
import { ref, onMounted } from 'vue'
import { useChat } from './composables/useChat'
import SessionSidebar from './components/SessionSidebar.vue'
import ChatMessages from './components/ChatMessages.vue'
import ChatInput from './components/ChatInput.vue'
import ContractCheck from './views/ContractCheck.vue'
import PolicyLibrary from './views/PolicyLibrary.vue'
import StatementView from './views/StatementView.vue'
import { bindReportToSession } from './api/contract'

// 聊天状态机:统一管理会话列表、消息列表与 SSE 流式收发
const {
  sessions, // 会话列表(侧栏展示)
  activeSessionId, // 当前选中会话 ID
  activeSession, // 当前会话对象(标题栏用)
  messages, // 当前会话的消息列表
  streaming, // 是否正在流式生成
  loadSessions, // 加载会话列表
  handleCreate, // 新建会话
  selectSession, // 切换会话
  handleDelete, // 删除会话
  sendMessage, // 发送消息(SSE 流式)
  stopStream, // 停止生成
} = useChat()

// 当前功能视图:chat=聊天 / contract=合同体检 / policy=政策库 / statement=核算单
const activeView = ref('chat')

// 聊天上下文提示(合同体检跳转后显示横幅:本对话基于哪份体检报告)
const chatContext = ref(null)

// 切换视图:聊天状态保留在 useChat 里,切回时原样恢复
function changeView(view) {
  activeView.value = view
}

// 合同体检后"去聊天继续提问":
// 1. 新建一个体检专用会话(标题醒目:合同体检 · 文件名,侧栏一眼可辨)
// 2. 把报告绑定到该会话(报告入库 + 写摘要消息,Agent 能记得报告结论)
// 3. 聊天视图显示上下文横幅,明确提示这是基于体检报告的对话
async function askChat(fileName, report) {
  // 新建体检专用会话(标题明显,区别于普通对话)
  const sessionId = await handleCreate(`合同体检 · ${fileName}`)
  // 报告绑定到新会话(写摘要消息,后续追问有上下文)
  if (report) {
    try {
      await bindReportToSession(sessionId, report)
      await selectSession(sessionId) // 重新拉取消息(含刚写入的体检摘要)
    } catch {
      /* 绑定失败不阻塞跳转,聊天里仍可手动追问 */
    }
  }
  // 记录上下文提示(聊天视图横幅显示)
  chatContext.value = { fileName }
  changeView('chat') // 切到聊天视图
}

// 页面加载时拉取会话列表(历史会话在侧栏恢复)
onMounted(loadSessions)
</script>

<template>
  <div class="app-layout">
    <!-- 左侧:功能导航 + 会话栏 -->
    <SessionSidebar
      :sessions="sessions"
      :active-session-id="activeSessionId"
      :active-view="activeView"
      @create="handleCreate"
      @select="selectSession"
      @delete="handleDelete"
      @change-view="changeView"
    />

    <!-- 右侧:主区(按视图切换) -->
    <main class="chat-area">
      <!-- 聊天视图:标题栏 + 消息列表 + 输入区 -->
      <template v-if="activeView === 'chat'">
        <header class="chat-header">
          <!-- 印章式 logo:朱红方块 + 白字,呼应"维权档案"主题 -->
          <div class="brand-mark" aria-hidden="true">权</div>
          <!-- 应用名(会话未选中时显示) -->
          <span v-if="!activeSession" class="brand-name">劳动智法助手</span>
          <!-- 当前会话标题(已选中会话时显示) -->
          <span v-else class="session-title" :title="activeSession.title">
            {{ activeSession.title }}
          </span>
        </header>

        <!-- 体检对话上下文横幅:提示用户这是基于体检报告的对话 -->
        <div v-if="chatContext" class="context-banner">
          <span class="banner-mark" aria-hidden="true">报告</span>
          本对话基于《{{ chatContext.fileName }}》体检报告,可继续追问报告中的条款问题
        </div>

        <!-- 消息列表(自动滚动到底部;空态引导 chip 点击直接发问) -->
        <ChatMessages :messages="messages" @send="sendMessage" />

        <!-- 底部输入区(发送 / 停止生成) -->
        <ChatInput :streaming="streaming" @send="sendMessage" @stop="stopStream" />
      </template>

      <!-- 合同体检视图(带当前会话 ID;ask-chat 传文件名+报告,用于新建体检专用会话) -->
      <ContractCheck
        v-else-if="activeView === 'contract'"
        :session-id="activeSessionId"
        @ask-chat="(report) => askChat(report?.file_name || '合同', report)"
      />

      <!-- 政策库视图 -->
      <PolicyLibrary v-else-if="activeView === 'policy'" />

      <!-- 核算单视图 -->
      <StatementView v-else-if="activeView === 'statement'" />
    </main>
  </div>
</template>

<style scoped>
/* 整体布局:侧栏 + 主区左右并排,撑满全屏 */
.app-layout {
  display: flex;
  height: 100vh;
  background: var(--paper);
}

/* 主区:右侧弹性占满剩余宽度 */
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* 顶部标题栏:纸白底,细分割线 */
.chat-header {
  height: 56px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 24px;
  background: var(--card);
  border-bottom: 1px solid var(--line);
}

/* 印章式 logo:朱红圆角方块,白字 */
.brand-mark {
  width: 30px;
  height: 30px;
  border-radius: 6px;
  background: var(--seal-600);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 700;
  flex-shrink: 0;
}

/* 应用名:衬线感标题 */
.brand-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--ink-900);
  letter-spacing: 0.5px;
}

/* 会话标题:次要层级 */
.session-title {
  font-size: 14px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 体检对话上下文横幅:纸色底,朱红左边条,醒目提示 */
.context-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 12px 24px 0;
  padding: 8px 14px;
  background: #faf3f2;
  border: 1px solid #e8cfca;
  border-left: 3px solid var(--seal-600);
  border-radius: 6px;
  font-size: 13px;
  color: var(--ink-700);
}

/* 横幅标记:朱红印章小牌 */
.banner-mark {
  background: var(--seal-600);
  color: #fff;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 3px;
  flex-shrink: 0;
}
</style>
