import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import './styles/main.css'

// 创建 Vue 应用实例
const app = createApp(App)

// 注册全部 Element Plus 图标组件(模板里可直接 <el-icon><Delete /></el-icon> 使用)
for (const [name, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(name, component)
}

// 挂载 Element Plus(使用中文语言包,让组件内置文案显示中文)
app.use(ElementPlus, { locale: zhCn })

// 挂载到 index.html 里的 #app 节点
app.mount('#app')
