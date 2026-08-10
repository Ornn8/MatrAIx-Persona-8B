<div align="center">
  <h1>MatrAIx</h1>
  <p><strong>先模拟,再落地。</strong></p>
  <p>
    面向 AI 系统与交互产品评估的人口规模级、persona 驱动基础设施,
    用异质的模拟用户进行评测。
  </p>
  <p>
    <a href="https://matraix.ai/"><img alt="Website" src="https://img.shields.io/badge/Website-matraix.ai-4f7cff?style=for-the-badge"></a>
    <a href="https://discord.gg/knVyQQnRFa"><img alt="Discord" src="https://img.shields.io/badge/Discord-join%20MatrAIx-5865F2?style=for-the-badge&logo=discord&logoColor=white"></a>
    <a href="https://x.com/MatrAIx2026"><img alt="X" src="https://img.shields.io/badge/X-%40MatrAIx2026-000000?style=for-the-badge&logo=x&logoColor=white"></a>
    <a href="https://www.linkedin.com/company/matraix"><img alt="LinkedIn" src="https://img.shields.io/badge/LinkedIn-MatrAIx-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white"></a>
    <a href="https://forms.gle/hwEHng5HGWRqcJue9"><img alt="Google Form" src="https://img.shields.io/badge/Google%20Form-join%20MatrAIx-4285F4?style=for-the-badge&logo=googleforms&logoColor=white"></a>
    <a href="docs/README.md"><img alt="Docs" src="https://img.shields.io/badge/Docs-Handbook-5b5b5b?style=for-the-badge"></a>
    <a href="https://huggingface.co/datasets/MatrAIx2026/MatrAIx_Persona_1M_Public_Release"><img alt="Hugging Face" src="https://img.shields.io/badge/Hugging%20Face-Persona%201M-ffcc4d?style=for-the-badge"></a>
    <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/License-MIT-c33b32?style=for-the-badge"></a>
    <a href="docs/quickstart.md#10-playground--play-tasks-visually"><img alt="Playground" src="https://img.shields.io/badge/Playground-Visual%20Runner-56b879?style=for-the-badge"></a>
  </p>
  <p>
    [<a href="README.md">English</a>] · [<strong>中文</strong>]
  </p>
</div>

---

**MatrAIx** 是一套人口规模级、persona 驱动的 AI 评测基础设施:不是用一个"通用用户"来测试,而是把采样得到的 persona 记录实例化为 LLM 智能体,让它们在**问卷(Survey)、AI 聊天机器人(Chatbot)、Web、原生应用(App,含 macOS/iOS)** 四种环境中执行可复现的任务。

核心是一份共享的 **1,290 维分类 schema**,覆盖背景、心理、能力与行为。Persona 同时来自依赖感知的合成生成与证据感知的真实数据落地;一个确定性、质量过滤的 **百万 persona 核心集**已发布到 [Hugging Face](https://huggingface.co/datasets/MatrAIx2026/MatrAIx_Persona_1M_Public_Release) 供研究使用。共享遥测、任务自有验证与报告把个体回答与轨迹汇聚为子群体和群体层面的结论。

名称致敬 *The Matrix*:一个用于探索、压力测试与假设生成的模拟世界,**不能替代来自真实人群的证据**。

## 中国 persona 管线(新增)

一条把 persona 落地到真实受访者的数据管线,不再只依赖合成:

- **数据源**:CGSS 2017(12,582 位受访者)、CGSS 2021(8,148 位)与 WVS Wave-7 中国样本(3,036 位),通过声明式 crosswalk(`persona/curation/existing_data/scripts/crosswalks/`)映射到 1,290 维 schema,校验 0 错误。
- **Persona 池**:`persona/datasets/cgss2017-llm/`(200 人,LLM 富化,人均约 105 维,带证据引证)与 `persona/datasets/wvs-cn/`(3,036 人)。每个池带独立的 `source` 标记与 manifest,中国 cohort 绝不混入通用池。
- **消费画像**:每个 `cgss2017-llm` persona 附带 10 字段消费行为画像——付费意愿、价格锚点、价格敏感度、付费模式偏好、推广接受度、信任的渠道、消费风格、决策因素、品牌忠诚度、付费理由——用于模拟定价/推广/产品反馈研究。画像仅在市场研究场景**显式请求**时渲染。
- **中文渲染**:设置 `MATRAIX_PERSONA_LANGUAGE=zh` 即可让 persona 叙事以中文渲染(1,290/1,290 维已翻译;默认英文且与原来逐字节一致)。

详见[交付总览](docs/persona/delivery-map.md)与[消费画像字段说明](docs/persona/consumer-profile-fields.md)。

## 环境要求

- [Docker](https://docs.docker.com/get-docker/)
- [uv](https://docs.astral.sh/uv/) 与 Python 3.12
- Node.js 20+(仅 Playground / viewer 前端)
- persona-agent 示例所需的模型 API key — 见 [agents.md](docs/environment/agents.md)

## 安装

```bash
git clone <repo-url> && cd MatrAIx
uv venv --python 3.12
uv pip install -e .
uv pip install pytest pytest-asyncio httpx
uv pip install -e packages/playground
uv pip install -e packages/harbor-langsmith
uv pip install -e packages/rewardkit
uv pip install -e environment/adapters/simpleqa
```

所有 Matraix Playground 命令以 **`uv run harbor …`** 运行。

GUI 或 CLI 任务运行前,按你的 provider 配置模型 API key(smoke test 不需要):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # anthropic/claude-* 模型
# export OPENAI_API_KEY="sk-..."        # openai/gpt-* 模型
```

完整 key 对照见 [agents.md](docs/environment/agents.md)。Playground 也可以从 `application/playground/.env.local` 读取 key。

### 导入 Persona 1M(可选)

```bash
huggingface-cli download MatrAIx2026/MatrAIx_Persona_1M_Public_Release \
  --repo-type dataset \
  --local-dir persona/datasets/matraix-persona-1m/release
```

Playground:Dataset → **`matraix-persona-1m`**。CLI:`--dataset persona/datasets/matraix-persona-1m`。
详见 [Handbook § Persona 1M](docs/README.md#3-persona-1m-optional)。

## 快速开始

### Smoke test

无需 API key:

```bash
uv run harbor run -c configs/jobs/example-job-recipe/harbor-smoke-local.yaml
```

### GUI 任务运行

Playground 选择任务、采样 persona,并启动与 CLI auto 模式相同的 Matraix Playground 任务。启动 API + 前端(两个终端):

```bash
# 终端 A — API
VENV=.venv bash application/playground/backend/run_dev.sh

# 终端 B — 前端
cd application/playground/frontend && npm ci && npm run dev
```

打开 **http://localhost:5173** → Playground → 选择 persona cohort →
选择 Survey / Chat / Web / OS app 任务 → **Lock pipeline** → **Run eval**。
详见 [Playground §10](docs/quickstart.md#10-playground--play-tasks-visually)。

### CLI 任务开发 / 运行

**开发** — 复制 `application/tasks/` 下的参考任务,编辑 `task.toml` / `instruction.md` / `input/` / verifier,然后在 Playground 中注册([task-guide.md](docs/application/task-guide.md)):

```bash
# 用输出的 export 行 + recipe 路径运行,例如:
uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-chat-local.yaml
```

## 文档

**[MatrAIx Handbook](docs/README.md)** — 指南、persona / application / environment 文档。

- **[中国 persona 管线](docs/persona/delivery-map.md)** — 真实数据 CGSS/WVS 管线、persona 池、消费画像。
- **[中文渲染](docs/persona/zh-rendering.md)** — `MATRAIX_PERSONA_LANGUAGE=zh` 语言开关。

<p align="center">
  <img src="docs/assets/matraix-architecture.png" alt="MatrAIx 架构" width="900">
</p>

## 仓库结构

```text
MatrAIx/
├── persona/                 Schema、数据集、synthesis/curation/validation 管线
│   ├── schema/              1,290 维 persona schema
│   ├── datasets/            开发样本池、CGSS/WVS 中国池、persona YAML
│   ├── curation/            现有数据 crosswalk(CGSS/WVS)+ LLM 富化
│   ├── validation/          落地/质量校验套件
│   └── scripts/             persona 任务与管线辅助脚本
├── application/
│   ├── tasks/               Survey · chat · web · os-app 任务规格
│   ├── task-spec/           共享任务契约
│   ├── playground/          可视化运行器(后端 API + 前端)
│   └── scripts/             generate_application_job.py 与任务工具
├── environment/
│   ├── runtime/             Matraix Playground 运行时
│   ├── agents/              Persona 条件化智能体
│   ├── task-environments/   Docker 镜像 / sidecar
│   └── adapters/            外部适配器(如 SimpleQA)
├── packages/                playground · rewardkit · harbor-langsmith
├── apps/viewer/             与 `harbor view` 配对的前端
├── configs/jobs/            精选与生成的 Matraix Playground 任务 recipe
├── docs/                    Handbook — persona/ · application/ · environment/
├── examples/                最小示例任务
├── src/matraix/             Python 包入口
├── scripts/                 仓库级辅助脚本
├── tests/                   单元 / 环境测试
└── jobs/                    本地 Matraix Playground 运行输出(gitignored)
```

大型生成数据集不入库(见上方 Hugging Face 发布)。

## 加入社区

[![Discord](https://img.shields.io/badge/Discord-join%20MatrAIx-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/knVyQQnRFa)
[![X](https://img.shields.io/badge/X-follow%20%40MatrAIx2026-000000?style=for-the-badge&logo=x&logoColor=white)](https://x.com/MatrAIx2026)

[![LinkedIn](https://img.shields.io/badge/LinkedIn-follow%20MatrAIx-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/company/matraix)
[![Google Form](https://img.shields.io/badge/Google%20Form-join%20MatrAIx-4285F4?style=for-the-badge&logo=googleforms&logoColor=white)](https://forms.gle/hwEHng5HGWRqcJue9)

1. 加入 Discord,昵称格式 **`姓名 - 单位`**。填写 Google Form(背景、兴趣、论文署名 / 致谢)。
2. 与我们打个招呼!我们乐于因共同的兴趣或经历与你连接。
3. 参与 MatrAIx 研究社区,协作或贡献!

## 许可

MIT — 见 [LICENSE](LICENSE)。

## 致谢

- **中国综合社会调查(CGSS)** — 中国 persona 管线将 CGSS 2017 / 2021 的题目(中国人民大学,经 [CNSDA](https://www.cnsda.org/) 发布)映射到 persona schema。CGSS 数据按 CNSDA 注册条款仅限学术使用;本仓库中的衍生 persona 数据仅提供研究用途,不得用于商业再分发。
- **世界价值观调查(WVS)Wave 7** — 通过 [WVSA](https://www.worldvaluessurvey.org/) 映射的中国 2018 年样本,按公开跨国数据的 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 条款使用。
- **Inter 字体** — 按 [SIL Open Font License 1.1](https://openfontlicense.org) 随附。
