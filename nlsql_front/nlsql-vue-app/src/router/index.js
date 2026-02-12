import { createRouter, createWebHistory } from 'vue-router'
import Layout from '../components/Layout.vue'

const routes = [
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue')
      },
      {
        path: 'database',
        name: 'Database',
        component: () => import('../views/Database.vue')
      },
      {
        path: 'table-metadata',
        name: 'TableMetadata',
        component: () => import('../views/TableMetadata.vue')
      },
      {
        path: 'metadata-detail',
        name: 'MetadataDetail',
        component: () => import('../views/MetadataDetail.vue')
      },
      {
        path: 'table-metadata-manage',
        name: 'TableMetadataManage',
        component: () => import('../views/TableMetadataManage.vue')
      },
      {
        path: 'model',
        name: 'Model',
        component: () => import('../views/Model.vue')
      },
      {
        path: 'instance',
        name: 'Instance',
        component: () => import('../views/Instance.vue')
      },
      {
        path: 'task',
        name: 'Task',
        component: () => import('../views/Task.vue')
      },
      {
        path: 'entity',
        name: 'Entity',
        component: () => import('../views/Entity.vue')
      },
      {
        path: 'element',
        name: 'Element',
        component: () => import('../views/Element.vue')
      },
      {
        path: 'entity-relation',
        name: 'EntityRelation',
        component: () => import('../views/EntityRelation.vue')
      },
      {
        path: 'prompt',
        name: 'Prompt',
        component: () => import('../views/Prompt.vue')
      },
      {
        path: 'prompt-config',
        name: 'PromptConfig',
        component: () => import('../views/PromptConfig.vue')
      },
      {
        path: 'knowledge',
        name: 'Knowledge',
        component: () => import('../views/Knowledge.vue')
      },
      {
        path: 'qa-example',
        name: 'QAExample',
        component: () => import('../views/QAExample.vue')
      },
      {
        path: 'test',
        name: 'Test',
        component: () => import('../views/Test.vue')
      },
      {
        path: 'history',
        name: 'History',
        component: () => import('../views/History.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
