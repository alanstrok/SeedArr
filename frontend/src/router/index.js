import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: 'Dashboard', icon: 'mdi-view-dashboard' },
  },
  {
    path: '/torrents',
    name: 'Torrents',
    component: () => import('@/views/Torrents.vue'),
    meta: { title: 'Torrents', icon: 'mdi-download' },
  },
  {
    path: '/rules',
    name: 'Rules',
    component: () => import('@/views/Rules.vue'),
    meta: { title: 'Rules', icon: 'mdi-format-list-checks' },
  },
  {
    path: '/trackers',
    name: 'Trackers',
    component: () => import('@/views/Trackers.vue'),
    meta: { title: 'Trackers', icon: 'mdi-server-network' },
  },
  {
    path: '/connections',
    name: 'Connections',
    component: () => import('@/views/Connections.vue'),
    meta: { title: 'Connections', icon: 'mdi-connection' },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/Settings.vue'),
    meta: { title: 'Settings', icon: 'mdi-cog' },
  },
  {
    path: '/logs',
    name: 'Logs',
    component: () => import('@/views/Logs.vue'),
    meta: { title: 'Logs', icon: 'mdi-text-box-multiple' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
