<script setup>
import { ref, watch, nextTick } from 'vue'
import MessageItem from './MessageItem.vue'

// 消息列表(父组件传入)
const props = defineProps({ messages: { type: Array, required: true } })

// 空态引导 chip 点击 → 直接发送示例问题
const emit = defineEmits(['send'])

const listEl = ref(null) // 滚动容器 DOM 引用

// 判断用户是否停留在底部附近(向上翻历史时不打扰,生成时才自动跟随)
function isNearBottom() {
  const el = listEl.value
  if (!el) return true // 容器不存在(首次渲染)直接滚
  // 距底部不足 120px 视为"在底部"
  return el.scrollHeight - el.scrollTop - el.clientHeight < 120
}

// 滚动到底部(等 DOM 更新完成后执行,保证新内容可见)
async function scrollToBottom() {
  const el = listEl.value
  if (!el) return
  await nextTick()
  el.scrollTop = el.scrollHeight
}

// 监听消息列表变化(新消息 / 打字机逐字追加都会触发,deep 监听嵌套字段)
watch(
  () => props.messages,
  () => {
    // 仅在用户停留在底部附近时自动滚动,避免翻历史时被拽下去
    if (isNearBottom()) scrollToBottom()
  },
  { deep: true },
)
</script>

<template>
  <div ref="listEl" class="chat-messages">
    <!-- 消息列表:每条消息一个组件 -->
    <MessageItem v-for="m in messages" :key="m.id" :message="m" />

    <!-- 空态:还没有消息时的引导页(印章式 logo) -->
    <div v-if="!messages.length" class="empty-hint">
      <!-- 大印章 logo -->
      <div class="empty-seal" aria-hidden="true">权</div>
      <h2 class="empty-title">打工人权益助手</h2>
      <p class="empty-desc">算得清加班费,读得懂劳动法</p>
      <!-- 引导示例:一点即问 -->
      <div class="empty-examples">
        <button
          class="example-chip"
          @click="$emit('send', '我月薪 8000,工作日加班 2 小时,加班费怎么算?')"
        >
          加班费怎么算?
        </button>
        <button
          class="example-chip"
          @click="$emit('send', '被公司裁员,经济补偿金怎么算?')"
        >
          被裁员怎么赔?
        </button>
        <button
          class="example-chip"
          @click="$emit('send', '月薪 15000,每月个税扣多少?')"
        >
          个税扣多少?
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 消息列表滚动区:占满中间区域 */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px 0;
}

/* 空态引导页:垂直居中 */
.empty-hint {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 24px;
}

/* 大印章 logo:朱红描边圆角方块 */
.empty-seal {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  border: 2px solid var(--seal-600);
  color: var(--seal-600);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  font-weight: 700;
  margin-bottom: 10px;
  box-shadow: 0 4px 14px rgba(178, 58, 46, 0.15);
}

/* 引导页标题 */
.empty-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--ink-900);
  letter-spacing: 1px;
}

/* 引导页描述 */
.empty-desc {
  margin: 0;
  font-size: 13px;
  color: var(--muted);
}

/* 示例引导区 */
.empty-examples {
  display: flex;
  gap: 10px;
  margin-top: 18px;
  flex-wrap: wrap;
  justify-content: center;
}

/* 示例 chip:墨蓝描边,悬停变实 */
.example-chip {
  border: 1px solid var(--ink-700);
  background: transparent;
  color: var(--ink-700);
  padding: 8px 14px;
  border-radius: 999px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
}

/* 示例 chip 悬停:墨蓝实底白字 */
.example-chip:hover {
  background: var(--ink-900);
  color: #fff;
}
</style>
