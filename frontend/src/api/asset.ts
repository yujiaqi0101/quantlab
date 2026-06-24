/**
 * Asset Registry API — 资产注册中心 API
 *
 * 统一管理所有量化资产：
 *   Dataset / FeatureSet / LabelSet / ModelPackage / StrategyPackage / RiskProfile / DeploymentProfile
 */
import { http } from './http'

// ==================================================================
// Types
// ==================================================================

export type AssetType =
  | 'DATASET'
  | 'FEATURE_SET'
  | 'LABEL_SET'
  | 'MODEL_PACKAGE'
  | 'STRATEGY_PACKAGE'
  | 'RISK_PROFILE'
  | 'DEPLOYMENT_PROFILE'

export type AssetStatus =
  | 'DRAFT'
  | 'ACTIVE'
  | 'ARCHIVED'
  | 'DEPRECATED'

export interface AssetIndex {
  asset_id: string
  name: string
  family: string
  version: string
  asset_type: AssetType
  status: AssetStatus
  created_at: string
  tags: string[]
  description: string
  hash: string
}

export interface AssetDetail extends AssetIndex {
  [key: string]: any
}

export interface AssetSummary {
  total_assets: number
  by_type: Record<string, number>
  n_families: number
  n_champions: number
  n_lineage_edges: number
}

export interface LineageNode {
  asset_id: string
  name: string
  asset_type: string
  version: string
}

export interface LineageTree {
  asset_id: string
  name: string
  asset_type: string
  version: string
  parents: LineageTree[]
  children: LineageTree[]
}

export interface AssetLineage {
  asset_id: string
  tree: LineageTree
  ancestors: LineageNode[]
  descendants: LineageNode[]
  dependency_chain: any[]
}

export interface ChampionPointer {
  family: string
  champion_asset_id: string
  promoted_at: string
  previous_champion_id: string
  promotion_reason: string
}

// ==================================================================
// 查询
// ==================================================================

export const assetApi = {
  /** 获取资产摘要 */
  getSummary(): Promise<AssetSummary> {
    return http.get('/asset/summary').then((r) => r.data)
  },

  /** 列出资产 */
  listAssets(params?: {
    asset_type?: AssetType
    family?: string
    status?: AssetStatus
  }): Promise<{ total: number; assets: AssetIndex[] }> {
    return http.get('/asset/list', { params }).then((r) => r.data)
  },

  /** 获取资产详情 */
  getAsset(assetId: string): Promise<AssetDetail> {
    return http.get(`/asset/${assetId}`).then((r) => r.data)
  },

  /** 获取资产 manifest */
  getManifest(assetId: string): Promise<any> {
    return http.get(`/asset/${assetId}/manifest`).then((r) => r.data)
  },

  /** 获取资产血缘 */
  getLineage(assetId: string): Promise<AssetLineage> {
    return http.get(`/asset/${assetId}/lineage`).then((r) => r.data)
  },

  /** 获取所有 Champion */
  getAllChampions(): Promise<{ total: number; champions: Record<string, AssetIndex> }> {
    return http.get('/asset/champions/all').then((r) => r.data)
  },

  /** 获取指定 Family 的 Champion */
  getChampion(family: string): Promise<AssetDetail> {
    return http.get(`/asset/champions/${family}`).then((r) => r.data)
  },

  /** 列出所有 Family */
  listFamilies(): Promise<{ total: number; families: string[] }> {
    return http.get('/asset/families/all').then((r) => r.data)
  },

  /** 获取 Family 版本历史 */
  getFamilyVersions(family: string): Promise<{ family: string; total: number; versions: any[] }> {
    return http.get(`/asset/families/${family}/versions`).then((r) => r.data)
  },

  /** 搜索资产 */
  search(query: string): Promise<{ query: string; total: number; assets: AssetIndex[] }> {
    return http.get(`/asset/search/${query}`).then((r) => r.data)
  },

  // ------------------------------------------------------------------
  // 注册
  // ------------------------------------------------------------------

  registerDataset(req: any): Promise<{ asset_id: string; status: string }> {
    return http.post('/asset/register/dataset', req).then((r) => r.data)
  },

  registerFeatureSet(req: any): Promise<{ asset_id: string; status: string }> {
    return http.post('/asset/register/feature-set', req).then((r) => r.data)
  },

  registerLabelSet(req: any): Promise<{ asset_id: string; status: string }> {
    return http.post('/asset/register/label-set', req).then((r) => r.data)
  },

  registerModelPackage(req: any): Promise<{ asset_id: string; status: string }> {
    return http.post('/asset/register/model-package', req).then((r) => r.data)
  },

  registerStrategyPackage(req: any): Promise<{ asset_id: string; status: string }> {
    return http.post('/asset/register/strategy-package', req).then((r) => r.data)
  },

  // ------------------------------------------------------------------
  // 管理
  // ------------------------------------------------------------------

  setChampion(req: {
    family: string
    asset_id: string
    reason: string
  }): Promise<ChampionPointer> {
    return http.post('/asset/champion/set', req).then((r) => r.data)
  },

  addLineage(req: {
    parent_asset_id: string
    child_asset_id: string
    relation: string
    note: string
  }): Promise<{ status: string }> {
    return http.post('/asset/lineage/add', req).then((r) => r.data)
  },
}
