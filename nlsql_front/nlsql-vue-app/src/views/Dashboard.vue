<template>
  <div class="dashboard">
    <div class="card">
      <h2 class="card-title">欢迎使用灵境语数</h2>
      <p class="welcome-text">
        NL2SQL智能数据查询平台，让数据查询变得更简单
      </p>
      <div class="stats-grid">
        <div class="stat-card">
          <el-icon class="stat-icon" :size="32">
            <Coin />
          </el-icon>
          <div class="stat-content">
            <div class="stat-value">5</div>
            <div class="stat-label">数据库</div>
          </div>
        </div>
        <div class="stat-card">
          <el-icon class="stat-icon" :size="32">
            <Link />
          </el-icon>
          <div class="stat-content">
            <div class="stat-value">12</div>
            <div class="stat-label">模型实例</div>
          </div>
        </div>
        <div class="stat-card">
          <el-icon class="stat-icon" :size="32">
            <ChatDotRound />
          </el-icon>
          <div class="stat-content">
            <div class="stat-value">856</div>
            <div class="stat-label">查询次数</div>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <h3 class="card-title">快速开始</h3>
      <el-steps direction="vertical" :active="1">
        <el-step title="配置数据源" description="连接您的数据库，支持MySQL、PostgreSQL等多种数据库"></el-step>
        <el-step title="语义建模" description="定义业务实体和关系，让系统理解您的业务语义"></el-step>
        <el-step title="自然语言查询" description="使用自然语言提问，系统自动转换为SQL并执行"></el-step>
      </el-steps>
    </div>
  </div>
</template>

<script setup>
import { Coin, Link, ChatDotRound } from '@element-plus/icons-vue'
</script>

<style scoped>
.dashboard {
  max-width: 1280px;
  margin: 0 auto;
}

.welcome-text {
  font-size: 16px;
  color: var(--text-secondary);
  margin-bottom: 24px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-top: 22px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 18px;
  background: var(--stats-gradient);
  border-radius: 14px;
  color: white;
  box-shadow: var(--stats-shadow);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--stats-shadow-hover);
}

.stat-icon {
  margin-right: 15px;
  opacity: 0.96;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  line-height: 1;
}

.stat-label {
  font-size: 14px;
  opacity: 0.92;
  margin-top: 5px;
}

:deep(.el-step) {
  padding-bottom: 8px;
}

:deep(.el-step__title) {
  color: var(--primary-color) !important;
}

:deep(.el-step__description) {
  color: var(--text-secondary) !important;
}
</style>
