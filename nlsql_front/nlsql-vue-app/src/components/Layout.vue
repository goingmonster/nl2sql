<template>
  <div class="app-container">
    <!-- 头部 -->
    <header class="header">
      <div class="brand-block">
        <div class="logo">灵境语数</div>
        <div class="brand-subtitle">企业级 NL2SQL 智能数据查询平台</div>
      </div>
      <div class="header-actions">
        <div class="status-pill">
          <span class="status-dot" />
          系统运行中
        </div>
        <el-dropdown trigger="click" @command="handleThemeChange">
          <el-button class="theme-btn" text>
            主题切换
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item
                v-for="item in themeOptions"
                :key="item.value"
                :command="item.value"
              >
                {{ item.label }}
                <span v-if="currentTheme === item.value" class="selected-mark">✓</span>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button type="primary" class="header-btn">
          配置向导
        </el-button>
      </div>
    </header>

    <!-- 侧边栏 -->
    <Sidebar />

    <!-- 主内容区 -->
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import Sidebar from './Sidebar.vue'

const THEME_KEY = 'nlsql-theme'
const themeOptions = [
  { label: '紫色主题', value: 'purple' },
  { label: '海洋主题', value: 'ocean' },
  { label: '蓝白主题', value: 'bluewhite' }
]
const currentTheme = ref('purple')

const applyTheme = (theme) => {
  const validTheme = themeOptions.some(item => item.value === theme) ? theme : 'purple'
  document.documentElement.setAttribute('data-theme', validTheme)
  localStorage.setItem(THEME_KEY, validTheme)
  currentTheme.value = validTheme
}

const handleThemeChange = (theme) => {
  applyTheme(theme)
}

onMounted(() => {
  applyTheme(localStorage.getItem(THEME_KEY) || 'purple')
})
</script>

<style>
.app-container {
  width: 100%;
  min-height: 100vh;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-btn {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.2), rgba(255, 255, 255, 0.08));
  border: 1px solid rgba(255, 255, 255, 0.34);
  border-radius: 999px;
  padding: 8px 18px;
  font-size: 13px;
  font-weight: 600;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.theme-btn {
  height: 30px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.34);
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  font-size: 12px;
  padding: 0 12px;
}

.theme-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.52);
}

.selected-mark {
  margin-left: 8px;
  color: var(--primary-color);
  font-weight: 700;
}

.header-btn:hover {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.34), rgba(255, 255, 255, 0.18));
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(6, 27, 49, 0.24);
}

.brand-block {
  display: flex;
  flex-direction: column;
}

.brand-subtitle {
  font-size: 11px;
  letter-spacing: 0.2px;
  opacity: 0.86;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.32);
  background: rgba(255, 255, 255, 0.12);
  font-size: 12px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #79f2ca;
  box-shadow: 0 0 0 4px rgba(121, 242, 202, 0.22);
}

@media (max-width: 860px) {
  .brand-subtitle,
  .status-pill {
    display: none;
  }
}
</style>
