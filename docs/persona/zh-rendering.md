# Persona 渲染语言(Persona Rendering Language)

Persona 叙述(prompt 中渲染给 agent 的 1290 维画像)默认是英文,支持按需切换为简体中文。

## 开关方式

| 方式 | 说明 |
|---|---|
| 环境变量 `MATRAIX_PERSONA_LANGUAGE=zh` | 进程级默认中文;不设置或非 `zh` 即英文(向后兼容) |
| 代码参数 `build_dimension_narrative(..., language="zh")` | 单次调用级覆盖,优先级高于环境变量 |

模板层的 "You are {name}." / "## Who you are" 与叙述内容同步切换:
- `persona_system.md.j2`、`persona_instruction.md.j2`:"You are" ↔ "你是"
- `persona_macros.md.j2`:`render_persona_narrative` 的 "## Who you are" ↔ "## 你是谁"

## 翻译表

`persona/schema/labels_zh.json`(1290 维 × 全部取值,6347 条):

```json
{
  "age_bracket": {"label": "年龄段", "values": {"35-44": "35-44岁", ...}},
  ...
}
```

- 由 `translate_schema_labels.py` 生成(DeepSeek 批量翻译,支持 resume)
- 渲染时缺失的维度/取值**回退英文**(不会报错、不会改变维度集合与顺序)
- 专有名词(Python/GitHub/Mandarin 等)按规则保留原文

## 行为保证

- 默认(`language=None` + 无环境变量)→ 英文,输出与改造前逐字节一致
- 中文模式仅替换 label/value/section 标题的**文本**,不改变:
  - 维度集合与排序(`collect_dimension_items` 逻辑不变)
  - 预算截断逻辑(按字符计,中文更紧凑,实际可用维度更多)
  - 跳过规则(`_NULLISH`、defaultValue)
- 回归测试:`tests/unit/matraix/test_persona_dimension_narrative.py`(zh 渲染、英文回退、空表回退)

## 典型用途

`source: cgss` 的中国 persona 池配合 `MATRAIX_PERSONA_LANGUAGE=zh` 即可让 agent 以中文身份叙述参与中文产品评测场景。
