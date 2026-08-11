# Playground i18n 架构重构方案

> 响应上游 PR 评审(MatrAIx-ai/MatrAIx-Persona-8B PR #20)的 4 点要求。
> 目标:把当前"每文件双语言表 + 二元切换"的 i18n 实现,重构为
> **每语言一个 pack、可懒加载、可扩展、English-first** 的架构。
> v1 仅内置 `en-US` + `zh-CN`,但架构不硬编码二元语言。

## 1. 目标与验收标准(对应评审 4 点)

| # | 官方要求 | 验收标准 |
|---|---|---|
| 1 | 独立语言维度 | 每个 locale 一个独立 pack 文件;locale registry;通用 picker;懒加载;缺失 key 回退英文 |
| 2 | UI locale 与 runtime/persona 语言分离 | UI 翻译只覆盖 chrome;persona/prompt 语言走独立 `language` 字段(已有 `MATRAIX_PERSONA_LANGUAGE`),不耦合到 UI i18n |
| 3 | 默认可覆盖 + 记录 | 默认跟随 UI;可覆盖(Follow UI / en / zh);run 记录生效语言与来源;后端不把浏览器 locale 当权威 |
| 4 | English-first | `en-US` 为默认与源语言;其他 locale 是可选附加 pack;UI 默认不设非英文 |

## 2. 现状与差距

| 维度 | 现状 | 差距 |
|---|---|---|
| pack 结构 | `messages/sections/*.ts` 14 个文件,每个内含 `{en-US, zh-CN}` 双表 | 双表硬编码进每个文件,非单语言 pack |
| 加载 | `import.meta.glob(..., eager: true)` 全量打进主 bundle | 无懒加载,所有语言常驻 |
| 语言枚举 | `type Locale = "zh-CN" \| "en-US"` + `toggleLocale` 二元切换 | 无 registry、无通用 picker,不可扩展 |
| 默认 | `DEFAULT_LOCALE = "zh-CN"` | **违反 English-first,必须改 `en-US`** |
| 缺失回退 | `dictionaries[locale][key] ?? en-US ?? fallback` | ✅ 已符合 |
| runtime 语言 | 后端 `MATRAIX_PERSONA_LANGUAGE` 环境变量/参数 | 部分符合 #2;`job/request` 显式字段 + 持久化留后续迭代(#3) |

## 3. 目标架构

```
application/playground/frontend/src/i18n/
├── types.ts                    # Locale / LocaleMeta / MessageValues
├── registry.ts                 # locale 注册表 + 懒加载 loader
├── I18nProvider.tsx            # 懒加载 provider,en-US 常驻兜底
├── picker.tsx                  # 通用语言选择器(组件)
└── messages/
    ├── packs/
    │   ├── en-US.ts            # 单语言 pack:扁平 { key: string }
    │   └── zh-CN.ts            # 单语言 pack:扁平 { key: string }
    └── sections/               # (删除,合并入 packs)
```

### 3.1 types.ts

```ts
export type Locale = "en-US" | "zh-CN"; // 可扩展:追加即加 pack 文件 + 注册表项

export interface LocaleMeta {
  code: Locale;
  /** 语言自述名,如 "English" / "简体中文" */
  label: string;
  /** 英文名,用于 en 界面展示其他语言 */
  englishName: string;
}

export type MessageValues = Record<string, string | number>;
/** 单语言 pack:扁平 key → 文案 */
export type MessagePack = Record<string, string>;
```

### 3.2 registry.ts

```ts
import type { Locale, LocaleMeta, MessagePack } from "./types";

/** 语言注册表 —— 新增语言只需:加 pack 文件 + 在此登记 */
export const LOCALE_REGISTRY: LocaleMeta[] = [
  { code: "en-US", label: "English", englishName: "English" },
  { code: "zh-CN", label: "简体中文", englishName: "Simplified Chinese" },
];

/** 懒加载映射:en-US 静态常驻(默认+兜底),其余动态 import */
export const localePacks: Record<Locale, () => Promise<MessagePack>> = {
  "en-US": () => import("./messages/packs/en-US").then((m) => m.default),
  "zh-CN": () => import("./messages/packs/zh-CN").then((m) => m.default),
};
```

### 3.3 I18nProvider.tsx

- **en-US pack 静态 import 常驻**(作为默认与缺失回退基座,任何时刻可用)。
- 其他 locale:首次切换时 `localePacks[locale]()` 动态加载;加载期间 `t()` 用 en-US 兜底,加载完成后切换。
- `DEFAULT_LOCALE = "en-US"`。
- 暴露:`locale / setLocale / locales(注册表)/ t / formatNumber / formatDate`。
- 移除二元 `toggleLocale`(TopBar 改用 picker)。

```tsx
const enPack = enUSPack; // 静态 import
export function I18nProvider({ children }) {
  const [locale, setLocaleState] = useState<Locale>(readStoredLocale); // 默认 en-US
  const [pack, setPack] = useState<MessagePack>(enPack);
  const [loading, setLoading] = useState(false);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    setLoading(true);
    localePacks[next]().then((p) => { setPack(p); setLoading(false); })
      .catch(() => { setPack(enPack); setLoading(false); }); // 加载失败回退 en
    try { window.localStorage.setItem(STORAGE_KEY, next); } catch {}
  }, []);

  const t = (key, fallback = key, values) =>
    interpolate(pack[key] ?? enPack[key] ?? fallback, values);
  // locale 变化时 pack 异步更新;期间 pack=旧 pack?见 §3.4
}
```

### 3.4 语言切换的瞬时一致性

切换瞬间 `pack` 还是旧语言,会导致"新 locale 名 + 旧语言文案"一闪而过。
方案:切换时**立即把 pack 置为 en-US**(常驻,同步可用),再异步加载目标 pack。
`t()` 始终取 `pack[key] ?? enPack[key] ?? fallback`,故任何时刻都有 en 兜底,不会空白。

### 3.5 picker.tsx

从 `LOCALE_REGISTRY` 渲染通用下拉/菜单:

```tsx
export function LocalePicker({ compact = false }) {
  const { locale, setLocale } = useI18n();
  return (
    <select value={locale} onChange={(e) => setLocale(e.target.value as Locale)}
      aria-label={t("shell.locale.picker", "Language")}>
      {LOCALE_REGISTRY.map((l) => (
        <option key={l.code} value={l.code}>{l.label}</option>
      ))}
    </select>
  );
}
```

### 3.6 pack 文件生成

`en-US.ts` / `zh-CN.ts` 由现有 14 个 section 文件**合并展开**得到(脚本一次性生成,后续手工维护单语言 pack):

```ts
// messages/packs/en-US.ts
export default {
  "shell.nav.application": "Application",
  "shell.nav.personaWorld": "Persona World",
  // …全部 en 文案(扁平 key)
};
```

## 4. 实施步骤

1. **生成单语言 pack**:脚本读 `sections/*.ts`,提取 `en-US`/`zh-CN` 两段,分别合并为 `packs/en-US.ts`、`packs/zh-CN.ts`(扁平 key)。
2. **types.ts**:扩展 `LocaleMeta`/`LOCALE_REGISTRY`/`MessagePack`。
3. **registry.ts**:`localePacks` 懒加载映射(替代 `dictionaries`)。
4. **I18nProvider.tsx**:懒加载 + en-US 常驻 + `DEFAULT_LOCALE="en-US"` + 移除 `toggleLocale`。
5. **TopBar**:二元切换按钮 → `LocalePicker`(通用下拉)。
6. **删除** `sections/` 与旧 `registry.ts` 的 eager glob。
7. **验证**:`npm run typecheck` + `npm run build`;en 默认渲染确认与官方原版一致;切 zh 懒加载确认。
8. **提交 + 更新 PR #20 + 回复官方评审**(说明架构已按 4 点要求重构,v1 内置 en+zh-CN,可扩展)。

## 5. 明确不做(本轮范围外)

| 项 | 说明 |
|---|---|
| runtime/persona 语言显式字段(job/request `language` + follow-UI/override + 持久化) | 官方"可迭代";后端已有 `MATRAIX_PERSONA_LANGUAGE` 独立机制,任务正文语言由任务自身管理,本轮不动 |
| 新增第三种语言 | 架构支持即可,不新增 |
| 任务/产物内容翻译 | UI 只翻 chrome |

## 6. 风险与兼容

- **en 默认回退**:pack[key] 缺失时 en-US 兜底,不会出现空白;en-US 是唯一"必须完整"的 pack,zh 允许缺 key(回退 en)。
- **组件兼容**:`useI18n` 签名不变(`locale/setLocale/t` 等),仅移除 `toggleLocale`(使用方仅 TopBar,一并替换)。
- **bundle 体积**:zh pack 从主 bundle 移出(懒加载),en-US 常驻 → 主 bundle 减小。
- **lazy 与构建**:`import()` 动态路径由 Vite 处理,`import.meta.glob` 不再需要。
