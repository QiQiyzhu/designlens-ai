# DeepSeek 接入与真实调用记录

DesignLens 使用服务端 DeepSeek Chat Completions HTTP 适配。默认仍是零远程调用的 `extractive` 模式；设置 `DESIGNLENS_PROVIDER=deepseek` 后，应用的生成及工作流节点会发出真实模型请求。API Key 不进入前端、仓库或模型提示词。真实研究与合成示例的标签不会因为接通模型而改变。

## 配置

2026-09-10 核对官方中文文档：[首次调用](https://api-docs.deepseek.com/zh-cn/)、[思考模式](https://api-docs.deepseek.com/zh-cn/guides/thinking_mode/)、[JSON Output](https://api-docs.deepseek.com/zh-cn/guides/json_mode/)。当前示例使用 `deepseek-flash`，地址为 `https://api.deepseek.com`。实际响应模型名会单独保存；服务商模型别名可能迁移，不能将请求别名当成永久固定权重。

在仓库根目录的 PowerShell 配置。密钥通过隐藏输入读取，不要将它写入命令字面量、提交文件或聊天：

```powershell
$deepSeekSecret = Read-Host 'DeepSeek API Key' -AsSecureString
$deepSeekPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($deepSeekSecret)
try {
    $env:DEEPSEEK_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($deepSeekPointer)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($deepSeekPointer)
    Remove-Variable deepSeekSecret, deepSeekPointer
}
$env:DESIGNLENS_PROVIDER = 'deepseek'
$env:DESIGNLENS_API_BASE = 'https://api.deepseek.com'
$env:DESIGNLENS_MODEL = 'deepseek-flash'
$env:DESIGNLENS_MAX_OUTPUT_TOKENS = '768'
$env:DESIGNLENS_TIMEOUT_SECONDS = '30'
```

`DESIGNLENS_API_KEY` 若设置会覆盖公共的 `DEEPSEEK_API_KEY`。环境文件不会自动加载。变量仅属于当前进程及其子进程；完成后可以 `Remove-Item Env:DEEPSEEK_API_KEY`，并将 `DESIGNLENS_PROVIDER` 改回 `extractive`。

## 先预检，再明确执行

```powershell
.\.venv\Scripts\python.exe -m scripts.real_model_smoke --output outputs/deepseek-preflight.json
.\.venv\Scripts\python.exe -m scripts.real_model_smoke --execute --max-calls 3 --output outputs/deepseek-smoke.json
```

第一条命令只校验配置，**零网络调用**，正常状态为 `ready_not_executed`。第二条最多三次可能计费的请求，依次运行仓库里的 `citation`、`irrelevant`、`instruction-data` 合成开发夹具；可以改成 `--max-calls 1` 或 `2`。每个案例只有一次调用，没有自动重试；HTTP/协议失败停止剩余请求。有效模型输出但自动检查失败会保留结果并让命令退出 1；配置或传输失败退出 2。

探针的 1–3 次限制属于此脚本。交互应用不具有全局三次额度限制；每次点击生成都会请求一次，演示前应在服务商控制台设置预算/限额。它也不自动保存 API Key。

## 实际请求边界

适配器发送 `stream=false`、`max_tokens=768`、`thinking={"type":"disabled"}`。DeepSeek 默认开启思考，因此这里显式关闭，控制小规模证据摘录的输出预算。代码直接发送 HTTP JSON，使用服务端参数 `thinking`，没有发送 Qwen 的 `enable_thinking` 或 SDK 的 `extra_body`。结构化模式设置 `response_format={"type":"json_object"}`，同时在 system 消息要求 JSON 与输出 schema；返回后还需经过应用的格式和精确引用校验。

DeepSeek 配置仅允许其官方 HTTPS 主机及 `/v1` 别名，禁止重定向；请求上限 64 KiB，响应读取上限 1 MiB；连接超时 5 秒，其余 HTTP 操作超时默认 30 秒、可配置 5–60 秒。HTTPX 的分阶段超时不是整段执行的硬性墙钟截止。`length`、拒答、工具调用、空输出、非 JSON、429 和网络错误均显式失败；不会偷偷回退到 extractive 并显示模型成功。原始错误响应不写入报告。

默认只向远程发送明确标记 `is_demo=true` 的来源。真实研究保持本机，需独立确认研究授权和服务商数据处理条件后，才可以由本地所有者显式设置 `DESIGNLENS_ALLOW_REAL_REMOTE=1`。接通模型不构成真实研究数据的自动发送授权。

## 什么证据才可以写入作品集

探针保存执行 commit、实际工作树文件字节 SHA256、数据集和提示词 SHA256、实际请求次数、请求/响应摘要、状态码、请求 ID、请求模型和响应模型、耗时、服务商返回的 token 用量及逐案例输出。缓存命中/未命中 token 只在服务商返回时保留；`cost_usd=null`，因为脚本没有拿到账单，不用估算替代真实扣费。

本次适配验证的 [63 项后端测试](../reports/remote-provider-tests.xml) 包括原有 44 项与 19 项远程适配/探针检查；适配检查使用 MockTransport，没有付费模型调用。原有 [48 次确定性夹具结果](../reports/evaluation.md) 继续保留 extractive 来源，不改成 DeepSeek 跑分。真实探针结果应单独保存、审核后再公开；在有实际回执前，真实 LLM 的质量、延迟和 token 结果均待验证。

即使三例全部通过，也只证明这三条开发夹具的格式、原文引用及预期行为检查通过。它不能证明语义理解、注入防护完整性、独立测试集泛化或真实产品价值。人工评分保持 pending，真实参与者与有效产品决策保持 0。
