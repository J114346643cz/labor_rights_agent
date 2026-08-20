# 劳动智法助手 · 前端

基于 **Vue 3 + Vite + Element Plus** 的聊天前端,通过 **SSE 流式** 消费后端回答(打字机效果)。

## 功能

四个功能台(左侧导航切换,聊天状态切换视图不丢失):

- **聊天**:SSE 流式打字机回答、工具调用徽标、法条来源逐条展开、会话管理(新建/切换/删除,历史持久化)
- **合同体检**:上传文件或粘贴合同文本 → 风险分级报告(违法/模糊/合规/未约定统计 + 逐条检查 + 处置建议)
- **政策库**:各地政策档案(最低工资/高温津贴/工伤赔偿等)浏览、上传维护、删除
- **核算单**:加班费 / 经济补偿核算表单 → 带城市政策依据的核算单(结果大数字 + 明细 + 免责声明)

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
├── App.vue                  # 布局:左侧功能导航 + 右侧视图切换
├── api/
│   ├── http.js              # axios 实例(普通接口用)
│   ├── sessions.js          # 会话接口封装
│   ├── chatStream.js        # SSE 流式解析(fetch + ReadableStream)
│   ├── contract.js          # 合同体检接口
│   ├── policies.js          # 政策库接口
│   └── statement.js         # 核算单接口
├── composables/
│   └── useChat.js           # 聊天状态机(会话 / 消息 / 流式收发)
├── components/
│   ├── SessionSidebar.vue   # 功能导航 + 会话列表(新建 / 切换 / 删除)
│   ├── ChatMessages.vue     # 消息列表(自动滚动)
│   ├── MessageItem.vue      # 单条消息(markdown / 工具徽标 / 法条引注)
│   └── ChatInput.vue        # 输入框(Enter 发送,Shift+Enter 换行)
├── views/
│   ├── ContractCheck.vue    # 合同体检(上传/粘贴 → 风险报告)
│   ├── PolicyLibrary.vue    # 政策库(列表 / 上传 / 删除)
│   └── StatementView.vue    # 核算单(表单 → 核算单)
└── styles/main.css          # 全局样式 + 设计令牌
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
