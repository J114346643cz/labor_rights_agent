<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { buildStatement } from '../api/statement'
import { listCities } from '../api/policies'

// 核算类型:severance=经济补偿,overtime=加班费
const kind = ref('overtime')

// 已收录城市(来自后端 city_policies.csv,动态拉取;只有这些城市能核算)
const cities = ref([])
// 是否还在加载城市列表
const citiesLoading = ref(false)

// 经济补偿表单(severance)——字段名与后端 StatementRequest 一致(snake_case)
const severanceForm = ref({
  city: '',
  monthly_salary: null,
  years: null,
  months: 0,
  scenario: 'negotiated',
})

// 加班费表单(overtime)
const overtimeForm = ref({
  city: '',
  monthly_salary: null,
  overtime_type: 'weekday',
  hours: null,
})

// 情形选项(与后端 severance.py 一致):协商解除 / 违法解除(N+1) / 违法解除(2N)
const SCENARIOS = [
  { value: 'negotiated', label: '协商解除' },
  { value: 'N+1', label: '违法解除(N+1)' },
  { value: 'illegal', label: '违法解除(2N)' },
]

// 加班类型选项(与后端 overtime.py 的倍数对应)
const OVERTIME_TYPES = [
  { value: 'weekday', label: '工作日延时(1.5倍)' },
  { value: 'weekend', label: '休息日(2倍)' },
  { value: 'holiday', label: '法定节假日(3倍)' },
]

// 核算单结果(后端返回)
const statement = ref(null)
// 是否正在生成
const calculating = ref(false)

// 当前表单:按类型取对应表单对象
const form = computed(() => (kind.value === 'severance' ? severanceForm.value : overtimeForm.value))

// 页面进入时拉取已收录城市(核算单城市下拉用)
onMounted(async () => {
  citiesLoading.value = true
  try {
    const { data } = await listCities()
    cities.value = data.cities || []
    // 有收录城市时默认选第一个,方便用户
    if (cities.value.length) {
      overtimeForm.value.city = cities.value[0]
      severanceForm.value.city = cities.value[0]
    }
  } finally {
    citiesLoading.value = false
  }
})

// 生成核算单
async function handleCalculate() {
  // 基础校验:城市已选 + 月薪必填为正数
  if (!form.value.city) return ElMessage.warning('请选择城市')
  if (!form.value.monthly_salary || form.value.monthly_salary <= 0) {
    ElMessage.warning('请填写月薪')
    return
  }
  // 类型专属校验
  if (kind.value === 'severance') {
    if (form.value.years === null || form.value.years < 0) return ElMessage.warning('请填写工作年限')
    if (form.value.months < 0 || form.value.months > 11) return ElMessage.warning('不满一年的月份需在 0-11 之间')
  } else {
    if (!form.value.hours || form.value.hours <= 0) return ElMessage.warning('请填写加班小时数')
  }

  calculating.value = true
  statement.value = null
  try {
    // 按类型组装请求参数
    const params = kind.value === 'severance'
      ? { kind: 'severance', ...severanceForm.value }
      : { kind: 'overtime', ...overtimeForm.value }
    const { data } = await buildStatement(params)
    statement.value = data
    // 后端返回 error 字段(如城市无数据):直接提示
    if (data.error) ElMessage.warning(data.error)
  } catch {
    // 错误提示由 http.js 拦截器统一弹出
  } finally {
    calculating.value = false
  }
}

// 金额格式化:千分位 + 两位小数;非数字(如字符串说明)返回 '--'
const fmtMoney = (v) => {
  const n = Number(v)
  return Number.isFinite(n)
    ? n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : '--'
}

// 应得金额:加班费取 result.amount,经济补偿取 result.amount(两个工具都返回 amount)
const resultAmount = computed(() => statement.value?.result?.amount ?? 0)

// 计算明细:只显示数字字段(n_months/base_salary/amount 等),跳过字符串说明
const numericRows = computed(() => {
  const result = statement.value?.result
  if (!result) return []
  return Object.entries(result).filter(([, v]) => typeof v === 'number')
})

// 计算说明:detail/basis/note 字符串说明拼接展示
const textRows = computed(() => {
  const result = statement.value?.result
  if (!result) return []
  return Object.entries(result).filter(([, v]) => typeof v === 'string' && v)
})
</script>

<template>
  <div class="arch-view">
    <!-- 页头 -->
    <h2 class="arch-view-title">核算单</h2>
    <p class="arch-view-desc">输入你的情况,生成带城市政策依据的金额核算单</p>

    <div class="statement-layout">
      <!-- 左侧:输入表单 -->
      <div class="arch-card form-card">
        <!-- 类型切换 -->
        <el-radio-group v-model="kind" class="kind-switch">
          <el-radio-button value="overtime">加班费</el-radio-button>
          <el-radio-button value="severance">经济补偿</el-radio-button>
        </el-radio-group>

        <!-- 城市提示:只有 CSV 收录的城市能核算 -->
        <p v-if="cities.length" class="city-tip">
          支持城市:{{ cities.map((c) => c + '市').join('、') }}
        </p>
        <p v-else-if="!citiesLoading" class="city-tip empty">
          暂未收录城市政策数据,请先在后端上传 city_policies.csv
        </p>

        <!-- 加班费表单 -->
        <div v-if="kind === 'overtime'" class="fields">
          <div class="field-row">
            <label class="field-label">城市</label>
            <el-select v-model="overtimeForm.city" :loading="citiesLoading" placeholder="选择城市">
              <el-option v-for="c in cities" :key="c" :label="c + '市'" :value="c" />
            </el-select>
          </div>
          <div class="field-row">
            <label class="field-label">月薪(元)</label>
            <el-input-number v-model="overtimeForm.monthly_salary" :min="0" :precision="2" controls-position="right" />
          </div>
          <div class="field-row">
            <label class="field-label">加班类型</label>
            <el-select v-model="overtimeForm.overtime_type">
              <el-option v-for="t in OVERTIME_TYPES" :key="t.value" :label="t.label" :value="t.value" />
            </el-select>
          </div>
          <div class="field-row">
            <label class="field-label">加班小时</label>
            <el-input-number v-model="overtimeForm.hours" :min="0" :precision="1" controls-position="right" />
          </div>
        </div>

        <!-- 经济补偿表单 -->
        <div v-else class="fields">
          <div class="field-row">
            <label class="field-label">城市</label>
            <el-select v-model="severanceForm.city" :loading="citiesLoading" placeholder="选择城市">
              <el-option v-for="c in cities" :key="c" :label="c + '市'" :value="c" />
            </el-select>
          </div>
          <div class="field-row">
            <label class="field-label">月薪(元)</label>
            <el-input-number v-model="severanceForm.monthly_salary" :min="0" :precision="2" controls-position="right" />
          </div>
          <div class="field-row">
            <label class="field-label">工作年限</label>
            <el-input-number v-model="severanceForm.years" :min="0" :precision="0" controls-position="right" />
          </div>
          <div class="field-row">
            <label class="field-label">不满一年月份</label>
            <el-input-number v-model="severanceForm.months" :min="0" :max="11" :precision="0" controls-position="right" />
          </div>
          <div class="field-row">
            <label class="field-label">解除情形</label>
            <el-select v-model="severanceForm.scenario">
              <el-option v-for="s in SCENARIOS" :key="s.value" :label="s.label" :value="s.value" />
            </el-select>
          </div>
        </div>

        <!-- 生成按钮 -->
        <div class="form-actions">
          <el-button type="primary" class="seal-btn" :loading="calculating" @click="handleCalculate">
            {{ calculating ? '核算中…' : '生成核算单' }}
          </el-button>
        </div>
      </div>

      <!-- 右侧:核算单结果 -->
      <div class="arch-card statement-card">
        <!-- 未生成时的引导 -->
        <div v-if="!statement" class="statement-empty">
          <p class="empty-main">核算单将在这里生成</p>
          <p class="empty-sub">填写左侧信息,点击「生成核算单」</p>
        </div>

        <!-- 后端返回错误(如城市无数据) -->
        <div v-else-if="statement.error" class="statement-error">
          <p class="error-text">{{ statement.error }}</p>
        </div>

        <!-- 核算单正文 -->
        <template v-else>
          <!-- 抬头:朱红印章式标题 -->
          <div class="statement-head">
            <span class="statement-title">{{ statement.type }}</span>
            <span class="statement-city">{{ statement.city }}</span>
          </div>

          <!-- 结果大数字(金额) -->
          <div class="amount-block">
            <span class="amount-label">{{ statement.type === '加班费核算单' ? '应得加班费' : '应得经济补偿' }}</span>
            <span class="amount-value">{{ fmtMoney(resultAmount) }}<span class="amount-unit">元</span></span>
          </div>

          <!-- 计算明细:数字字段 -->
          <div v-if="numericRows.length" class="detail-block">
            <h4 class="detail-title">计算明细</h4>
            <div class="detail-row" v-for="([k, v], i) in numericRows" :key="i">
              <span class="detail-key">{{ k }}</span>
              <span class="detail-val">{{ fmtMoney(v) }}</span>
            </div>
          </div>

          <!-- 计算说明:detail/basis/note 文字 -->
          <div v-if="textRows.length" class="detail-block">
            <h4 class="detail-title">计算说明</h4>
            <p v-for="([k, v], i) in textRows" :key="i" class="text-note">
              <span class="note-key">{{ k }}</span>{{ v }}
            </p>
          </div>

          <!-- 城市政策依据 -->
          <div class="policy-block">
            <h4 class="detail-title">政策依据({{ statement.city }})</h4>
            <div class="detail-row"><span class="detail-key">最低工资</span><span class="detail-val">{{ fmtMoney(statement.policy?.min_wage) }} 元</span></div>
            <div class="detail-row"><span class="detail-key">社平工资 3 倍</span><span class="detail-val">{{ fmtMoney(statement.input?.avg_salary_3x) }} 元</span></div>
            <div class="detail-row"><span class="detail-key">数据截至</span><span class="detail-val">{{ statement.policy?.data_as_of || '--' }}</span></div>
            <div class="detail-row"><span class="detail-key">来源</span><span class="detail-val">{{ statement.policy?.source || '--' }}</span></div>
          </div>

          <!-- 免责声明 -->
          <p class="disclaimer">{{ statement.disclaimer }}</p>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 左右布局 */
.statement-layout {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 16px;
  align-items: start;
}

/* 窄屏堆叠 */
@media (max-width: 1000px) {
  .statement-layout {
    grid-template-columns: 1fr;
  }
}

/* 类型切换 */
.kind-switch {
  margin-bottom: 10px;
}

/* 城市提示:收录城市清单 */
.city-tip {
  margin: 0 0 14px;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.8;
}

/* 未收录时的提示:琥珀色 */
.city-tip.empty {
  color: var(--risk-warn);
}

/* 表单项 */
.fields {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* 单行:标签 + 控件 */
.field-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 标签:固定宽度右对齐 */
.field-label {
  width: 96px;
  text-align: right;
  font-size: 13px;
  color: var(--ink-700);
  flex-shrink: 0;
}

/* 控件占满剩余 */
.field-row :deep(.el-select),
.field-row :deep(.el-input-number) {
  flex: 1;
}

/* 生成按钮行 */
.form-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 18px;
}

/* 朱红主按钮 */
.seal-btn {
  --el-button-bg-color: var(--seal-600);
  --el-button-border-color: var(--seal-600);
  --el-button-hover-bg-color: #c74a3d;
  --el-button-hover-border-color: #c74a3d;
}

/* 核算单卡 */
.statement-card {
  min-height: 360px;
  display: flex;
  flex-direction: column;
}

/* 未生成引导 */
.statement-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--muted);
}

.statement-empty p {
  margin: 4px 0;
}

.empty-sub {
  font-size: 12.5px;
}

/* 错误提示 */
.statement-error {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.error-text {
  color: var(--risk-bad);
  font-size: 14px;
  border: 1px solid var(--risk-bad);
  padding: 10px 18px;
  border-radius: 6px;
  background: #faf3f2;
}

/* 抬头 */
.statement-head {
  display: flex;
  align-items: center;
  gap: 10px;
  border-bottom: 2px solid var(--seal-600);
  padding-bottom: 10px;
}

/* 抬头标题:朱红印章感 */
.statement-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--seal-600);
  letter-spacing: 2px;
}

/* 城市名 */
.statement-city {
  font-size: 12px;
  color: var(--muted);
  border: 1px solid var(--line);
  padding: 1px 8px;
  border-radius: 3px;
}

/* 金额大数字 */
.amount-block {
  text-align: center;
  padding: 22px 0 18px;
  border-bottom: 1px dashed var(--line);
}

/* 金额标签 */
.amount-label {
  display: block;
  font-size: 13px;
  color: var(--muted);
  margin-bottom: 6px;
}

/* 金额数值:朱红大字 */
.amount-value {
  font-size: 34px;
  font-weight: 700;
  color: var(--seal-600);
  font-variant-numeric: tabular-nums;
}

/* 金额单位 */
.amount-unit {
  font-size: 14px;
  margin-left: 4px;
}

/* 明细区 */
.detail-block,
.policy-block {
  margin-top: 14px;
}

/* 明细标题 */
.detail-title {
  margin: 0 0 8px;
  font-size: 12px;
  color: var(--muted);
  letter-spacing: 0.5px;
}

/* 明细行 */
.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 3px 0;
  font-size: 13px;
}

/* 明细键:灰 */
.detail-key {
  color: var(--muted);
}

/* 明细值:数字等宽 */
.detail-val {
  color: var(--text);
  font-variant-numeric: tabular-nums;
}

/* 文字说明:detail/basis/note */
.text-note {
  margin: 4px 0;
  font-size: 12.5px;
  color: #555c66;
  line-height: 1.7;
}

/* 说明键名:灰 */
.note-key {
  color: var(--muted);
  margin-right: 6px;
}

/* 免责声明 */
.disclaimer {
  margin: auto 0 0;
  padding-top: 14px;
  font-size: 11.5px;
  color: var(--muted);
  line-height: 1.7;
  text-align: center;
}
</style>
