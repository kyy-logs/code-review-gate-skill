# 回归运行协议

## 固定项

- 案例输入：`SUITE.json` 中 `source_run` 对应的 repo、base/head、diff、scope、CHANGE。
- 探针：对应案例只跑 behavior-review（除非该案例明确要跑其他探针）。
- 模型：`deepseek-flash[1m]`。
- effort：`high`。
- 截止：每个探针 600 秒。
- 执行代理：不得读取历史 findings、TARGET-CHECK、REPORT 或其他轮次结果。
- 目标答案不进入执行提示。

## 每次运行必须记录

- skill tree SHA256；
- commit / dirty diff 或冻结 skill；
- 案例 ID、base、head、diff SHA256；
- 探针耗时、请求数、工具调用、输出 tokens；
- JSON 是否有效、代理是否正常返回；
- 是否触发 600 秒截止。

## 判定

- 按 `TARGET-CHECK.json` 的目标定义判断命中，不按文字相似度。
- 目标外 finding 单独记录，不直接算误报，需人工核对。
- 目标缺失、unverified 或严重级别低于验收要求，均不能算通过。
- 关键案例发布前建议 2/3 命中；单次结果只能作探索。

## 不纳入

- 为单个案例追加提示词；
- 修改历史结果来匹配预期；
- 因耗时高而跳过目标检查；
- 把模型自报的 `duration` 当作实测时间。
