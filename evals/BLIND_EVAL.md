# 盲评操作说明：换模型跑出真实的语义裁决 / 触发精度分数

`evals/EXTRAS_RESULTS.md` 里的 0.800 / 0.842 是**确定性基线**，不是模型分数。
这份说明用来产出后者，并且不把它做成自证。

## 为什么必须换模型、且必须盲

金标是本仓库作者写的。如果再由同一个会话的模型按同一份 rubric 裁决，
等于「自己出题、自己判卷」，分数会虚高且不可证伪。因此题目包不含任何答案，
作答模型不许看金标文件、结果表，也不许看 README 里的分数段落。

## 四个文件

| 文件 | 生成方式 | 含答案 | 是否提交 |
|---|---|---|---|
| `evals/blind_pack.md` | `--make-blind-pack` | **无** | 是，CI 会重生成校验 |
| `evals/predictions_template.json` | `--make-template` | 全 `null` | 是，CI 会重生成校验 |
| `evals/my_predictions.json` | 复制模板后填写 | 有 | **否**，已 gitignore |
| `evals/EXTRAS_RESULTS.md` | `--suite all` | 基线分数 | 是 |

## 步骤

1. 重新生成题目包（评测集改过就必须重做，CI 也会检查）：

   ```bash
   python scripts/eval_extras.py --make-blind-pack
   python scripts/eval_extras.py --make-template
   ```

2. 复制模板，答案文件不要提交：

   ```bash
   cp evals/predictions_template.json evals/my_predictions.json
   ```

3. 把 `evals/blind_pack.md` 连同 `references/audit-rubric.md`，以及 `SKILL.md` 的
   When-to-use / When-not-to-use 两节，发给**另一个模型**（不同厂商或不同版本更好）。
   明确要求：只输出一个 JSON，40 个 id 一个不少；不要打开仓库里的其它文件。

4. 把回答写进 `evals/my_predictions.json`：

   - `semantic`：每个 id 对应一个检查项数组，如 `["C02", "C04"]`；**无命中写 `[]`**，这是合法答案。
   - `trigger`：每个 id 对应 `true` / `false`。
   - `null` 表示**未作答**，打分器会直接拒绝运行。这是故意的：防止空模板跑出一个看似合法的分数。

5. 跑分：

   ```bash
   python scripts/eval_extras.py --suite all --predictions evals/my_predictions.json
   python scripts/eval_extras.py --suite all --predictions evals/my_predictions.json \
     --out evals/MODEL_RESULTS.md
   ```

   输出里 `source` 会显示 `external (my_predictions.json)`，而不是 `deterministic baseline`。

## 必须随分数一起记录

模型名与版本、运行日期、temperature、是否看过任何金标、是否有网络访问、
是否重复跑过（同文不同答要报波动）。没有这些元数据的分数不要写进 README。

## 写回 README 的规矩

- 中英两版同步；`scripts/check_docs.py` 的 `TOKENS` 加新数字，`MEASURED_EXTRAS`
  要指向真实生成的结果文件，不能只检查 token 存在。
- 明确标注「一次可复现的非独立评测」：金标由同一作者编写，每套 20 条样本，
  Wilson 区间很宽。精确率、召回、误报必须同屏，不要只报好看的那一半。
- 基线行保留，别删。模型分数用来和基线比，不是替代它。
- 不要手改 `blind_pack.md` / `predictions_template.json`：CI 会重生成并 diff，
  手改会让 PR 变红。

## 局限

即使换了模型，这也不是第三方独立基准：金标、rubric、题目措辞都出自同一仓库；
模型可能已在训练数据里见过公开仓库；20 条样本下几个点的差异没有统计意义。
把它写成「一次可复现的非独立盲评」，不要写成「准确率」。
