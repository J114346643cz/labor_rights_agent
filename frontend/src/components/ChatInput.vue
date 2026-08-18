<script setup>
import { ref } from 'vue'

// 是否正在生成(父组件传入,生成中按钮变为"停止")
const props = defineProps({ streaming: { type: Boolean, default: false } })
const emit = defineEmits(['send', 'stop'])

const text = ref('') // 输入框内容

// 点击发送 / 按 Enter:非空且未在生成时触发 send 事件
function handleSend() {
  // 空内容或正在生成时不发送
  if (!text.value.trim() || props.streaming) return
  emit('send', text.value) // 把消息抛给父组件处理
  text.value = '' // 发送成功后清空输入框
}

// 键盘事件:Enter 发送,Shift+Enter 换行
function handleKeydown(e) {
  // 按 Enter 且未按 Shift → 发送(并阻止默认的换行行为)
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}
</script>

<template>
  <div class="chat-input">
    <!-- 多行输入框:自适应高度,Enter 发送 -->
    <el-input
      v-model="text"
      type="textarea"
      :autosize="{ minRows: 2, maxRows: 6 }"
      resize="none"
      placeholder="输入你的问题,如:我月薪 8000,加班费怎么算?(Enter 发送,Shift+Enter 换行)"
      @keydown="handleKeydown"
    />
    <!-- 操作按钮:未生成时显示"发送",生成中显示"停止" -->
    <div class="input-actions">
      <!-- 发送按钮:朱红(呼应印章主题) -->
      <el-button
        v-if="!props.streaming"
        class="send-btn"
        type="primary"
        @click="handleSend"
      >
        <el-icon><Promotion /></el-icon>
        发送
      </el-button>
      <!-- 停止按钮(生成中):中断 SSE 流 -->
      <el-button v-else type="danger" @click="emit('stop')">
        <el-icon><VideoPause /></el-icon>
        停止
      </el-button>
    </div>
  </div>
</template>

<style scoped>
/* 输入区容器:底部白底,细上边线 */
.chat-input {
  padding: 16px 24px 18px;
  background: var(--card);
  border-top: 1px solid var(--line);
}

/* 输入框:纸色底,圆角克制 */
.chat-input :deep(.el-textarea__inner) {
  background: #faf9f6;
  border-radius: 8px;
  box-shadow: none;
  border-color: var(--line);
}

/* 输入框聚焦:朱红描边 */
.chat-input :deep(.el-textarea__inner:focus) {
  border-color: var(--seal-600);
}

/* 按钮行:靠右对齐 */
.input-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

/* 发送按钮:朱红实底(覆盖 Element Plus 默认主题色) */
.send-btn {
  --el-button-bg-color: var(--seal-600);
  --el-button-border-color: var(--seal-600);
  --el-button-hover-bg-color: #c74a3d;
  --el-button-hover-border-color: #c74a3d;
}
</style>
