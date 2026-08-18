import axios from 'axios'
import { ElMessage } from 'element-plus'

// axios 实例:统一 baseURL(开发环境由 Vite 代理到 http://127.0.0.1:8000)
// 注意:SSE 流式请求不走 axios(axios 不支持流式解析),走 api/chatStream.js 的 fetch
const http = axios.create({
  baseURL: '/api/agent', // 后端路由前缀(与 FastAPI router prefix 一致)
  timeout: 15000, // 普通接口 15 秒超时
})

// 响应拦截器:非 2xx 时统一弹出后端返回的错误信息(detail 字段)
http.interceptors.response.use(
  // 成功响应:原样透传给调用方
  (response) => response,
  // 失败响应:提取后端 detail 提示用户,再继续抛出给调用方处理
  (error) => {
    const detail = error.response?.data?.detail
    ElMessage.error(detail || '网络错误,请稍后重试')
    return Promise.reject(error)
  },
)

export default http
