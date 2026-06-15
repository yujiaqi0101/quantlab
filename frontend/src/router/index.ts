import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'

const routes = [
  {
    path: '/',
    component: MainLayout,
    redirect: '/strategies',
    children: [
      {
        path: 'strategies',
        name: 'Strategies',
        component: () => import('@/views/strategies/StrategyList.vue'),
        meta: { title: 'Strategies', icon: 'Odometer' },
      },
      {
        path: 'strategies/:id',
        name: 'StrategyDetail',
        component: () => import('@/views/strategies/StrategyDetail.vue'),
        meta: { title: 'Strategy Detail', icon: 'Odometer' },
      },
      {
        path: 'datasets',
        name: 'Datasets',
        component: () => import('@/views/datasets/DatasetList.vue'),
        meta: { title: 'Datasets', icon: 'Coin' },
      },
      {
        path: 'datasets/:id',
        name: 'DatasetDetail',
        component: () => import('@/views/datasets/DatasetDetail.vue'),
        meta: { title: 'Dataset Detail', icon: 'Coin' },
      },
      {
        path: 'backtests',
        name: 'Backtests',
        component: () => import('@/views/backtests/BacktestWorkspace.vue'),
        meta: { title: 'Backtest Workspace', icon: 'DataLine' },
      },
      {
        path: 'experiments',
        name: 'Experiments',
        component: () => import('@/views/experiments/ExperimentList.vue'),
        meta: { title: 'Experiments', icon: 'Files' },
      },
      {
        path: 'experiments/:id',
        name: 'ExperimentDetail',
        component: () => import('@/views/experiments/ExperimentDetail.vue'),
        meta: { title: 'Experiment Detail', icon: 'Files' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  document.title = `${to.meta.title || 'QuantLab'} - QuantLab Studio`
})

export default router
