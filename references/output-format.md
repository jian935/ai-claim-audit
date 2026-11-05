# Output Format

Produce **one audit table**, then a short "what to ask for" list, then a
rewrite, then limitations. Never open with a verdict paragraph — the table is
the product.

## Template

```markdown
# 效果声明审计 · <document name>

扫描 N 条声明，其中 M 条缺证据；S1 × a / S2 × b / S3 × c。

| # | 原文声明 | 命中检查 | 严重度 | 缺什么 | 需要对方补的证据 |
|---|---|---|---|---|---|
| Q01 | 「准确率达到 94%」 | C01, C10 | S2 | 分母、复现路径 | 评测集条数与来源、跑分脚本路径、数据版本 |
| Q02 | 「…」 | C02 | S1 | 目标集定义 | 正例是否由外部字段（岗位名）而非正文关键词定义 |

## 需要补的输入（不要替对方编）
- [ ] Q01：评测集条数 n、正例定义、数据版本
- [ ] Q02：目标集构造规则、标注来源字段名

## 改写（只能变弱，不能变强）
- 原文：「准确率达到 94%，模型已可用。」
- 改写：「在 <待补：n 条、来源、口径> 上测得 94%；该结果尚不能推广到线上流量。」

## 本次审计的局限
- 机器预检只覆盖字面措辞，看不到数据集、标签来源与代码里的口径定义。
- C02/C03/C04/C07/C08/C11 由模型依据本文件与 failure-patterns.md 裁决，
  裁决依据是对方提供的材料；材料不足时标注「无法判断」，不标「通过」。
- 未命中的检查不等于通过；本审计不验证任何数字的真伪。
```

## Rules for filling the table

- **One row per claim.** Split multi-claim sentences; never merge two claims
  into one row to make the table shorter.
- **Quote the original fragment verbatim.** Paraphrasing hides the problem.
- **Severity = the highest severity among the raised checks** (S1 > S2 > S3).
  Never average, never add.
- **"缺什么" names a concrete artifact**, not a feeling:
  `评测集条数`、`留出集划分规则`、`正例外字段定义`、`口径枚举唯一源`、
  `重跑命令`。Avoid "缺少论证".
- **Every S1 gets a rebuild instruction**, not a caveat. A self-confirming
  target set cannot be rescued by adding a footnote.
- **Compliant claims still get a row** with `命中检查 = —` and a one-line note
  on what evidence made them pass. This is what makes the audit falsifiable:
  the reader can check the same standard was applied to good and bad claims.

## Writing the closing limitation section

State plainly that a clean pre-check is not evidence a claim is true, that
semantic checks depend on material the user supplied, and that the audit does
not verify any number. This section is mandatory; an audit without it is exactly
the kind of unqualified claim this skill exists to catch.
