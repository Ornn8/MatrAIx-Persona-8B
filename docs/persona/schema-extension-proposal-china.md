# Schema 扩展提案:中国数据新增维度(草案)

> 状态:提案(v0.1,未实施)| 关联:CGSS2017/2021、WVS 中国样本 crosswalk
> 原则:只在 **1290 维 schema 没有 home、但真实数据源有可靠信号** 时新增维度;每维必须有数据源变量可证、可 crosswalk 忠实映射。

## 背景

CGSS2017/2021 与 WVS 中国样本的提取过程中,以下构念在真实数据里信号强且被频繁引用,但 1290 维 schema 无对应维度,只能丢弃:

- 幸福感/生活满意度(CGSS a36、WVS Q46/Q49)
- 一般社会信任(CGSS a33/v458、WVS Q57——现有 `trust_level` 已承载其一)
- 机构信任(WVS I_TRUSTPOLICE/COURTS/ARMY)
- 社会公平感知(CGSS a35 系列)
- 孤独感/抑郁情绪(CGSS a17 已有 `bfi2_facet_depression`,但无独立孤独维度)
- 网络依赖/成瘾(CGSS c491-c4911,现有 `habit_doomscrolling` 是近似映射)
- 网购态度(CGSS c551 系列)
- 政治效能/政治兴趣(WVS Q26、CGSS 政治态度题)
- 婚姻家庭传统观(CGSS d181-d185 之外的婚姻观题)
- 孝道/家庭责任(CGSS d191-d197、d202——`val_family` 已近似承载)
- 宽容度(WVS I_HOMOLIB/I_ABORTLIB/I_DIVORLIB)
- 环保态度(CGSS 环保题、WVS 环保指数)
- 世俗价值观(WVS SACSECVAL)
- 民族认同/民族主义(WVS I_NATIONALISM/I_AUTHORITY)
- 居住安排/与父母同住(CGSS d3e 系列)
- 户籍/城乡二元(CGSS a18、H_URBRURAL——`urbanicity` 已近似)
- 生育态度(CGSS 生育观题)
- 工作价值观(WVS 工作目标题)
- 教育期望(CGSS 对子女教育期望)
- 灵性(WVS I_DEVOUT)

## 提案维度表

### P1 — 高置信度(3 源交叉验证 / 语义独立,优先实施)

| 建议 id | 说明 | category(复用) | allowed values | 数据源+变量 | 置信度 |
|---|---|---|---|---|---|
| `state_happiness` | 幸福感 | State: Emotional | Very happy / Happy / Neutral / Unhappy / Very unhappy | CGSS2017 a36;WVS Q46 | 高(CGSS a36 直接;WVS 方向已复核) |
| `life_satisfaction` | 生活满意度 | State: Emotional | Very satisfied / Satisfied / Neutral / Dissatisfied / Very dissatisfied | WVS Q49(1-10);CGSS 满意度题 | 高 |
| `att_institutional_trust` | 机构信任 | Values & Motivation | Trusting / Neutral / Distrusting | WVS I_TRUSTPOLICE/I_TRUSTCOURTS/I_TRUSTARMY 均值 | 高(WVS 指数) |
| `att_social_fairness` | 社会公平感知 | Values & Motivation | High / Moderate / Low | CGSS2017 a35 系列(公平判断) | 中高(题号待核对) |
| `state_loneliness` | 孤独感 | State: Emotional | Never / Rarely / Sometimes / Often | CGSS 孤独/心情题(待核);a17 近似 | 中 |
| `habit_internet_dependence` | 网络依赖 | Behavior: Habits | Daily / Weekly / Monthly / Rarely / Never | CGSS2017 c491-c4911(11 题聚合,替代现有 doomscrolling 近似) | 高(量表) |
| `lstyle_online_shopping` | 网购态度 | Behavior: Preferences | Frequent / Occasional / Rare / Never | CGSS2017 c551 系列 | 中高 |
| `att_political_engagement` | 政治参与兴趣 | Values & Motivation | Engaged / Neutral / Disengaged | WVS Q26;CGSS 政治兴趣题 | 中高 |
| `demo_living_arrangement` | 居住安排 | Demographic: Family | Lives alone / With partner / With children / With parents / Multigenerational / Other | CGSS d3e 同住编码 | 高 |
| `demo_hukou_status` | 户籍类型 | Demographic: Core | Urban hukou / Rural hukou / Unified household | CGSS a18 | 高(≠urbanicity,独立构念) |
| `att_marriage_traditionalism` | 婚姻传统观 | Values & Motivation | Enthusiast / Positive / Neutral / Skeptical / Opposed | CGSS 婚姻观题(d181-d185 体系) | 中高 |
| `val_filial_duty` | 孝道观念 | Values & Motivation | Core value / Important / Moderate / Minor / Irrelevant | CGSS d191-d197、d202 | 中高 |
| `att_sexuality_tolerance` | 性取向宽容 | Values & Motivation | Accepting / Neutral / Opposed | WVS I_HOMOLIB | 中高 |
| `att_environmental_concern` | 环保关注 | Values & Motivation | Strong / Moderate / Weak | CGSS 环保题、WVS 环保题 | 中 |
| `demo_migration_status` | 迁移经历 | Demographic: Core | Never migrated / Internal migrant / Returned | CGSS a21/a23-a25 | 高 |
| `lifex_mobility_history` | 流动经历 | Demographic: Life Events | Never left hometown / Moved within region / Moved nationally / Moved internationally | CGSS a21(现有 `lifex_geographic_mobility` 已近似,可合并) | 高 |

### P2 — 中/低置信度(需 codebook 复核或语义较弱,后置)

| 建议 id | 说明 | category | allowed values | 数据源+变量 | 置信度 |
|---|---|---|---|---|---|
| `val_secularism` | 世俗价值观 | Values & Motivation | Secular / Mixed / Sacred | WVS SACSECVAL | 中(指数语义需复核) |
| `att_nationalism` | 民族认同/爱国 | Values & Motivation | Strong / Moderate / Weak | WVS I_NATIONALISM/I_AUTHORITY | 中 |
| `val_work_ethic` | 工作价值观 | Values & Motivation | Achievement / Security / Balance | WVS 工作目标题 | 中低 |
| `att_procreation` | 生育意愿 | Values & Motivation | Pro-child / Neutral / Anti-child | CGSS 生育观题 | 中低 |
| `edu_expectation_children` | 对子女教育期望 | Education | Graduate / College / High school / Any | CGSS 教育期望题 | 低(题号漂移大) |

## 影响评估

1. **schema 本体**(`persona/schema/dimensions.json`):1290 → 1305+。每维需 id/label/category/values/index/phrase。category 全部复用现有 44 类,不新增类。
2. **taxonomy(阻塞性)**:`persona_taxonomy.json` 的 `expected_attribute_count` 与相关叶子 `expected_count` 必须同步;重跑 `generate_persona_taxonomy_mapping.ps1` 校验零报错并重新生成 CSV(`persona_taxonomy_mapping.csv`)。
3. **DAG 层**:`full_dag.json` 为每新维加节点(prior 可用 CGSS/WVS 分布统计)+ 轻量 edges/CPT;跑 `validate_graph.py`(0 违规)+ 采样审计边际漂移。**若已有发布 codes,兼容性最大风险点**(新维度无 codes 分布)。
4. **去重/发布**:`projection_config.json` 投影、`coreset_1m/targets.json` 校准可选加高置信度维度。
5. **Playground**:`dimension_categories.json` devProfile、persona_taxonomy 的 schema_categories 引用。
6. **crosswalk**:`cgss.py`/`cgss2021.py`/`wvs_cn.py` 各加 compute + selftest(缺失码/faithful 规则照旧);`labels2017/2021.json` 补标签。

## 建议实施顺序

1. **Schema + taxonomy 同步**(先做,阻断后续)
2. **DAG 节点 + 校验**(评估是否触发已发布 codes 重生成——若触发需专项决策)
3. **Crosswalk 扩展 + selftest + 全量重跑 validate**
4. **可选**:去重投影、coreset 校准、Playground dev pool 重生成

## 决策点

- [ ] P1 16 维是否全部采纳,还是先做"社会信任/福祉"6 维(幸福感/生活满意度/一般信任/机构信任/公平/孤独)?
- [ ] 新维度是否进入**合成 DAG**(影响合成 persona 边际)还是仅真实提取?
- [ ] 是否接受**已发布 Persona 1M codes 不重新生成**(新维度仅对未来提取生效)?
