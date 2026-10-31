import type { Character } from '../types';

export function Sidebar({ character }: { character?: Character }) {
  return (
    <aside className="sidebar">
      <a className="brand" href="/">心语<span>PERSONA / 01</span></a>
      <div className="portrait" role="img" aria-label="栖川旧书店的窗与书架插画">
        <div className="moon" /><div className="window" />
        <div className="books">{Array.from({ length: 5 }, (_, i) => <i key={i} />)}</div>
        <span>栖川 · 旧书店</span>
      </div>
      <div className="profile">
        <p className="eyebrow">YOUR COMPANION</p>
        <h1>{character?.name ?? '沈砚'}<span>SHEN YAN</span></h1>
        <p>{character?.subtitle ?? '听你说，也陪你慢慢想。'}</p>
        <div className="tags"><span>温和沉稳</span><span>旧书修补者</span><span>28 岁</span></div>
      </div>
      <div className="note">
        <span>关于他</span>
        <p>三年前，在栖川开了一家旧书店。喜欢修补旧书，也收集读者留在书页间的便签。</p>
        <p>“有些话，不必急着说完。”</p>
      </div>
      <div className="sidebar-bottom">
        <span className="dot" /> 单角色对话原型 · M2
        <p>聊天临时保留；开启并确认的记忆保存在本机，可跨新对话引用。通过“长期记忆”管理，通过“计划与进度”查看任务。</p>
      </div>
    </aside>
  );
}
