<script setup>
import { onMounted } from 'vue'
import { useChat } from './composables/useChat'
import SessionSidebar from './components/SessionSidebar.vue'
import ChatMessages from './components/ChatMessages.vue'
import ChatInput from './components/ChatInput.vue'

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

// 页面加载时拉取会话列表(历史会话在侧栏恢复)
onMounted(loadSessions)
</script>

<template>
  <div class="app-layout">
    <!-- 左侧:会话栏(新建 / 切换 / 删除) -->
    <SessionSidebar
      :sessions="sessions"
      :active-session-id="activeSessionId"
      @create="handleCreate"
      @select="selectSession"
      @delete="handleDelete"
    />

    <!-- 右侧:聊天区 -->
    <main class="chat-area">
      <!-- 顶部标题栏:印章标识 + 当前会话标题 -->
      <header class="chat-header">
        <!-- 印章式 logo:朱红方块 + 白字,呼应"维权档案"主题 -->
        <div class="brand-mark" aria-hidden="true">权</div>
        <!-- 应用名(会话未选中时显示) -->
        <span v-if="!activeSession" class="brand-name">打工人权益助手</span>
        <!-- 当前会话标题(已选中会话时显示) -->
        <span v-else class="session-title" :title="activeSession.title">
          {{ activeSession.title }}
        </span>
      </header>

      <!-- 消息列表(自动滚动到底部;空态引导 chip 点击直接发问) -->
      <ChatMessages :messages="messages" @send="sendMessage" />

      <!-- 底部输入区(发送 / 停止生成) -->
      <ChatInput :streaming="streaming" @send="sendMessage" @stop="stopStream" />
    </main>
  </div>
</template>

<style scoped>
/* 整体布局:侧栏 + 聊天区左右并排,撑满全屏 */
.app-layout {
  display: flex;
  height: 100vh;
  background: var(--paper);
}

/* 聊天区:右侧弹性占满剩余宽度 */
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
</style>
