"""Offline authored claim-support audit. Never reads .env or calls an API/DB."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.fact_support_evaluation import evaluate


def markdown(report):
    s=report['summary'];p=s['policy_confusion'];m=s['semantic_confusion']
    lines=['# 完整事实支持开发集审计','',
           '这是固定合成参考标注与现有规则的对比；不是自动语义裁判、独立盲评或模型生成质量评分。','',
           f"数据版本：{report['dataset_version']}；SHA256：`{report['dataset_sha256']}`。",'',
           '| 项目 | 计数 |','| --- | --- |',
           f"| 回复 / 事实断言 | {s['responses']} / {s['factual_claims']} |",
           f"| 支持 / 缺依据 / 矛盾 / 未决 | {s['claim_verdicts'].get('supported',0)} / {s['claim_verdicts'].get('unsupported',0)} / {s['claim_verdicts'].get('contradicted',0)} / {s['claim_verdicts'].get('unresolved',0)} |",
           f"| 纯非事实回复（不计事实支持分母） | {s['nonfactual_only_responses']} |",
           f"| 回答义务引用覆盖 | {s['obligation_hits']} / {s['obligations']} |",
           f"| 综合策略 TP / FP / FN / TN | {p['tp']} / {p['fp']} / {p['fn']} / {p['tn']} |",
           f"| 仅语义 TP / FP / FN / TN | {m['tp']} / {m['fp']} / {m['fn']} / {m['tn']} |",
           f"| 未决不入混淆矩阵 | {p['unresolved_excluded']} |",'',
           'TP=有问题且拦截；FP=无问题却拦截；FN=有问题却漏检；TN=无问题且放行。完整专名策略与语义支持分开，详见每条标注。','',
           '| 类别 | 回复 | 策略漏检 | 策略误拦截 | 未决排除 |',
           '| --- | --- | --- | --- | --- |']
    for name,stats in report['categories'].items():
        q=stats['policy_confusion'];lines.append(f"| {name} | {stats['responses']} | {q['fn']} | {q['fp']} | {q['unresolved_excluded']} |")
    lines+=['','## 发现清单','', '| ID | 类型 | 回复 | 判据 |','| --- | --- | --- | --- |']
    for row in report['findings']:
        reasons=[c['rationale'] for c in row['claims'] if c['verdict'] in ('unsupported','contradicted','unresolved')]
        if not reasons:reasons=[c['rationale'] for c in row['claims']]
        clean=lambda v:v.replace('|','\\|').replace('\n',' ')
        lines.append('| '+' | '.join(map(clean,[row['id'],row['finding'],row['reply'],'；'.join(reasons)]))+' |')
    lines+=['','## 限制','']+['- '+x for x in report['limits']]
    return '\n'.join(lines)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--format',choices=('json','markdown'),default='json')
    parser.add_argument('--fail-on-findings',action='store_true',help='Exit 1 on known misses, overblocks, or unresolved labels; default audits without declaring quality passed')
    args=parser.parse_args()
    try:report=evaluate()
    except Exception:
        print('参考数据或评测无效；未生成有效审计结果。',file=sys.stderr)
        return 2
    for cmd,key in [(['git','rev-parse','HEAD'],'code_revision'),(['git','status','--porcelain'],'working_tree_dirty')]:
        result=subprocess.run(cmd,cwd=Path(__file__).resolve().parent.parent,capture_output=True,text=True)
        report[key]=(bool(result.stdout.strip()) if key=='working_tree_dirty' else result.stdout.strip()) if result.returncode==0 else None
    print(markdown(report) if args.format=='markdown' else json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False))
    return int(args.fail_on_findings and bool(report['findings']))


if __name__=='__main__':
    raise SystemExit(main())
