<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { DocumentAdd, Download, ChatDotRound } from '@element-plus/icons-vue'
import { checkContractText, checkContractFile, downloadReportDocx } from '../api/contract'

// 当前会话 ID(父组件传入):体检时带上,报告会写入会话上下文,方便后续聊天追问
// 注意:必须接住 props 变量,否则 handleCheck 里 props.sessionId 会抛 ReferenceError
const props = defineProps({
  sessionId: { type: String, default: null },
})
// 事件:ask-chat=去聊天继续提问,把报告 JSON 带给父组件(绑定到体检专用会话)
const emit = defineEmits(['ask-chat'])

// 输入方式切换:true=粘贴文本,false=上传文件
const mode = ref('text')
// 粘贴的合同文本
const textInput = ref('')
// 选中的合同文件
const file = ref(null)
// 是否正在体检(loading)
const checking = ref(false)
// 体检报告(后端返回的完整报告 JSON)
const report = ref(null)
// 文件名(报告抬头用)
const fileName = ref('')

// 合同文件类型白名单(与后端 parser 支持的格式一致:Word/PDF/文本)
const ACCEPT_EXTS = ['.txt', '.md', '.pdf', '.docx']
// 支持格式提示文案(醒目展示)
const ACCEPT_TEXT = 'Word(.docx) / PDF / txt / md'

// 选择文件:校验类型与大小(后端限制 5MB)
function handleFileChange(uploadFile) {
  const f = uploadFile.raw
  const ext = f.name.slice(f.name.lastIndexOf('.')).toLowerCase()
  // .doc 老格式:单独提示(后端解析不了,需另存为 .docx)
  if (ext === '.doc') {
    ElMessage.error('不支持旧版 .doc 格式,请在 Word 中「另存为」.docx 后上传')
    return false
  }
  if (!ACCEPT_EXTS.includes(ext)) {
    ElMessage.error(`仅支持 ${ACCEPT_TEXT} 格式`)
    return false
  }
  if (f.size > 5 * 1024 * 1024) {
    ElMessage.error('文件超过 5MB 限制')
    return false
  }
  file.value = f
  return true
}

// 开始体检:文本或文件二选一提交
async function handleCheck() {
  // 文本方式:校验非空
  if (mode.value === 'text' && !textInput.value.trim()) {
    ElMessage.warning('请先粘贴合同文本')
    return
  }
  // 文件方式:校验已选文件
  if (mode.value === 'file' && !file.value) {
    ElMessage.warning('请先选择合同文件')
    return
  }

  checking.value = true
  report.value = null // 清掉上一次报告
  try {
    // 按输入方式调用对应接口(带上当前会话 ID:报告摘要写入会话,后续可追问)
    const { data } = mode.value === 'text'
      ? await checkContractText(textInput.value, props.sessionId)
      : await checkContractFile(file.value, props.sessionId)
    fileName.value = data.file_name || '合同'
    report.value = data
  } catch {
    // 错误提示由 http.js 响应拦截器统一弹出
  } finally {
    checking.value = false
  }
}

// 下载 Word 版报告:后端渲染 docx → Blob 触发浏览器下载
async function handleDownload() {
  try {
    const { data } = await downloadReportDocx(report.value)
    // 生成 Blob URL 并触发 <a> 下载(文件名用合同文件名)
    const url = URL.createObjectURL(data)
    const a = document.createElement('a')
    a.href = url
    a.download = `${report.value.file_name || '合同体检报告'}.docx`
    a.click()
    URL.revokeObjectURL(url) // 释放 Blob URL
  } catch {
    // 下载失败:提示(拦截器对 blob 错误无法提取 detail,这里补一句)
    ElMessage.error('报告下载失败,请重试')
  }
}

// 去聊天继续提问:把报告交给父组件(新建体检专用会话并绑定报告)
function handleAskChat() {
  emit('ask-chat', report.value)
}

// 分级色:verdict → 色值(体检结论语义色)
const verdictColor = (v) => ({
  违法: 'var(--risk-bad)',
  模糊: 'var(--risk-warn)',
  合法: 'var(--risk-ok)',
  未约定: 'var(--risk-na)',
}[v] || 'var(--risk-na)')
</script>

<template>
  <div class="arch-view">
    <!-- 页头 -->
    <h2 class="arch-view-title">合同体检</h2>
    <p class="arch-view-desc">粘贴劳动合同文本或上传文件,逐条检查条款合规性,生成风险分级报告</p>

    <!-- 输入区:两种方式二选一 -->
    <div class="arch-card">
      <!-- 方式切换:粘贴文本 / 上传文件 -->
      <el-radio-group v-model="mode" class="mode-switch">
        <el-radio-button value="text">粘贴文本</el-radio-button>
        <el-radio-button value="file">上传文件</el-radio-button>
      </el-radio-group>

      <!-- 粘贴文本方式 -->
      <el-input
        v-if="mode === 'text'"
        v-model="textInput"
        type="textarea"
        :rows="8"
        resize="none"
        placeholder="把劳动合同文本粘贴到这里,例如:甲方...乙方...试用期 6 个月...工资按月支付..."
        class="contract-input"
      />

      <!-- 上传文件方式:拖拽上传 -->
      <el-upload
        v-else
        drag
        :auto-upload="false"
        :limit="1"
        accept=".txt,.md,.pdf,.docx"
        :on-change="handleFileChange"
        :on-remove="() => (file = null)"
        class="contract-upload"
      >
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <div class="upload-text">拖拽合同文件到这里,或点击选择</div>
        <div class="upload-hint">支持 {{ ACCEPT_TEXT }},不超过 5MB</div>
      </el-upload>

      <!-- 开始体检按钮 -->
      <div class="check-actions">
        <el-button
          type="primary"
          class="seal-btn"
          :loading="checking"
          :icon="DocumentAdd"
          @click="handleCheck"
        >
          {{ checking ? '体检中…' : '开始体检' }}
        </el-button>
      </div>
    </div>

    <!-- 报告区:体检完成后展示 -->
    <div v-if="report" class="report-area">
      <!-- 报告操作栏:固定在报告顶部(报告很长,按钮放底部看不到) -->
      <div class="report-toolbar">
        <span class="toolbar-hint">报告已生成,可下载或继续追问</span>
        <div class="toolbar-actions">
          <el-button size="small" :icon="Download" @click="handleDownload">下载 Word 报告</el-button>
          <el-button size="small" type="primary" class="seal-btn" :icon="ChatDotRound" @click="handleAskChat">
            去聊天继续提问
          </el-button>
        </div>
      </div>

      <!-- 体检结论印章卡:四个分级数字 -->
      <div class="arch-card summary-card">
        <h3 class="arch-card-title">体检结论 · {{ report.file_name }}</h3>
        <div class="summary-grid">
          <div class="summary-item" style="--c: var(--risk-bad)">
            <span class="summary-num">{{ report.summary.violations }}</span>
            <span class="summary-label">违法条款</span>
          </div>
          <div class="summary-item" style="--c: var(--risk-warn)">
            <span class="summary-num">{{ report.summary.warnings }}</span>
            <span class="summary-label">模糊条款</span>
          </div>
          <div class="summary-item" style="--c: var(--risk-ok)">
            <span class="summary-num">{{ report.summary.ok }}</span>
            <span class="summary-label">合规条款</span>
          </div>
          <div class="summary-item" style="--c: var(--risk-na)">
            <span class="summary-num">{{ report.summary.not_specified }}</span>
            <span class="summary-label">未约定</span>
          </div>
        </div>
      </div>

      <!-- 逐条检查结果 -->
      <div class="arch-card findings-card">
        <h3 class="arch-card-title">条款明细(共 {{ report.summary.total }} 项)</h3>
        <!-- 每条发现:条款名 + 分级色标 + 原文 + 依据 + 风险 -->
        <div
          v-for="(f, i) in report.findings"
          :key="i"
          class="finding-item"
        >
          <div class="finding-head">
            <span class="finding-bar" :style="{ background: verdictColor(f.verdict) }" />
            <span class="finding-field">{{ f.field }}</span>
            <span class="finding-verdict" :style="{ color: verdictColor(f.verdict) }">
              {{ f.verdict }}
            </span>
          </div>
          <!-- 合同原文摘录 -->
          <p v-if="f.text" class="finding-text">{{ f.text }}</p>
          <!-- 检查依据(法条/规则) -->
          <p v-if="f.basis" class="finding-basis">依据:{{ f.basis }}</p>
          <!-- 风险说明 -->
          <p v-if="f.reason" class="finding-reason">{{ f.reason }}</p>
        </div>
      </div>

      <!-- 处置建议:每项按 问题/路径/证据/提醒 分字段展示 -->
      <div v-if="report.remedies" class="arch-card remedies-card">
        <h3 class="arch-card-title">处置建议</h3>
        <!-- 每条维权指引 -->
        <div v-for="(r, i) in report.remedies.remedies" :key="i" class="remedy-item">
          <!-- 问题简述 -->
          <p class="remedy-issue">{{ r.issue }}</p>
          <!-- 维权路径 -->
          <p class="remedy-path">{{ r.path }}</p>
          <!-- 证据清单 -->
          <p v-if="r.evidence?.length" class="remedy-evidence">
            证据准备:{{ r.evidence.join('、') }}
          </p>
          <!-- 特别提醒 -->
          <p v-if="r.note" class="remedy-note">{{ r.note }}</p>
        </div>
        <!-- 复杂案件建议 -->
        <p v-if="report.remedies.complex_advice" class="remedy-advice">
          {{ report.remedies.complex_advice }}
        </p>
      </div>

      <!-- 免责声明 -->
      <p class="disclaimer">{{ report.disclaimer }}</p>
    </div>
  </div>
</template>

<style scoped>
/* 输入方式切换 */
.mode-switch {
  margin-bottom: 14px;
}

/* 粘贴文本输入框 */
.contract-input {
  margin-bottom: 14px;
}

/* 上传区 */
.contract-upload {
  margin-bottom: 14px;
  width: 100%;
}

/* 上传图标 */
.upload-icon {
  font-size: 40px;
  color: var(--seal-600);
  margin-bottom: 8px;
}

/* 上传提示主文字 */
.upload-text {
  font-size: 14px;
  color: var(--ink-700);
}

/* 上传提示小字:格式醒目 */
.upload-hint {
  font-size: 12.5px;
  color: var(--seal-600);
  margin-top: 4px;
}

/* 按钮行 */
.check-actions {
  display: flex;
  justify-content: flex-end;
}

/* 朱红主按钮 */
.seal-btn {
  --el-button-bg-color: var(--seal-600);
  --el-button-border-color: var(--seal-600);
  --el-button-hover-bg-color: #c74a3d;
  --el-button-hover-border-color: #c74a3d;
}

/* 报告区 */
.report-area {
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* 报告操作栏:顶部固定(报告很长,按钮不随内容滚走) */
.report-toolbar {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 16px;
  background: var(--ink-900);
  border-radius: 8px;
}

/* 工具栏提示文字 */
.toolbar-hint {
  font-size: 13px;
  color: #f2f0ea;
}

/* 工具栏按钮组 */
.toolbar-actions {
  display: flex;
  gap: 8px;
}

/* 工具栏下载按钮:墨蓝底上的纸色按钮 */
.report-toolbar :deep(.el-button:not(.seal-btn)) {
  --el-button-bg-color: transparent;
  --el-button-border-color: #5b6778;
  --el-button-text-color: #f2f0ea;
  --el-button-hover-bg-color: rgba(255, 255, 255, 0.1);
  --el-button-hover-border-color: #f2f0ea;
  --el-button-hover-text-color: #fff;
}

/* 结论统计:四宫格 */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

/* 单个统计格:顶部色条 + 大数字 + 标签 */
.summary-item {
  border-top: 3px solid var(--c);
  padding: 10px 0 6px;
  text-align: center;
  background: #faf9f6;
  border-radius: 0 0 6px 6px;
}

/* 统计数字 */
.summary-num {
  display: block;
  font-size: 28px;
  font-weight: 700;
  color: var(--c);
  line-height: 1.2;
}

/* 统计标签 */
.summary-label {
  font-size: 12px;
  color: var(--muted);
}

/* 单条发现 */
.finding-item {
  padding: 10px 0;
  border-bottom: 1px dashed var(--line);
}

/* 最后一条去掉分割线 */
.finding-item:last-child {
  border-bottom: 0;
}

/* 发现标题行 */
.finding-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 分级色条 */
.finding-bar {
  width: 3px;
  height: 14px;
  border-radius: 1.5px;
  flex-shrink: 0;
}

/* 条款名 */
.finding-field {
  font-weight: 600;
  font-size: 14px;
  color: var(--ink-900);
}

/* 分级结论 */
.finding-verdict {
  font-size: 12px;
  font-weight: 600;
  border: 1px solid currentColor;
  padding: 1px 8px;
  border-radius: 3px;
}

/* 合同原文摘录:仿宋 */
.finding-text {
  margin: 8px 0 4px;
  font-family: var(--font-law);
  font-size: 13px;
  color: #555c66;
  line-height: 1.8;
}

/* 检查依据 */
.finding-basis {
  margin: 4px 0;
  font-size: 12px;
  color: var(--risk-ok);
}

/* 风险说明 */
.finding-reason {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--risk-bad);
}

/* 单条处置建议 */
.remedy-item {
  padding: 12px 0;
  border-bottom: 1px dashed var(--line);
}

/* 最后一条去掉分割线 */
.remedy-item:last-of-type {
  border-bottom: 0;
}

/* 问题简述:加粗 */
.remedy-issue {
  margin: 0 0 6px;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--ink-900);
}

/* 维权路径 */
.remedy-path {
  margin: 0 0 6px;
  font-size: 13px;
  color: var(--text);
  line-height: 1.8;
}

/* 证据清单 */
.remedy-evidence {
  margin: 0 0 6px;
  font-size: 12.5px;
  color: var(--risk-ok);
  line-height: 1.7;
}

/* 特别提醒 */
.remedy-note {
  margin: 0;
  font-size: 12.5px;
  color: var(--risk-warn);
  line-height: 1.7;
}

/* 复杂案件建议 */
.remedy-advice {
  margin: 10px 0 0;
  font-size: 13px;
  color: var(--muted);
  background: #faf9f6;
  padding: 10px 14px;
  border-radius: 6px;
  border-left: 3px solid var(--seal-600);
}

/* 免责声明 */
.disclaimer {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
  text-align: center;
  line-height: 1.7;
}
</style>
