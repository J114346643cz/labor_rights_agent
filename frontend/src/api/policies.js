import http from './http'

// 获取政策库文档列表(城市 / 类型 / 生效日期 / 来源)
export function listPolicies() {
  return http.get('/policies')
}

// 获取已收录城市列表(来自后端 city_policies.csv,核算单下拉用)
export function listCities() {
  return http.get('/policies/cities')
}

// 上传官方政策文件入库(众包维护公共政策库)
export function uploadPolicy({ file, city, policyType, effectiveDate, source }) {
  // 用 FormData 传 multipart(与后端 UploadFile + Form 参数对应)
  const formData = new FormData()
  formData.append('file', file)
  formData.append('city', city)
  formData.append('policy_type', policyType)
  formData.append('effective_date', effectiveDate)
  formData.append('source', source)
  return http.post('/policies', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000, // 入库含文本解析 + 向量化,给足 2 分钟
  })
}

// 删除政策文档(按 doc_id)
export function deletePolicy(docId) {
  return http.delete(`/policies/${docId}`)
}
