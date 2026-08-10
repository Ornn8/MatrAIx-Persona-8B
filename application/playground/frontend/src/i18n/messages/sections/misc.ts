import type { MessageBundle } from "../../types";

const messages: MessageBundle = {
  "en-US": {
    "runHeader.title": "Configure a simulation",
    "runHeader.subtitle.chatbot": "Pick personas and a chat application, then launch. Watch the simulated user converse bubble-by-bubble.",
    "runHeader.subtitle.survey": "Pick a persona and a questionnaire, then launch. A simulated user fills out the form and we score the responses.",
    "runHeader.subtitle.web": "Pick personas and a web task, then launch. The simulated user completes the site in a real browser trace.",
    "runHeader.subtitle.os-app": "Pick personas and an OS app task, then launch. Native apps on Linux, macOS, or iOS.",
    "promptPanel.empty": "Run a simulation to see the exact prompts used.",
    "promptPanel.personaPrompt": "Persona prompt",
    "promptPanel.personaPromptSublabel": "simulated-user system prompt",
    "promptPanel.taskPrompt": "Task prompt",
    "promptPanel.taskPromptSublabel": "application instruction",
    "promptPanel.emptyValue": "(empty)",
    "turnBubble.toolCallFailed": "Tool call failed",
    "turnBubble.toolCallOk": "Tool call OK",
    "structuredExposure.details": "Details",
    "structuredExposure.top": "Top",
    "misc.logoHomeAria": "MatrAIx home",
    "misc.optionalLabel": "Optional label",
  },
  "zh-CN": {
    "runHeader.title": "配置模拟任务",
    "runHeader.subtitle.chatbot": "选择数字人和聊天应用后启动，逐条观察模拟用户的对话。",
    "runHeader.subtitle.survey": "选择数字人和问卷后启动，观察模拟用户填写表单并查看回答评分。",
    "runHeader.subtitle.web": "选择数字人和网页任务后启动，观察模拟用户在真实浏览器轨迹中完成网站操作。",
    "runHeader.subtitle.os-app": "选择数字人和桌面应用任务后启动，使用 Linux、macOS 或 iOS 原生应用。",
    "promptPanel.empty": "运行一次模拟后，这里会显示实际使用的提示词。",
    "promptPanel.personaPrompt": "数字人提示词",
    "promptPanel.personaPromptSublabel": "模拟用户系统提示词",
    "promptPanel.taskPrompt": "任务提示词",
    "promptPanel.taskPromptSublabel": "应用指令",
    "promptPanel.emptyValue": "（空）",
    "turnBubble.toolCallFailed": "工具调用失败",
    "turnBubble.toolCallOk": "工具调用正常",
    "structuredExposure.details": "详情",
    "structuredExposure.top": "首选",
  "misc.logoHomeAria": "MatrAIx 首页",
  "misc.optionalLabel": "可选标签",
  },
};

export default messages;
