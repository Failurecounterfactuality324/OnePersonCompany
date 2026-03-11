# OnePersonCompany

把一人创业的日常混乱，变成可交付成果。

**OnePersonCompany** 是一个面向独立开发者/一人公司创始人的 Agent 操作系统：
你给它碎片进展，它用 LLM 生成 `每日简报`、`发版包`、`周复盘`，并自动生成可分享文案。

## 10 秒理解

- 不是聊天机器人，而是交付物引擎
- 不是通用框架，而是一人创业场景
- 不是规则拼接，而是 LLM 驱动产出

## 先配置模型（必须）

当前默认是 **LLM 强制模式**（`OPC_LLM_ENABLED=true` + `OPC_LLM_STRICT=true`）。
不配置对应 API Key 会直接报错。

### 1) OpenAI

```bash
export OPC_LLM_PROVIDER=openai
export OPENAI_API_KEY=your_key
export OPC_LLM_MODEL=gpt-4.1-mini
```

### 2) Anthropic

```bash
export OPC_LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=your_key
export OPC_LLM_MODEL=claude-3-7-sonnet-latest
```

### 3) DeepSeek

```bash
export OPC_LLM_PROVIDER=deepseek
export DEEPSEEK_API_KEY=your_key
export OPC_LLM_MODEL=deepseek-chat
```

### 4) 通义 DashScope（兼容模式）

```bash
export OPC_LLM_PROVIDER=dashscope
export DASHSCOPE_API_KEY=your_key
export OPC_LLM_MODEL=qwen-plus
```

### 5) Moonshot

```bash
export OPC_LLM_PROVIDER=moonshot
export MOONSHOT_API_KEY=your_key
export OPC_LLM_MODEL=moonshot-v1-8k
```

### 6) 智谱

```bash
export OPC_LLM_PROVIDER=zhipu
export ZHIPU_API_KEY=your_key
export OPC_LLM_MODEL=glm-4-flash
```

## 抗超时建议（推荐开启）

如果日志里出现 `ReadTimeout`，建议调大读取超时并启用重试：

```bash
export OPC_LLM_READ_TIMEOUT_SEC=90
export OPC_LLM_MAX_RETRIES=3
export OPC_LLM_RETRY_BACKOFF_SEC=2
```

### 7) 任何 OpenAI 兼容网关（自定义）

```bash
export OPC_LLM_PROVIDER=openai_compatible
export OPC_COMPAT_BASE_URL=https://your-gateway/v1
export OPC_COMPAT_API_KEY=your_key
export OPC_LLM_MODEL=your-model-name
```

## 爆款演示（推荐）

```bash
cd /Users/kaicui/PycharmProjects/OnePersonCompany
python opc.py demo day0 --lang zh
```

这条命令会自动完成：
- 初始化任务
- 生成每日简报
- 生成发版包
- 生成周复盘
- 生成一条可发朋友圈/社媒的分享文案

## 页面化使用（推荐）

启动服务后直接打开页面即可，不需要命令行操作：

```bash
uvicorn onepersoncompany.api:app --reload --host 0.0.0.0 --port 8100
```

浏览器访问：

`http://localhost:8100/`

页面内支持：
- 一键 Demo
- 30 秒无 Key 即时体验（`/demo/instant`）
- 流程生成（daily-brief / launch-pack / weekly-review）
- 任务新增与完成
- 分享文案生成
- 多平台分享素材包（X/朋友圈/小红书）
- 创始人信息登录感入口（本地缓存）
- 案例模板库一键套用
- 价值对比区块（Before/After）
- 结果卡片一键导出 PNG（适合社媒传播）

## CLI 快速开始

```bash
python opc.py init
python opc.py run daily-brief --lang zh --update "今天修了3个bug"
python opc.py run launch-pack --lang zh --update "新增邀请返利"
python opc.py run weekly-review --lang zh
python opc.py share --lang zh
python opc.py demo day0 --lang zh

python opc.py task list
python opc.py task add --title "发布本周 build-in-public" --priority 2
python opc.py task done --id <task_id>
```

## API 接口

- `GET /health`
- `GET /demo`
- `GET /public/snapshot`
- `POST /init`
- `POST /run/daily-brief`
- `POST /run/launch-pack`
- `POST /run/weekly-review`
- `GET /tasks`
- `POST /tasks`
- `POST /tasks/status`
- `POST /share`
- `POST /share/pack`
- `POST /demo/day0`
- `POST /demo/instant`

启动 API：

```bash
uvicorn onepersoncompany.api:app --reload --host 0.0.0.0 --port 8100
```

## 数据存储

默认本地 JSON：

- `data/tasks.json`
- `data/artifacts.json`

可通过环境变量改路径：

```bash
export OPC_DATA_DIR=/your/path/opc-data
```

## 调试日志

项目会自动生成日志文件用于排查问题：

- `logs/onepersoncompany.log`

日志内容包括：

- API 请求方法/路径/状态码/耗时
- LLM 初始化与调用失败原因
- CLI 命令执行与异常信息

## 安全边界

- 默认不自动对外发布
- 所有执行需要显式 CLI/API 触发
- 所有产物落地保存，支持审计与复盘

## 当前阶段定位

当前目标不是“又一个 Agent 框架”，而是：
**让独立开发者 1 分钟产出可展示成果，并愿意分享给别人看。**
