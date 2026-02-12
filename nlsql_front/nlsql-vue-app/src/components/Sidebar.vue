<template>
  <div class="sidebar">
    <div class="sidebar-header">
      灵境语数
    </div>

    <div class="menu-group" v-for="group in menuGroups" :key="group.title">
      <div class="menu-group-title" @click="toggleGroup(group)">
        <span>{{ group.title }}</span>
        <el-icon :class="{ 'rotate-180': group.expanded }">
          <ArrowDown />
        </el-icon>
      </div>
      <transition name="fade">
        <div v-show="group.expanded">
          <router-link
            v-for="item in group.items"
            :key="item.path"
            :to="item.path"
            class="menu-item"
            :class="{ active: $route.path === item.path }"
          >
            <el-icon class="mr-2">
              <component :is="item.icon" />
            </el-icon>
            <span>{{ item.title }}</span>
          </router-link>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import {
  ArrowDown,
 Coin,
  Link,
  Monitor,
  Setting,
  Document,
  ChatDotRound,
  EditPen,
  Folder,
  DataAnalysis,
  Clock,
  Tickets,
   List,
   Connection
} from '@element-plus/icons-vue'

const menuGroups = ref([
  {
    title: '资源集成',
    expanded: true,
    items: [
      { title: '数据库管理', path: '/database', icon: 'Coin' },
      { title: '模型管理', path: '/model', icon: 'Link' },
      { title: '实例管理', path: '/instance', icon: 'Monitor' },
      { title: '任务管理', path: '/task', icon: 'Tickets' }
    ]
  },
  {
    title: '数据库元数据',
    expanded: true,
    items: [
      { title: '基础数据', path: '/table-metadata', icon: 'List' },
      { title: '详细元数据', path: '/metadata-detail', icon: 'Document' },
      { title: '元数据管理', path: '/table-metadata-manage', icon: 'Setting' }
    ]
  },
  {
    title: '语义建模',
    expanded: true,
    items: [
      { title: '实体管理', path: '/entity', icon: 'Setting' },
      { title: '要素管理', path: '/element', icon: 'Document' },
      { title: '实体关系', path: '/entity-relation', icon: 'Connection' }
    ]
  },
  {
    title: '策略优化',
    expanded: false,
    items: [
      { title: '提示词管理', path: '/prompt', icon: 'EditPen' },
      { title: '提示词生成配置', path: '/prompt-config', icon: 'Setting' },
      { title: '知识管理', path: '/knowledge', icon: 'Folder' },
      { title: '问答样例管理', path: '/qa-example', icon: 'ChatDotRound' }
    ]
  },
  {
    title: '评估与审计',
    expanded: false,
    items: [
      { title: '测试问答', path: '/test', icon: 'DataAnalysis' },
      { title: '历史会话查看', path: '/history', icon: 'Clock' }
    ]
  }
])

const toggleGroup = (group) => {
  group.expanded = !group.expanded
}
</script>

<style scoped>
.rotate-180 {
  transform: rotate(180deg);
  transition: transform 0.3s ease;
}

.menu-group-title .el-icon {
  transition: transform 0.3s ease;
}

.menu-item {
  font-size: 13px;
}

.mr-2 {
  margin-right: 8px;
  font-size: 16px;
  opacity: 0.92;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-2px);
}
</style>
