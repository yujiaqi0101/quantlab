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
      {
        path: 'observe',
        name: 'ObserveOverview',
        component: () => import('@/views/observe/OverviewView.vue'),
        meta: { title: 'Observe Studio', icon: 'View' },
      },
      {
        path: 'observe/overview',
        name: 'ObserveOverviewDetail',
        component: () => import('@/views/observe/OverviewView.vue'),
        meta: { title: 'Overview', icon: 'View' },
      },
      {
        path: 'observe/positions',
        name: 'ObservePositions',
        component: () => import('@/views/observe/PositionsView.vue'),
        meta: { title: 'Positions', icon: 'Wallet' },
      },
      {
        path: 'observe/orders',
        name: 'ObserveOrders',
        component: () => import('@/views/observe/OrdersView.vue'),
        meta: { title: 'Orders', icon: 'List' },
      },
      {
        path: 'observe/trades',
        name: 'ObserveTrades',
        component: () => import('@/views/observe/TradesView.vue'),
        meta: { title: 'Trades', icon: 'Tickets' },
      },
      {
        path: 'observe/risk',
        name: 'ObserveRisk',
        component: () => import('@/views/observe/RiskView.vue'),
        meta: { title: 'Risk', icon: 'Warning' },
      },
      {
        path: 'observe/health',
        name: 'ObserveHealth',
        component: () => import('@/views/observe/HealthView.vue'),
        meta: { title: 'Strategy Health', icon: 'Heart' },
      },
      {
        path: 'observe/timeline',
        name: 'ObserveTimeline',
        component: () => import('@/views/observe/TimelineView.vue'),
        meta: { title: 'Timeline', icon: 'Timer' },
      },
      {
        path: 'observe/replay',
        name: 'ObserveReplay',
        component: () => import('@/views/observe/ReplayView.vue'),
        meta: { title: 'Replay', icon: 'VideoPlay' },
      },
      {
        path: 'observe/analysis',
        name: 'ObserveAnalysis',
        component: () => import('@/views/observe/AnalysisView.vue'),
        meta: { title: 'Root Cause', icon: 'Aim' },
      },
      {
        path: 'observe/performance',
        name: 'ObservePerformance',
        component: () => import('@/views/observe/PerformanceView.vue'),
        meta: { title: 'Performance', icon: 'TrendCharts' },
      },
      {
        path: 'observe/journal',
        name: 'ObserveJournal',
        component: () => import('@/views/observe/JournalView.vue'),
        meta: { title: 'Journal', icon: 'Notebook' },
      },
      {
        path: 'trading',
        name: 'TradingStudio',
        component: () => import('@/views/trading/TradingStudio.vue'),
        meta: { title: 'Trading Studio', icon: 'VideoCamera' },
        children: [
          { path: '', redirect: '/trading/overview' },
          { path: 'overview', name: 'TradingOverview', component: () => import('@/views/trading/workspaces/OverviewWorkspace.vue'), meta: { title: 'Overview' } },
          { path: 'market', name: 'TradingMarket', component: () => import('@/views/trading/workspaces/MarketWorkspace.vue'), meta: { title: 'Market' } },
          { path: 'signals', name: 'TradingSignals', component: () => import('@/views/trading/workspaces/SignalsWorkspace.vue'), meta: { title: 'Signals' } },
          { path: 'orders', name: 'TradingOrders', component: () => import('@/views/trading/workspaces/OrdersWorkspace.vue'), meta: { title: 'Orders' } },
          { path: 'positions', name: 'TradingPositions', component: () => import('@/views/trading/workspaces/PositionsWorkspace.vue'), meta: { title: 'Positions' } },
          { path: 'portfolio', name: 'TradingPortfolio', component: () => import('@/views/trading/workspaces/PortfolioWorkspace.vue'), meta: { title: 'Portfolio' } },
          { path: 'risk', name: 'TradingRisk', component: () => import('@/views/trading/workspaces/RiskWorkspace.vue'), meta: { title: 'Risk' } },
          { path: 'journal', name: 'TradingJournal', component: () => import('@/views/trading/workspaces/JournalWorkspace.vue'), meta: { title: 'Journal' } },
          { path: 'replay', name: 'TradingReplay', component: () => import('@/views/trading/workspaces/ReplayWorkspace.vue'), meta: { title: 'Replay' } },
        ],
      },
      {
        path: 'live',
        redirect: '/trading',
      },
      {
        path: 'ml-lab',
        name: 'MLLab',
        component: () => import('@/views/ml_lab/MLLab.vue'),
        meta: { title: 'ML Lab', icon: 'Cpu' },
      },
      {
        path: 'research-graph',
        name: 'ResearchGraph',
        component: () => import('@/views/research_graph/ResearchGraphStudio.vue'),
        meta: { title: 'Research Graph Studio', icon: 'Share' },
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
