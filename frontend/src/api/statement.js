import http from './http'

// 生成核算单(kind: "severance" 经济补偿 / "overtime" 加班费)
// 参数:城市 + 月薪 + 各类型专属字段(年限/月份/情形 或 加班类型/小时)
export function buildStatement(params) {
  return http.post('/statement', params)
}
