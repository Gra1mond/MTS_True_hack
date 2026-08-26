import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'chat', component: { template: '<div />' } },
    { path: '/settings', name: 'settings', component: { template: '<div />' } },
  ],
})

export default router
