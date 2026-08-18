<script setup>
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

// markdown 渲染器:助手回答支持加粗/列表/表格等排版
// html: true 允许内联 HTML,但输出会再过 DOMPurify 消毒,防 XSS
const md = new MarkdownIt({ html: true, linkify: true })

// 单条消息(父组件传入,结构见 useChat.js 说明)
const props = defineProps({ message: { type: Object, required: true } })

// 是否为助手消息(决定气泡样式与是否渲染 markdown)
const isAssistant = computed(() => props.message.role === 'assistant')

// markdown → HTML(渲染后再用 DOMPurify 消毒,双重保险)
const renderedHtml = computed(() =>
  DOMPurify.sanitize(md.render(props.message.content || '')),
)

// 工具徽标文案:调用过的工具用顿号拼接,如 "加班费计算、个税计算"
const toolText = computed(() =>
  props.message.toolCalls?.length
    ? props.message.toolCalls.join('、')
    : '',
)
</script>

<template>
  <div class="message-row" :class="isAssistant ? 'assistant' : 'user'">
    <!-- 助手头像:朱红小印章(用户消息不显示,靠右对齐) -->
    <div v-if="isAssistant" class="avatar" aria-hidden="true">权</div>

    <div class="message-body">
      <!-- 内容区:助手渲染 markdown,用户消息直接显示纯文本 -->
      <div
        v-if="isAssistant"
        class="bubble markdown-body"
        v-html="renderedHtml"
      />
      <div v-else class="bubble user-bubble">{{ message.content }}</div>

      <!-- 打字机光标:流式生成中,显示在回答末尾 -->
      <span
        v-if="message.streaming"
        class="typing-cursor"
        aria-label="正在生成"
      />

      <!-- 工具调用徽标:朱红描边小章,如"核算凭证 · 加班费计算" -->
      <div v-if="toolText" class="tool-seal">
        <span class="tool-seal-label">核算凭证</span>
        <span class="tool-seal-value">{{ toolText }}</span>
      </div>

      <!-- 法条引注卡:每条来源一张卡,可单独展开看条文原文 -->
      <div
        v-if="isAssistant && message.sources?.length"
        class="sources-block"
      >
        <p class="sources-heading">法条依据({{ message.sources.length }})</p>
        <!-- 每条来源独立开合(el-collapse 每项一个) -->
        <el-collapse class="source-collapse">
          <el-collapse-item
            v-for="(s, i) in message.sources"
            :key="i"
            :name="i"
            class="source-item"
          >
            <!-- 标题行:朱红索引条 + 法名 · 条款号 -->
            <template #title>
              <span class="source-cite">
                <span class="source-bar" aria-hidden="true" />
                <span class="source-law">{{ s.law }}</span>
                <span class="source-article">第{{ s.article }}条</span>
              </span>
            </template>
            <!-- 条文原文:仿宋字体(法律文书惯用) -->
            <div class="source-text">{{ s.text }}</div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 单条消息行:助手靠左,用户靠右 */
.message-row {
  display: flex;
  padding: 14px 24px;
}

/* 用户消息:整体右对齐 */
.message-row.user {
  justify-content: flex-end;
}

/* 助手头像:朱红小印章 */
.avatar {
  width: 34px;
  height: 34px;
  border-radius: 6px;
  background: var(--seal-600);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 700;
  flex-shrink: 0;
  margin-right: 12px;
  box-shadow: 0 0 0 2px var(--seal-soft);
}

/* 消息主体:限制最大宽度,避免撑满整行 */
.message-body {
  max-width: 78%;
}

/* 气泡基础样式 */
.bubble {
  padding: 12px 16px;
  border-radius: 8px;
  line-height: 1.75;
  font-size: 14px;
  word-break: break-word;
}

/* 助手气泡:白卡 + 细边框 */
.assistant .bubble {
  background: var(--card);
  border: 1px solid var(--line);
}

/* 用户气泡:墨蓝实底白字 */
.user-bubble {
  background: var(--ink-900);
  color: #f2f0ea;
}

/* 打字机光标:回答末尾的闪烁竖线 */
.typing-cursor {
  display: inline-block;
  width: 2px;
  height: 16px;
  background: var(--seal-600);
  margin-left: 2px;
  vertical-align: -2px;
  animation: blink 1s steps(1) infinite;
}

/* 光标闪烁动画 */
@keyframes blink {
  50% {
    opacity: 0;
  }
}

/* 工具徽标:朱红描边小章(核算凭证) */
.tool-seal {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  padding: 3px 10px;
  border: 1px solid var(--seal-600);
  border-radius: 4px;
  font-size: 12px;
}

/* 凭证字样:朱红实底白字 */
.tool-seal-label {
  background: var(--seal-600);
  color: #fff;
  padding: 1px 5px;
  border-radius: 2px;
  font-size: 11px;
}

/* 凭证内容:朱红字 */
.tool-seal-value {
  color: var(--seal-600);
}

/* 法条依据区 */
.sources-block {
  margin-top: 12px;
  max-width: 100%;
}

/* 依据区标题:小字 + 上分割线 */
.sources-heading {
  margin: 0 0 6px;
  font-size: 12px;
  color: var(--muted);
  letter-spacing: 0.5px;
}

/* 每条引注卡:覆盖 Element Plus 折叠项默认边框,改为整卡描边 */
.source-collapse {
  --el-collapse-border-color: var(--line);
  --el-collapse-header-height: 40px;
  border-top: 0;
  border-bottom: 0;
}

/* 单条引注卡:卡片式,间隔 */
.source-item {
  margin-bottom: 6px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--card);
}

/* 标题行:法名 + 条款号 */
.source-cite {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

/* 朱红索引条:档案感 */
.source-bar {
  width: 3px;
  height: 14px;
  border-radius: 1.5px;
  background: var(--seal-600);
  flex-shrink: 0;
}

/* 法名:加粗 */
.source-law {
  font-weight: 600;
  color: var(--ink-900);
}

/* 条款号:朱红 */
.source-article {
  color: var(--seal-600);
}

/* 条文原文:仿宋字体(法律文书惯用),灰黑小字 */
.source-text {
  padding: 0 4px 10px;
  font-family: var(--font-law);
  font-size: 13px;
  line-height: 1.9;
  color: #555c66;
  white-space: pre-wrap;
}
</style>

<style>
/* 全局 markdown 排版样式(非 scoped:作用于 v-html 渲染出的子节点) */
.markdown-body h1,
.markdown-body h2,
.markdown-body h3 {
  margin: 0.6em 0 0.4em;
  font-size: 1.1em;
  color: var(--ink-900);
}

/* 段落间距 */
.markdown-body p {
  margin: 0.4em 0;
}

/* 列表缩进 */
.markdown-body ul,
.markdown-body ol {
  padding-left: 1.6em;
  margin: 0.4em 0;
}

/* 行内代码 */
.markdown-body code {
  background: #f0efe9;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
}

/* 表格边框与内边距 */
.markdown-body table {
  border-collapse: collapse;
  margin: 0.6em 0;
}

.markdown-body th,
.markdown-body td {
  border: 1px solid var(--line);
  padding: 6px 12px;
}

/* 引用块:左侧朱红竖线 + 纸色底(呼应引注卡) */
.markdown-body blockquote {
  border-left: 3px solid var(--seal-600);
  margin: 0.6em 0;
  padding: 4px 12px;
  color: var(--muted);
  background: #faf8f4;
}
</style>
