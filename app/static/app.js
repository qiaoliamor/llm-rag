const $ = (id) => document.getElementById(id);
let csrf = '', busy = false;
function addMessage(role, text, pending = false) {
  const row = document.createElement('div');
  row.className = `message ${role}${pending ? ' pending' : ''}`;
  const name = document.createElement('span'); name.className = 'who'; name.textContent = role === 'user' ? '你' : '沈砚';
  const bubble = document.createElement('div'); bubble.className = 'bubble'; bubble.textContent = text;
  row.append(name, bubble); $('messages').append(row);
  $('messages').scrollTop = $('messages').scrollHeight;
  return row;
}
function error(text = '') { $('error').textContent = text; $('error').hidden = !text; }
function controls() { $('send').disabled = busy || !csrf || !$('message').value.trim(); $('reset').disabled = busy || !csrf; $('counter').textContent = `${$('message').value.length} / 2000`; }
async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf, ...options.headers } });
  const body = await response.json();
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : '输入无效，请检查消息长度后重试。');
  return body;
}
async function init() {
  try {
    const data = await api('/v1/session'); csrf = data.csrf_token;
    $('status').textContent = data.provider === 'mock' ? '● 离线演示 · 非真实模型回复' : data.configured ? '● OpenAI API · 已配置' : '○ OpenAI API · 等待本地密钥';
    $('model').textContent = data.model;
    for (const m of data.messages) addMessage(m.role, m.content);
    $('welcome').hidden = data.messages.length > 0;
    if (!data.configured) error('请在项目 .env 中填写 OPENAI_API_KEY 并重启服务。密钥仅由本地后端读取。');
  } catch { error('无法连接本地服务，请确认服务已启动，然后刷新。'); }
  controls();
}
$('chat-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const text = $('message').value.trim(); if (!text || busy || !csrf) return;
  busy = true; error(); $('welcome').hidden = true;
  const userRow = addMessage('user', text); $('message').value = ''; controls();
  const pending = addMessage('assistant', '正在想怎么回答你…', true);
  try {
    const data = await api('/v1/chat', { method: 'POST', body: JSON.stringify({message: text}) });
    pending.remove(); addMessage('assistant', data.reply);
  } catch (e) {
    pending.remove(); userRow.remove(); $('message').value = text; error(e.message);
    $('welcome').hidden = Boolean($('messages').querySelector('.message'));
  } finally { busy = false; controls(); $('message').focus(); }
});
$('message').addEventListener('input', controls);
$('message').addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); $('chat-form').requestSubmit(); }
});
for (const b of document.querySelectorAll('.suggestions button')) b.addEventListener('click', () => { if (!busy) { $('message').value = b.textContent; controls(); $('message').focus(); } });
$('reset').addEventListener('click', () => $('reset-dialog').showModal());
$('cancel-reset').addEventListener('click', () => $('reset-dialog').close());
$('confirm-reset').addEventListener('click', async () => {
  $('confirm-reset').disabled = true;
  try {
    await api('/v1/session', {method:'DELETE'});
    document.querySelectorAll('.message').forEach(e => e.remove());
    $('welcome').hidden = false; $('message').value = ''; error(); controls();
  } catch (e) { error(e.message); }
  finally { $('reset-dialog').close(); $('confirm-reset').disabled = false; }
});
init();
