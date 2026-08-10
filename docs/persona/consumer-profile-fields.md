# 消费行为子集字段(Consumer Profile Fields)

> 轻量方案,不改动 `persona/schema/dimensions.json` / taxonomy / DAG。
> 只在中国 persona 池(`source: cgss`,persona_id 前缀 `cgss2017-`/`cgss2021-`)生成,
> Playground 渲染为显式 opt-in —— 只有明确的中国市场研究场景才注入,满足数据隔离约束。

## 字段定义(10 个)

值一律用英文枚举(与 schema 惯例一致),渲染时按 `language` 映射中文。

| 字段 | 中文 | 值域(枚举) | grounded 来源(优先) | 推断依据(LLM) |
|---|---|---|---|---|
| `willingness_to_pay` | 付费意愿 | `low` / `moderate` / `high` | — | 收入/SES、消费态度 |
| `price_anchor` | 价格锚点(人民币) | `under_50` / `50-200` / `200-500` / `500-2000` / `2000+` | `socioeconomic_band` | 消费风格、职业 |
| `price_sensitivity` | 价格敏感度 | `low` / `moderate` / `high` | `pref_save_vs_spend` | 收入、节俭倾向 |
| `payment_model_pref` | 付费模式偏好 | `one_time` / `subscription` / `freemium` / `ad_supported` | `att_subscription_services`、`lstyle_payment_pref` | 订阅态度、支付习惯 |
| `promo_receptivity` | 推广接受度 | `open` / `selective` / `resistant` | `att_advertising` | 广告态度 |
| `trusted_channels` | 信任的渠道(多选) | `word_of_mouth` / `platform_reviews` / `official_channels` / `influencer` / `offline` | — | 年龄、媒体习惯、信任水平 |
| `spending_style` | 消费风格 | `frugal` / `balanced` / `generous` | `pref_save_vs_spend` | SES、子女负担 |
| `decision_factors` | 决策因素(按权重排序,3-5 项) | `price` / `quality` / `brand` / `word_of_mouth` / `convenience` | — | 品牌忠诚、广告态度 |
| `brand_loyalty` | 品牌忠诚度 | `low` / `moderate` / `high` | `att_brand_loyalty`、`trait_loyalty`、`val_loyalty` | 忠诚倾向 |
| `payment_motivations` | 付费理由(多选) | `core_need` / `time_saving` / `membership_perks` / `creator_support` / `none` | — | 时间观、便利偏好 |

## 诚实原则

- 每个值必须带 `evidence`:引用 persona 已有维度(`维度名: 值`)或 CGSS 原始答项;无法支撑则留空/`null`。
- 值域之外的推断(如具体愿意付多少钱)以 `price_anchor` 区间表达,不编造精确数字。
- 问卷未覆盖的字段(如 `trusted_channels` 无直接变量)由 LLM 从相关维度推断,标记 `summary_inference`。

## 生成与注入

- 生成:`persona/curation/existing_data/scripts/build_consumer_profiles.py`(DeepSeek,并行,逐文件幂等写回 YAML `consumer_profile:` 区块)。
- 注入:渲染上下文 `build_template_context_extras(..., consumer_profile=...)` 显式传入;`persona_system.md.j2` 条件渲染 `## 消费画像` 区块。默认不渲染,隔离中国数据。
