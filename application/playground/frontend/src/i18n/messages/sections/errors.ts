import type { MessageBundle } from "../../types";

const messages: MessageBundle = {
  "en-US": {
    "errorBoundary.title": "Something went wrong",
    "errorBoundary.description": "Playground hit an unexpected error and stopped rendering. Your data is safe. You can recover the view or reload the app.",
    "errorBoundary.tryAgain": "Try again",
    "errorBoundary.reload": "Reload",
  },
  "zh-CN": {
    "errorBoundary.title": "出现了问题",
    "errorBoundary.description": "工作台遇到意外错误，已停止渲染。你的数据是安全的，可以尝试恢复视图或重新加载应用。",
    "errorBoundary.tryAgain": "重试",
    "errorBoundary.reload": "重新加载",
  },
};

export default messages;
