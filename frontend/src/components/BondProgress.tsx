import type { GrowthAccount } from '../types';

const labels = { memory: '长期记忆', emotion: '情绪关怀', weather: '天气关怀' };
export function BondProgress({ account }: { account?: GrowthAccount | null }) {
  const score=account?.character.score ?? 0;
  const next=Object.entries(account?.thresholds ?? {memory:30,emotion:60,weather:90}).find(([,value])=>score<value);
  return <section className="bond-progress" aria-label="亲密度成长">
    <div className="bond-heading"><span>和{account?.character.name ?? '沈砚'}的相处进度</span><strong>{score}<small> / 100</small></strong></div>
    <progress aria-label="亲密度" value={score} max={100} />
    <div className="ability-steps">{Object.entries(account?.thresholds ?? {memory:30,emotion:60,weather:90}).map(([key,value])=><span key={key} className={score>=value?'unlocked':''}>{score>=value?'✓':'○'} {value} · {labels[key as keyof typeof labels]}</span>)}</div>
    <p>{next?`再相处 ${next[1]-score} 分，可解锁${labels[next[0] as keyof typeof labels]}。`:'三项能力均已解锁，可在个人账户中决定是否授权。'} 持续聊天也能免费成长。</p>
  </section>;
}
