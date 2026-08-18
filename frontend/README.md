# 打工人权益助手 · 前端

基于 **Vue 3 + Vite + Element Plus** 的聊天前端,通过 **SSE 流式** 消费后端回答(打字机效果)。

## 功能

- 会话管理:新建 / 切换 / 删除会话,历史消息持久化(刷新页面可恢复)
- SSE 流式聊天:回答逐字输出,可中途"停止生成"
- 工具调用徽标:回答过程中调用了哪些计算工具(加班费 / 个税 / 经济补偿金等)
- 法条来源:回答引用的法律条文以折叠面板展示
- Markdown 渲染:助手回答支持加粗、列表、表格等排版(DOMPurify 消毒)

## 快速开始

```bash
# 1. 安装依赖
npm install

# 2. 启动开发服务器(http://localhost:5173,需后端已启动)
npm run dev
```

开发环境通过 Vite 代理把 `/api` 转发到 `http://127.0.0.1:8000`(见 `vite.config.js`),
前后端同源,无需处理 CORS。

## 目录结构

```
src/
├── main.js                  # 入口:挂载 Element Plus(中文语言包)+ 图标
├── App.vue                  # 布局:左侧会话栏 + 右侧聊天区
├── api/
│   ├── http.js              # axios 实例(会话 CRUD 用)
│   ├── sessions.js          # 会话接口封装
│   └── chatStream.js        # SSE 流式解析(fetch + ReadableStream)
├── composables/
│   └── useChat.js           # 聊天状态机(会话 / 消息 / 流式收发)
├── components/
│   ├── SessionSidebar.vue   # 会话列表(新建 / 切换 / 删除)
│   ├── ChatMessages.vue     # 消息列表(自动滚动)
│   ├── MessageItem.vue      # 单条消息(markdown / 工具徽标 / 法条来源)
│   └── ChatInput.vue        # 输入框(Enter 发送,Shift+Enter 换行)
└── styles/main.css          # 全局样式
```

## SSE 事件协议(与后端约定)

| 事件 | data | 说明 |
| --- | --- | --- |
| `session` | `{session_id, rewrite_query}` | 会话信息(首次发送时返回) |
| `tool` | `{name}` | 调用了某工具 |
| `delta` | `{text}` | 回答增量文本 |
| `done` | `{sources, tool_calls}` | 生成结束(法条来源 + 工具列表) |
| `error` | `{message}` | 出错信息 |

## 构建

```bash
npm run build   # 产物输出到 dist/
```
