import { t } from '../i18n';
import type { GrowthAccount } from '../types';

const tiers=[{score:0,name:'初识'},{score:30,name:'渐熟'},{score:60,name:'默契'},{score:90,name:'知心'}];
export function BondProgress({ account }: { account?: GrowthAccount | null }) {
  const score=account?.character.score ?? 0;
  const next=tiers.find(tier=>score<tier.score);
  const current=[...tiers].reverse().find(tier=>score>=tier.score) ?? tiers[0];
  return <section className="bond-progress" aria-label={t("亲密度成长")}>
    <div className="bond-heading"><span>{t("和{1}的相处进度", [t(account?.character.name ?? '沈砚')])}</span><strong>{score}<small> / 100</small></strong></div>
    <progress aria-label={t("亲密度")} value={score} max={100} />
    <div className="ability-steps">{tiers.map(tier=><span key={tier.score} className={score>=tier.score?'unlocked':''} aria-current={current.score===tier.score?'step':undefined}>{tier.score} · {t(tier.name)}</span>)}</div>
    <p>{t("现在是{1}。", [t(current.name)])}{next?t("距离{1}还有 {2} 分。", [t(next.name), next.score-score]):t("慢慢相处的每一天，都可以继续聊。")}</p>
  </section>;
}
