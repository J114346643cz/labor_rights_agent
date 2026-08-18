<script setup>
import { ElMessageBox } from 'element-plus'

// 父组件注入的会话数据与操作事件
defineProps({
  sessions: { type: Array, required: true }, // 会话列表(侧栏展示)
  activeSessionId: { type: String, default: null }, // 当前选中会话 ID(高亮)
})
const emit = defineEmits(['create', 'select', 'delete'])

// 点击删除图标:先弹确认框,确认后才通知父组件删除
async function confirmDelete(session) {
  try {
    await ElMessageBox.confirm(
      `确定删除会话「${session.title}」吗?删除后不可恢复。`,
      '删除会话',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    emit('delete', session.id) // 用户点了"删除"
  } catch {
    /* 用户点了"取消":什么都不做 */
  }
}
</script>

<template>
  <aside class="session-sidebar">
    <!-- 顶部:栏目标题 + 新建对话按钮 -->
    <div class="sidebar-header">
      <span class="sidebar-title">对话记录</span>
      <!-- 新建对话:朱红加号按钮 -->
      <el-button
        class="create-btn"
        type="primary"
        circle
        size="small"
        title="新建对话"
        @click="emit('create')"
      >
        <el-icon><Plus /></el-icon>
      </el-button>
    </div>

    <!-- 会话列表(超出高度滚动) -->
    <div class="session-list">
      <!-- 每个会话一行:点击切换,悬停显示删除按钮,选中带朱红左条 -->
      <div
        v-for="s in sessions"
        :key="s.id"
        class="session-item"
        :class="{ active: s.id === activeSessionId }"
        @click="emit('select', s.id)"
      >
        <!-- 会话标题(超长省略,悬停显示全名) -->
        <span class="session-title" :title="s.title">{{ s.title }}</span>
        <!-- 删除按钮(.stop 阻止冒泡,避免误触切换会话) -->
        <el-icon class="delete-icon" :size="14" @click.stop="confirmDelete(s)">
          <Delete />
        </el-icon>
      </div>
      <!-- 空态:还没有任何会话 -->
      <p v-if="!sessions.length" class="empty-tip">还没有对话记录<br />点击上方 + 开始</p>
    </div>

    <!-- 底部落款:呼应"档案"主题 -->
    <p class="sidebar-footer">劳动权益 · 有据可查</p>
  </aside>
</template>

<style scoped>
/* 侧栏整体:墨蓝深底,固定宽度,撑满高度 */
.session-sidebar {
  width: 260px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--ink-900);
}

/* 顶部标题区 */
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 16px 14px;
}

/* 栏目标题:纸白字,加字距 */
.sidebar-title {
  font-size: 14px;
  font-weight: 600;
  color: #f2f0ea;
  letter-spacing: 2px;
}

/* 新建按钮:朱红实底(覆盖 Element Plus 默认主题色) */
.create-btn {
  --el-button-bg-color: var(--seal-600);
  --el-button-border-color: var(--seal-600);
  --el-button-hover-bg-color: #c74a3d;
  --el-button-hover-border-color: #c74a3d;
}

/* 会话列表滚动区 */
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 10px;
}

/* 单个会话条目 */
.session-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 2px;
  position: relative;
}

/* 悬停:墨蓝浅一档 */
.session-item:hover {
  background: rgba(255, 255, 255, 0.06);
}

/* 当前选中:更亮背景 + 左侧朱红竖条(档案索引感) */
.session-item.active {
  background: rgba(255, 255, 255, 0.12);
}

/* 选中会话的朱红索引条 */
.session-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 2px;
  background: var(--seal-600);
}

/* 会话标题:占满剩余宽度,超长省略 */
.session-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13.5px;
  color: #d8dbe0;
}

/* 选中会话的标题文字更亮 */
.session-item.active .session-title {
  color: #fff;
}

/* 删除图标:默认隐藏,悬停显示 */
.delete-icon {
  color: #9aa3b0;
  visibility: hidden;
  flex-shrink: 0;
}

.session-item:hover .delete-icon {
  visibility: visible;
}

/* 删除图标悬停变朱红 */
.delete-icon:hover {
  color: #e0897f;
}

/* 空态提示 */
.empty-tip {
  margin: 24px 0;
  text-align: center;
  font-size: 12.5px;
  line-height: 1.8;
  color: #6e7a8c;
}

/* 底部落款:弱化小字 */
.sidebar-footer {
  margin: 0;
  padding: 14px 16px;
  font-size: 11px;
  letter-spacing: 1px;
  color: #5b6778;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
</style>
