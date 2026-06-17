import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'

const routes = [
  {
    path: '/',
    component: MainLayout,
    redirect: '/studio',
    children: [
      {
        path: 'studio',
        name: 'Studio',
        component: () => import('@/views/studio/ResearchStudio.vue'),
        meta: { title: 'Research Dashboard', icon: 'DataLine' },
      },
      {
        path: 'strategies',
        name: 'Strategies',
        component: () => import('@/views/strategies/StrategyList.vue'),
        meta: { title: 'Strategies', icon: 'Odometer' },
      },
      {
        path: 'strategy-builder',
        name: 'StrategyBuilder',
        component: () => import('@/views/strategies/StrategyBuilder.vue'),
        meta: { title: 'Strategy Builder', icon: 'SetUp' },
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
      {
        path: 'compare',
        name: 'Compare',
        component: () => import('@/views/compare/ExperimentCompare.vue'),
        meta: { title: 'Compare Experiments', icon: 'TrendCharts' },
      },
      {
        path: 'leaderboard',
        name: 'Leaderboard',
        component: () => import('@/views/leaderboard/LeaderboardPage.vue'),
        meta: { title: 'Leaderboard', icon: 'Trophy' },
      },
      {
        path: 'factors',
        name: 'Factors',
        component: () => import('@/views/factors/FactorStudio.vue'),
        meta: { title: 'Factor Studio', icon: 'Histogram' },
      },
      {
        path: 'signals',
        name: 'Signals',
        component: () => import('@/views/signals/SignalWorkspace.vue'),
        meta: { title: 'Signal Research', icon: 'Switch' },
      },
      {
        path: 'research',
        name: 'ResearchLab',
        component: () => import('@/views/research/ResearchLab.vue'),
        meta: { title: 'Research Lab', icon: 'Cpu' },
      },
      {
        path: 'production',
        name: 'ProductionStudio',
        component: () => import('@/views/production/ProductionStudio.vue'),
        meta: { title: 'Production Studio', icon: 'Monitor' },
      },
      {
        path: 'fidelity',
        name: 'FidelityStudio',
        component: () => import('@/views/fidelity/FidelityStudio.vue'),
        meta: { title: 'Execution Fidelity', icon: 'Aim' },
      },
      {
        path: 'alpha-aware',
        name: 'AlphaAwareStudio',
        component: () => import('@/views/alpha_aware/AlphaAwareStudio.vue'),
        meta: { title: 'Alpha-Aware', icon: 'Connection' },
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
