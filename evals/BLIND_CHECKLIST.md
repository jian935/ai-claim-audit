# 盲评分步清单（照着做，约 5 分钟）

> **这份清单只做一件事**：把**另一个模型**的 40 个答案，变成一张可复现、带 Wilson 区间的分数表。
> 清单本身不产生任何分数，分数来自 `--predictions`。
> 本仓库首屏的 **0.800 / 0.842 是确定性基线，不是模型分数**。
>
> **红线**：不要在写金标的同一个会话里跑模型；不要把金标当预测喂回去当准确率发布。

---

## 开始前

- [ ] 本机有 Python 3.10+，当前目录是仓库根目录
- [ ] 已理解上面那句红线（原因见 [`BLIND_EVAL.md`](BLIND_EVAL.md)）

## 第 1 步 · 准备题目（10 秒）

```bash
python scripts/eval_extras.py --make-blind-pack
python scripts/eval_extras.py --make-template
python scripts/eval_extras.py --self-test      # 顺带验题目包没有泄漏金标
```

生成 `evals/blind_pack.md`（不含任何答案）与 `evals/predictions_template.json`（40 个 `null`）。
**不要手改这两个文件**——CI 会重生成并 diff。

## 第 2 步 · 换一个模型（关键步骤）

打开**另一个模型**（不同厂商或不同版本更好），把下面三份内容整份贴给它：

1. `evals/blind_pack.md`
2. `references/audit-rubric.md`
3. `SKILL.md` 的 `When to use` / `When not to use` 两节

末尾附上这段提示词（可直接复制）：

```
只依据上面三份材料作答，不要打开或搜索本仓库的其它文件（那些文件含答案）。
Task A：对 S01–S20 每个编号，给出它违反了哪几项 C02/C03/C04/C07/C08/C11；
        无命中写 []，不要写 null。
Task B：对 T01–T20 每个编号，给出 true 或 false。
只输出一个 JSON 对象，不要任何解释、前言、结论或第二个 JSON：
{"semantic": {"S01": [], ... 共 20 个}, "trigger": {"T01": false, ... 共 20 个}}
40 个 id 一个不少，顺序不限。
```

- [ ] 该模型**没有**读过 `evals/semantic.json`、`evals/trigger.json`、两份 RESULTS 或任何 README 分数段
- [ ] 回复里 40 个 id 齐全

## 第 3 步 · 保存原始回复

把模型的**整段回复**原样存成 `evals/raw_reply.txt`（带 ```json 围栏、带解释文字都没关系）。

该文件已 gitignore，不会误提交。**不要手改答案**：缺题就让它重答，不要自己补一个看起来合理的值。

## 第 4 步 · 清洗 + 严格校验（一条命令）

```bash
python scripts/extract_predictions.py --raw evals/raw_reply.txt
```

成功时写出 `evals/my_predictions.json`（同样已 gitignore），并打印：

```
validated: 20 semantic + 20 trigger answers
  semantic: N check hits, M cases with no check
  trigger: X should-trigger / Y should-not-trigger
```

失败时直接告诉你是哪几题没答、哪个 id 非法、哪个值不是 bool，**不会**生成半份答案文件。
`[]` 是合法的「无命中」，`false` 是合法的「不触发」，`null` 一律视为未作答。

## 第 5 步 · 打分

```bash
python scripts/eval_extras.py --suite all --predictions evals/my_predictions.json
python scripts/eval_extras.py --suite all --predictions evals/my_predictions.json \
  --out evals/MODEL_RESULTS.md
```

验收：

- [ ] 输出里 `source` 是 `external (my_predictions.json)`，**不是** `deterministic baseline`
- [ ] 精确率 / 召回 / F1 / 95% 区间 / 误报同屏，没有只报好看的那一半
- [ ] 基线行 **0.800 / 0.842 保留**，模型分数用来和它比，不是替代它
- [ ] `evals/RESULTS.md` 与 `evals/EXTRAS_RESULTS.md` 没有被这次运行改动（模型分数是另存，不覆盖 golden）

---

## 常见失败

| 现象 | 原因 | 处理 |
|---|---|---|
| `no JSON object with a 'semantic'/'trigger' key found` | 只复制了模型的一句话总结，或回复被截断 | 把**整段**回复存进 raw 文件；必要时让它重发 |
| `is missing N id(s)` | 模型漏题 | 让它补答缺的编号，不要自己填 |
| `unanswered (null) id(s)` | 模型用 `null` 占位 | 同上；打分器故意拒绝，防止半份答案跑出合法分数 |
| `unknown check id(s) ['C99']` | 模型自己造了检查项 | 提醒它只能用 C02/C03/C04/C07/C08/C11 |
| `trigger answer must be true/false` | 模型写了 `"maybe"` / 中文 | 让它改成布尔值 |
| `missing suite(s): trigger` | 模型把 Task A / Task B 拆成了两个 JSON 对象 | 让它合并成**一个**含 `semantic` + `trigger` 的对象后重发 |
| `unknown id(s)` | 多写了 S99 之类 | 删掉多余编号后重跑 |
| 新会话里题目包和模板对不上 | 评测集改过但没重生成 | 回到第 1 步重跑两条生成命令（CI 也会拦） |

## 必须随分数一起记录

没有这些元数据，分数**不要**写进 README：

| 项 | 值 |
|---|---|
| 模型名与版本 | |
| 运行日期 | |
| temperature / 其它采样参数 | |
| 是否看过任何金标 | 否（否则作废） |
| 是否有网络访问 | |
| 是否重复跑过、同文不同答的波动 | |
| predictions 文件是否留存 | |

## 写回 README 的规矩

- 中英两版同步；`scripts/check_docs.py` 的 `TOKENS` 加新数字，`MEASURED_EXTRAS` 要指向真实生成的结果文件。
- 必须标注「**一次可复现的非独立盲评**」：金标、rubric、题目措辞都出自同一仓库；每套仅 20 条，Wilson 区间很宽。
- 基线行保留；精确率、召回、误报同屏。
- 完整方法论与局限见 [`BLIND_EVAL.md`](BLIND_EVAL.md)。

## 最后一条红线

把金标当预测喂回打分器会得到 **1.000**——那只是打分器自检，不是准确率。
也不要因为分数不好看就回头改那 8 类已知规则缺陷：在给 v1.0.0 打分的同一批案例上改规则，等于把评测变成调参记录。
