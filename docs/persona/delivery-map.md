# 中国 Persona 管线 — 交付总览

面向研究计划(用 agent 模拟真实用户对产品的**评价 / 使用体验 / 付费意愿 / 推广接受度 / 定价改变反应**)的中国 persona 数据管线,全部代码已推送到 fork(`Ornn8/MatrAIx-Persona-8B`)。

## 交付物清单

| # | 交付物 | 位置 | 状态 |
|---|---|---|---|
| 1 | CGSS2017 crosswalk(44 维 observed) | `persona/curation/existing_data/scripts/crosswalks/cgss.py` | ✅ 12,582 条,validate 0 错误 |
| 2 | CGSS2021 crosswalk(29 维 observed) | `.../crosswalks/cgss2021.py` | ✅ 8,148 条,validate 0 错误 |
| 3 | WVS wave-7 中国 crosswalk(9 维) | `.../crosswalks/wvs_cn.py` | ✅ 3,036 条,validate 0 错误 |
| 4 | LLM 富化引擎(evidence-grounded,~422 维可推断子集) | `.../scripts/llm_infer_engine.py` | ✅ |
| 5 | 并行批量跑批(分片断点续跑) | `.../scripts/run_llm_batch.py` | ✅ 200 人,~105.4 维/人 |
| 6 | **CGSS2017 LLM 池**(200 人) | `persona/datasets/cgss2017-llm/` | ✅ 含消费画像 |
| 7 | **WVS 中国池**(3,036 人) | `persona/datasets/wvs-cn/` | ✅ observed-only,隔离 |
| 8 | **消费画像子集**(10 字段/人) | `persona/datasets/cgss2017-llm/*.yaml` + `build_consumer_profiles.py` | ✅ 200/200,零 LLM 兜底 |
| 9 | 中文渲染(labels_zh 1290/1290 + 模板) | `persona/schema/labels_zh.json`、`persona_dimension_catalog.py`、j2 模板 | ✅ `MATRAIX_PERSONA_LANGUAGE=zh` |
| 10 | 前端 i18n 修复(高+中优先级) | `application/playground/frontend/src/**` | ✅ typecheck + build 通过 |
| 11 | schema 扩展提案(21 候选维度,不阻塞) | `docs/persona/schema-extension-proposal-china.md` | 📋 待决策 |
| 12 | **端到端冒烟验证** | `.../scripts/smoke_china_pipeline.py` | ✅ 全过 |
| 13 | 各数据源 manifest | `persona/curation/existing_data/manifests/` | ✅ 4 份 |

## 隔离原则(已落实)

- 中国池 `source` 标记:`cgss` / `wvs_cn`;persona_id 前缀 `cgss2017-`/`cgss2021-`/`wvs-cn-` 保留在 provenance
- 消费画像渲染为**显式 opt-in**:`build_template_context_extras(..., consumer_profile=...)`,不传不渲染
- 各池独立 manifest、独立目录,不混入通用池

## 验证方式

```bash
# 数据层
python persona/human_extraction/scripts/validate_extraction.py --input <extraction>.jsonl.gz --schema persona/schema/dimensions.json
# 端到端冒烟(加载/渲染/隔离/schema 值)
python persona/curation/existing_data/scripts/smoke_china_pipeline.py
# 前端
cd application/playground/frontend && npm run typecheck && npm run build
# 后端测试
python -m pytest tests/unit/matraix/test_persona_dimension_narrative.py
```

## 待决事项

1. **CGSS2021 LLM 富化**:2021 数据最新(8,148 人)但目前只有 observed-only 29 维;做 200 人 LLM 池需 API 成本(~1-2 小时)。是否执行?
2. **schema 扩展 3 个决策点**:happiness/信任/户口维度是否进入 1290 维(taxonomy 变更风险,见提案文档)。
3. **Playground 中国市场实验模板**:基于消费画像的定价 A/B、推广偏好问卷等场景模板,可下一步做。
4. **行为校准**:模拟付费意愿对照真实市场转化率(需要目标产品数据)。

## 数据来源与许可

- CGSS2017/CGSS2021:中国综合社会调查(中国人民大学),CNSDA 注册下载,仅学术使用
- WVS wave-7 中国:世界价值观调查公开样本(2018,n=3,036)
- 原始数据(.dta/.csv)与提取产物均 gitignored,仓库只含代码与 manifest
