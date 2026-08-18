# 打工人权益助手

一个基于 **RAG + Agent 工具调用** 的劳动权益问答助手:能计算加班费、个税、经济补偿金,并结合法律法规回答劳动法相关问题,回答附法条引用来源。

## 技术栈

| 端 | 技术 |
| --- | --- |
| 后端 | Python 3.13 · FastAPI · LangGraph · ChromaDB(fastembed BGE 中文向量) · DeepSeek API · SQLite(SQLModel) |
| 前端 | Vue 3 · Vite · Element Plus · Axios · SSE 流式(fetch + ReadableStream) |

## 目录结构

```
├── backend/                # 后端服务(项目根,直接在此启动)
│   ├── .env                # 密钥配置(已 gitignore,需自行创建)
│   ├── .venv/              # Python 虚拟环境(uv 创建)
│   ├── main.py             # FastAPI 入口(端口 8000)
│   ├── app/
│   │   ├── agent/          # Agent 循环(手写 ReAct / LangGraph / 流式)
│   │   ├── api/            # 聊天与会话接口
│   │   ├── core/           # LLM 调用、RAG 检索、记忆、工具
│   │   ├── schemas/        # Pydantic/SQLModel 模型
│   │   └── utils/          # 配置加载、提示词加载
│   ├── scripts/            # 知识库入库 / 评估 / 测试脚本
│   └── data/               # SQLite 库、法条文档、向量库、embedding 缓存
└── frontend/               # 前端应用(Vue 3 + Element Plus)
    └── src/
        ├── api/            # 会话 CRUD + SSE 流式解析
        ├── composables/    # useChat 聊天状态机
        └── components/     # 会话栏 / 消息列表 / 输入框等
```

## 快速开始

### 1. 后端(端口 8000)

```bash
# 首次:创建 .env 并填入 DeepSeek API Key(参考 backend/.env.example)
#   DEEPSEEK_API_KEY=sk-xxx
#   DEEPSEEK_BASE_URL=https://api.deepseek.com
#   DEEPSEEK_MODEL=deepseek-chat
cd backend
uv sync                       # 安装依赖（首次）
copy .env.example .env        # 填 DEEPSEEK_API_KEY
uv run python scripts/ingest_kb.py --force   # 法条入库（首次下载 BGE 模型 ~100MB）
uv run uvicorn main:app --reload        # 启动 http://127.0.0.1:8000
```

> 首次提问会自动下载 embedding 模型到 `backend/data/embedding_cache/`(D 盘,约 100MB),并构建 Chroma 向量库,请耐心等待。

### 2. 前端(端口 5173)

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 http://localhost:5173 。开发环境由 Vite 把 `/api` 代理到 `http://127.0.0.1:8000`,前后端同源,无需处理 CORS。



## 3.评估

```bash
cd backend
uv run python scripts/run_eval.py --only-local   # 计算题（离线）
uv run python scripts/run_eval.py                 # 全部（需服务运行）
```

> 存放在backend/data/eval_report.md



## 后端接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/agent/chat` | 非流式聊天(一次返回完整回答) |
| POST | `/api/agent/chat/stream` | **SSE 流式聊天**(打字机效果,前端主用) |
| POST | `/api/agent/sessions` | 新建会话 |
| GET | `/api/agent/sessions` | 会话列表(创建时间倒序) |
| GET | `/api/agent/sessions/{id}/messages` | 某会话的历史消息 |
| DELETE | `/api/agent/sessions/{id}` | 删除会话(含历史消息) |

## SSE 事件协议(`/chat/stream`)

| 事件 | data | 说明 |
| --- | --- | --- |
| `session` | `{session_id, rewrite_query}` | 会话信息(首次发送时返回新会话 ID) |
| `tool` | `{name}` | 调用了某工具(加班费 / 个税 / 赔偿金等) |
| `delta` | `{text}` | 回答增量文本(逐字) |
| `done` | `{sources, tool_calls}` | 生成结束:法条引用 + 工具名列表 |
| `error` | `{message}` | 出错信息 |

每个事件两行(`event: xxx` + `data: JSON`),空行分隔;前端用 `fetch` + `ReadableStream` 解析(`EventSource` 不支持 POST body,故不用)。

## 已支持的计算工具

- 加班费(工作日 / 休息日 / 法定节假日,月薪 ÷ 21.75 ÷ 8 × 倍数)
- 个税(累计预扣法)
- 经济补偿金(N 倍月薪,含月薪封顶规则)
- 年休假天数计算



# 免责声明

本项目回答仅供参考，不构成法律意见；涉及具体权益纠纷请咨询专业律师。

