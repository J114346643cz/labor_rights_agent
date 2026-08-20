<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import { listPolicies, uploadPolicy, deletePolicy } from '../api/policies'

// 政策文档列表
const policies = ref([])
// 是否正在加载列表
const loading = ref(false)
// 上传表单是否展开
const showUpload = ref(false)
// 上传中
const uploading = ref(false)

// 政策类型下拉选项(与后端 POLICY_TYPES 一致)
const POLICY_TYPES = ['最低工资', '高温津贴', '工伤赔偿', '社保基数', '其他']

// 上传表单数据(城市由用户自由输入,后端查不到该城市时核算单会提示)
const form = ref({
  file: null, // 政策文件
  city: '', // 城市(自由输入,如:杭州/广州/长沙)
  policyType: '高温津贴', // 政策类型(默认高温津贴)
  effectiveDate: '', // 生效日期
  source: '', // 来源
})

// 加载政策列表(页面进入与上传/删除后调用)
async function loadPolicies() {
  loading.value = true
  try {
    const { data } = await listPolicies()
    policies.value = data
  } finally {
    loading.value = false
  }
}

// 选择上传文件:校验非空(大小限制由后端兜底)
function handleFileChange(uploadFile) {
  form.value.file = uploadFile.raw
}

// 上传政策:校验必填项后提交
async function handleUpload() {
  // 逐项校验必填
  if (!form.value.file) return ElMessage.warning('请选择政策文件')
  if (!form.value.city) return ElMessage.warning('请选择城市')
  if (!form.value.effectiveDate) return ElMessage.warning('请填写生效日期')
  uploading.value = true
  try {
    const { data } = await uploadPolicy({
      file: form.value.file,
      city: form.value.city,
      policyType: form.value.policyType,
      effectiveDate: form.value.effectiveDate,
      source: form.value.source,
    })
    ElMessage.success(`已入库《${data.doc_name}》(${data.chunks} 段)`)
    // 上传成功后:收起表单、重置、刷新列表
    showUpload.value = false
    form.value = { file: null, city: '', policyType: '高温津贴', effectiveDate: '', source: '' }
    loadPolicies()
  } finally {
    uploading.value = false
  }
}

// 删除政策:确认后提交并刷新
async function handleDelete(doc) {
  try {
    await ElMessageBox.confirm(
      `确定删除《${doc.doc_name}》吗?该城市政策将不可检索。`,
      '删除政策',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    await deletePolicy(doc.doc_id)
    ElMessage.success('已删除')
    loadPolicies()
  } catch {
    /* 用户取消或删除失败:静默 */
  }
}

// 页面进入时加载列表
onMounted(loadPolicies)
</script>

<template>
  <div class="arch-view">
    <!-- 页头 -->
    <h2 class="arch-view-title">政策库</h2>
    <p class="arch-view-desc">各地官方政策档案(最低工资 / 高温津贴 / 工伤赔偿等),可共同维护</p>

    <!-- 上传入口 + 折叠表单 -->
    <div class="arch-card upload-card">
      <!-- 展开/收起上传表单 -->
      <button class="upload-toggle" @click="showUpload = !showUpload">
        <el-icon><Plus /></el-icon>
        上传政策文件
      </button>

      <!-- 上传表单(折叠区) -->
      <div v-if="showUpload" class="upload-form">
        <el-upload
          drag
          :auto-upload="false"
          :limit="1"
          :on-change="handleFileChange"
          :on-remove="() => (form.file = null)"
          class="upload-file"
        >
          <el-icon class="upload-icon"><UploadFilled /></el-icon>
          <div class="upload-text">选择官方政策文件</div>
          <div class="upload-hint">支持 txt / md / pdf / docx,不超过 5MB</div>
        </el-upload>

        <!-- 元数据表单(城市由用户自由输入) -->
        <div class="upload-fields">
          <el-input v-model="form.city" placeholder="城市(如:杭州/广州/长沙)" class="field" />
          <el-select v-model="form.policyType" class="field">
            <el-option v-for="t in POLICY_TYPES" :key="t" :label="t" :value="t" />
          </el-select>
          <el-date-picker
            v-model="form.effectiveDate"
            type="date"
            placeholder="生效日期"
            value-format="YYYY-MM"
            format="YYYY-MM"
            class="field"
          />
          <el-input v-model="form.source" placeholder="来源(如:XX市人社局)" class="field" />
        </div>

        <div class="upload-actions">
          <el-button type="primary" class="seal-btn" :loading="uploading" @click="handleUpload">
            {{ uploading ? '入库中…' : '确认入库' }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- 政策列表 -->
    <div v-loading="loading" class="policy-list">
      <!-- 空态 -->
      <div v-if="!loading && !policies.length" class="empty-tip">
        <p>政策库还是空的</p>
        <p class="empty-sub">点击上方「上传政策文件」,把官方政策收入档案</p>
      </div>

      <!-- 政策卡片:城市 + 类型标签 + 元信息 + 删除 -->
      <div v-for="p in policies" :key="p.doc_id" class="arch-card policy-card">
        <div class="policy-head">
          <span class="policy-city">{{ p.city }}</span>
          <span class="policy-type">{{ p.policy_type }}</span>
          <span class="policy-name" :title="p.doc_name">{{ p.doc_name }}</span>
          <el-button
            class="delete-btn"
            text
            :icon="Delete"
            size="small"
            @click="handleDelete(p)"
          >
            删除
          </el-button>
        </div>
        <div class="policy-meta">
          <span>生效:{{ p.effective_date || '未知' }}</span>
          <span>来源:{{ p.source || '未知' }}</span>
          <span>{{ p.chunks }} 段入库</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 上传卡片 */
.upload-card {
  margin-bottom: 16px;
}

/* 展开/收起按钮:墨蓝文字链接样式 */
.upload-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  border: 0;
  background: transparent;
  color: var(--ink-700);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
}

/* 展开/收起按钮悬停 */
.upload-toggle:hover {
  color: var(--seal-600);
}

/* 上传表单区 */
.upload-form {
  margin-top: 14px;
  border-top: 1px dashed var(--line);
  padding-top: 14px;
}

/* 上传图标 */
.upload-icon {
  font-size: 32px;
  color: var(--seal-600);
  margin-bottom: 6px;
}

/* 上传提示 */
.upload-text {
  font-size: 13.5px;
  color: var(--ink-700);
}

.upload-hint {
  font-size: 12px;
  color: var(--muted);
  margin-top: 2px;
}

/* 元数据表单:网格布局 */
.upload-fields {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-top: 12px;
}

/* 窄屏降为两列 */
@media (max-width: 1100px) {
  .upload-fields {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* 按钮行 */
.upload-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

/* 朱红主按钮 */
.seal-btn {
  --el-button-bg-color: var(--seal-600);
  --el-button-border-color: var(--seal-600);
  --el-button-hover-bg-color: #c74a3d;
  --el-button-hover-border-color: #c74a3d;
}

/* 政策列表 */
.policy-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 政策卡片 */
.policy-card {
  padding: 14px 18px;
}

/* 卡片头行 */
.policy-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 城市名:朱红 */
.policy-city {
  font-weight: 700;
  font-size: 15px;
  color: var(--seal-600);
}

/* 类型标签 */
.policy-type {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 3px;
  background: var(--seal-soft);
  color: var(--seal-600);
  flex-shrink: 0;
}

/* 文件名:省略 */
.policy-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13.5px;
  color: var(--ink-900);
}

/* 删除按钮:灰色,悬停变红 */
.delete-btn {
  color: var(--muted);
  flex-shrink: 0;
}

.delete-btn:hover {
  color: var(--risk-bad);
}

/* 元信息行 */
.policy-meta {
  display: flex;
  gap: 18px;
  margin-top: 8px;
  font-size: 12px;
  color: var(--muted);
}

/* 空态 */
.empty-tip {
  text-align: center;
  padding: 40px 0;
  color: var(--muted);
}

.empty-tip p {
  margin: 4px 0;
}

.empty-sub {
  font-size: 12.5px;
}
</style>
