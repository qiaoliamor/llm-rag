"""Synthetic scripted verdict contracts; never measured semantic accuracy."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import ValidationError

from app.config import Settings
from app.dialogue import conflicts
from app.memory_source import source_time_conflicts
from app.grounding import place_conflicts
from app.reply_pipeline import generate_checked
from app.semantic_review import evidence_bundle, review_reply
from app import fact_presentation as f

MEMORIES=[{'id':'synthetic','fact':'合成桜ヶ丘市に住んでいます。','event_date':'2026-11-13'}]


def judgment(text,verdict='not_applicable',ids=(),role=False):
    kind='nonfactual' if verdict=='not_applicable' else 'assertion'
    reasons={'not_applicable':'nonfactual','supported':'evidence_supports','unsupported':'missing_evidence','contradicted':'contradiction','uncertain':'uncertain'}
    return {'decision':'revise' if role or verdict in ('unsupported','contradicted') else 'abstain' if verdict=='uncertain' else 'accept',
        'confidence':.95,'role_issues':[0] if role else [],'segments':[{'text':text,'kind':kind,'verdict':verdict,'evidence_ids':list(ids),'reason':reasons[verdict]}]}


def run(replies,judge=None,history=None,memories=None,locale='ja-JP',**kw):
    generator=SimpleNamespace(generate=AsyncMock(side_effect=replies))
    result=asyncio.run(generate_checked(generator,history or [{'role':'user','content':'合成の会話'}],f.ANSWER_PROMPT,'合成の会話',
        memories or [],None,{'status':'disabled','assessment':None},{'enabled':False,'preference':'ask'},
        judge=judge,companion=True,locale=locale,multilingual_facts=True,**kw))
    return result,generator


@pytest.mark.parametrize('text,ids',[
    ('「我30岁」という設定にはしないよ。',('C01',)),
    ('不是“我30岁”，我是28岁。',('C01',)),
    ('我28岁，在栖川经营旧书店。',('C01','C02')),
    ('28歳で、栖川で古書店を営んでいるよ。',('C01','C02')),
    ('合成桜ヶ丘市に住んでいるんだね。',('memory_synthetic',)),
    ('我记得你住在合成桜ヶ丘市。',('memory_synthetic',)),
    ('「桜ヶ丘市」と省略せず、合成桜ヶ丘市のまま覚えているよ。',('memory_synthetic',)),
    ('“你刚才告诉我住在合成桜ヶ丘市”这句话不能凭旧记录来断定。',('memory_synthetic',)),
])
def test_valid_quotes_negations_and_full_names_not_lexically_overruled(text,ids):
    judge=SimpleNamespace(review=AsyncMock(return_value=judgment(text,'supported',ids)))
    (reply,guarded,status),g=run([text],judge,memories=MEMORIES,locale='zh-CN' if text.startswith(('不是','我','“')) else 'ja-JP')
    assert reply==text and not guarded and status['calls']==1
    g.generate.assert_awaited_once();judge.review.assert_awaited_once()


def test_legacy_false_positive_and_japanese_false_negative_are_retained_as_history():
    assert conflicts('「我30岁」という設定にはしないよ。')
    assert not conflicts('僕は30歳の医師だよ。')
    assert source_time_conflicts('“你刚才告诉我住在合成桜ヶ丘市”这句话不能凭旧记录来断定。',[])
    assert not source_time_conflicts('さっき合成桜ヶ丘市に住んでいると教えてくれたね。',[])
    assert place_conflicts('“青禾市”不是“合成青禾市”的完整写法。',['合成青禾市'])


@pytest.mark.parametrize('bad,good,locale',[
    ('僕は30歳の医師だよ。','28歳で、古書店を営んでいるよ。','ja-JP'),
    ('我是30岁的医生。','我28岁，在栖川经营旧书店。','zh-CN'),
    ('祖父からこの古書店を受け継いだんだ。','この店は三年前、自分で開いたんだ。','ja-JP'),
    ('这家店是我从祖父那里继承的。','这家店是三年前我自己开的。','zh-CN'),
    ('昔の記憶は失ってしまったんだ。','まだ話していないことは、ゆっくり話そう。','ja-JP'),
    ('さっき合成桜ヶ丘市に住んでいると教えてくれたね。','合成桜ヶ丘市に住んでいることは覚えているよ。','ja-JP'),
    ('你今天告诉我你住在合成桜ヶ丘市。','我记得你住在合成桜ヶ丘市。','zh-CN'),
    ('桜ヶ丘に住んでいるんだね。','そちらでの暮らしはどう？','ja-JP'),
    ('你住在桜ヶ丘，离我店里走路三分钟。','你住的地方，最近有什么喜欢去的地方吗？','zh-CN'),
    ('また僕の向かいに座ったね。','今日はどんな話をしようか。','ja-JP'),
    ('你又坐到我对面了。','今天想聊些什么？','zh-CN'),
    ('店は静かだし、君の予約ももう済ませてある。','店は静かだよ。話したいことから聞かせて。','ja-JP'),
    ('你从来没说过住那里。','按你现在的纠正来，之前的说法就不作为现址了。','zh-CN'),
])
def test_unsupported_paraphrases_rewrite_with_shared_budget(bad,good,locale):
    judge=SimpleNamespace(review=AsyncMock(side_effect=[judgment(bad,'unsupported'),judgment(good)]))
    (reply,guarded,status),g=run([bad,good],judge,memories=MEMORIES,locale=locale)
    assert reply==good and guarded and status['calls']==2
    assert f.REWRITE in g.generate.call_args.args[1] and 'missing_evidence' in g.generate.call_args.args[1]


@pytest.mark.parametrize('text',[
    'さっき、合成桜ヶ丘市に住んでいると教えてくれたね。',
    '你刚才说住在合成桜ヶ丘市，我听到了。',
    '明日、店に来てみる？',
    '店は静かで、ページをめくる音だけ聞こえる。',
    '「祖父から継いだ」は誰かの誤解で、僕は自分で開いたんだ。',
])
def test_semantic_review_can_accept_recent_assertion_invitation_atmosphere_or_negated_error(text):
    judge=SimpleNamespace(review=AsyncMock(return_value=judgment(text)))
    (reply,guarded,_),_=run([text],judge,history=[{'role':'user','content':'我住在合成桜ヶ丘市。'}])
    assert reply==text and not guarded
    bundle=judge.review.call_args.args[2]
    assert next(x for x in bundle if x['id']=='user_0')['current'] is True


@pytest.mark.parametrize('locale',['ja-JP','zh-CN'])
@pytest.mark.parametrize('enabled',[True,False])
def test_missing_judge_or_review_off_returns_nonfactual_localized_safe_reply(locale,enabled):
    judge=None if enabled else SimpleNamespace(review=AsyncMock())
    (reply,guarded,status),g=run(['unverified synthetic claim'],judge,locale=locale,review_enabled=enabled)
    assert guarded and status=={'status':'reply_safe_fallback','calls':0}
    assert ('うん' in reply)==(locale=='ja-JP')
    g.generate.assert_awaited_once()
    if judge:judge.review.assert_not_awaited()


@pytest.mark.parametrize('kind',['invalid','unknown','coverage','low','timeout','controls'])
def test_failure_never_falls_back_to_legacy_rules_or_retries(kind):
    text='さっき教えてくれたね。'
    result=judgment(text)
    if kind=='invalid':result={'bad':'synthetic'}
    if kind=='unknown':result=judgment(text,'supported',['invented'])
    if kind=='coverage':result=judgment('partial')
    if kind=='low':result['confidence']=.2
    if kind=='controls':result=judgment(text,'supported',['reply_policy'])
    judge=SimpleNamespace(review=AsyncMock(side_effect=TimeoutError()) if kind=='timeout' else AsyncMock(return_value=result))
    (reply,guarded,status),g=run([text],judge)
    assert reply!=text and guarded and status['status'] in ('unavailable','uncertain')
    g.generate.assert_awaited_once();judge.review.assert_awaited_once()


@pytest.mark.parametrize('locale',['zh-CN','ja-JP'])
def test_repeated_bad_reply_uses_language_fallback_and_two_call_limit(locale):
    text='私は30歳だ。';judge=SimpleNamespace(review=AsyncMock(return_value=judgment(text,'contradicted')))
    (reply,guarded,status),g=run([text,text],judge,locale=locale)
    assert '30' not in reply and guarded and status=={'status':'fallback','calls':2}
    assert g.generate.await_count==judge.review.await_count==2


@pytest.mark.parametrize('mode',['companion','audit'])
@pytest.mark.parametrize('weather_mode',['semantic','legacy'])
@pytest.mark.parametrize('emotion_mode',['semantic','legacy'])
def test_sdk_composition_and_control_policy_only_mock_transport(mode,weather_mode,emotion_mode):
    calls=[]
    def handler(request):
        body=json.loads(request.content);calls.append(body)
        prompt=body['messages'][0]['content'];data=json.loads(body['messages'][1]['content'])
        assert f.REVIEW_PROMPT_EXTRA in prompt
        assert (f.WEATHER_REVIEW in prompt)==(weather_mode=='semantic')
        assert (f.EMOTION_REVIEW in prompt)==(emotion_mode=='semantic')
        assert next(x['data'] for x in data['evidence'] if x['id']=='reply_policy')['reply_locale']=='ja-JP'
        result={'confidence':.95,'role_issues':[],'units':[{'id':u['id'],'kind':'nonfactual','verdict':'not_applicable','evidence_ids':[]} for u in data['units']]}
        return httpx.Response(200,json={'id':'synthetic','object':'chat.completion','created':0,'model':'synthetic','choices':[
            {'index':0,'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(result)}}]})
    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            settings=Settings(_env_file=None,chat_provider='gemini',gemini_api_key='synthetic-not-a-key',dialogue_mode=mode,
                weather_understanding_mode=weather_mode,emotion_understanding_mode=emotion_mode,reply_understanding_mode='semantic')
            evidence=evidence_bundle([{'role':'user','content':'合成会話'}],MEMORIES,None,None)
            evidence.append({'id':'reply_policy','kind':'reply_policy','data':{'reply_locale':'ja-JP'}})
            return await review_reply(f.FactAnalysisProvider(settings,client),'こんにちは。',[],evidence)
    assert asyncio.run(check()).status=='accept' and len(calls)==1


def test_mode_default_and_invalid_configuration(monkeypatch):
    monkeypatch.delenv('REPLY_UNDERSTANDING_MODE',raising=False)
    assert Settings(_env_file=None).reply_understanding_mode=='semantic'
    with pytest.raises(ValidationError):Settings(_env_file=None,reply_understanding_mode='other')


def test_semantic_path_never_invokes_legacy_character_time_place_or_scene_functions(monkeypatch):
    def forbidden(*a,**kw):raise AssertionError('legacy semantic guard invoked')
    for name in ('conflicts','grounding_conflicts','source_time_conflicts','scene_conflicts'):
        monkeypatch.setattr('app.reply_pipeline.'+name,forbidden)
    for name in ('place_conflicts','protected_places'):
        monkeypatch.setattr('app.grounding.'+name,forbidden)
    text='「我30岁」という設定にはしないよ。'
    judge=SimpleNamespace(review=AsyncMock(return_value=judgment(text,'supported',['C01'])))
    assert run([text],judge)[0][0]==text


def test_combined_fact_weather_emotion_keeps_numeric_boundary_and_single_rewrite_budget():
    from app.emotion import DEFAULTS
    from app.emotion_presentation import combined_fallback
    weather={'status':'ok','source':'mock','kind':'current','temperature_c':15}
    mood={'status':'analyzed','assessment':{'labels':['sadness'],'source':'model','intensity':.6,'confidence':.9}}
    config={**DEFAULTS,'enabled':True,'preference':'listen'}
    text='そちらは推定80度だよ。'
    g=SimpleNamespace(generate=AsyncMock(return_value=text))
    judge=SimpleNamespace(review=AsyncMock(return_value=judgment(text,'supported',['weather_current'])))
    result=asyncio.run(generate_checked(g,[{'role':'user','content':'合成会話'}],f.ANSWER_PROMPT,'合成会話',[],weather,mood,config,
        judge=judge,companion=True,locale='ja-JP',multilingual_facts=True,multilingual_weather=True,multilingual_emotion=True))
    assert result[0]==combined_fallback(weather,mood,config,'ja-JP') and result[2]['calls']==2
    assert g.generate.await_count==judge.review.await_count==2
    assert '15度' in result[0] and '80度' not in result[0]


def test_role_issue_rewrite_feedback_does_not_reduce_all_errors_to_shop_knowledge():
    text='僕は30歳。';correct='28歳だよ。'
    judge=SimpleNamespace(review=AsyncMock(side_effect=[judgment(text,'supported',['role_profile'],role=True),judgment(correct,'supported',['C01'])]))
    (reply,guarded,_),g=run([text,correct],judge)
    assert reply==correct and guarded
    prompt=g.generate.call_args.args[1]
    assert 'role_mismatch' in prompt and 'role_mismatch仅改掉不知道自家环境' not in prompt


def test_mixed_canonical_clause_cannot_hide_unsupported_shared_past():
    one='僕は28歳。';two='君とは子どもの頃から一緒だったね。';correct='28歳だよ。'
    result=judgment(one,'supported',['C01'])
    result['decision']='revise'
    result['segments']+=judgment(two,'unsupported')['segments']
    judge=SimpleNamespace(review=AsyncMock(side_effect=[result,judgment(correct,'supported',['C01'])]))
    (reply,guarded,status),_=run([one+two,correct],judge)
    assert reply==correct and guarded and status['calls']==2


def test_history_evidence_preserves_latest_correction_and_does_not_promote_assistant_claim():
    history=[{'role':'user','content':'店に着いたよ。'},{'role':'assistant','content':'僕の向かいに座ったね。'},
             {'role':'user','content':'もう店を出たよ。'}]
    bad='まだ僕の向かいにいるね。';good='外に出たんだね。今日は何を話そうか。'
    judge=SimpleNamespace(review=AsyncMock(side_effect=[judgment(bad,'contradicted',['user_2']),judgment(good,'supported',['user_2'])]))
    assert run([bad,good],judge,history=history)[0][0]==good
    evidence=judge.review.call_args.args[2]
    users=[e for e in evidence if e['kind']=='user']
    assert [e['current'] for e in users]==[False,True]
    assert [e['text'] for e in users]==['店に着いたよ。','もう店を出たよ。']
    assert not any('向かい' in e.get('text','') for e in evidence)


@pytest.mark.parametrize('locale,text',[('ja-JP','こんにちは。'),('zh-CN','你好。')])
def test_exact_audited_greeting_template_skips_review_even_when_judge_unavailable(locale,text):
    judge=SimpleNamespace(review=AsyncMock(side_effect=TimeoutError()))
    assert run([text],judge,locale=locale)[0]==(text,False,{'status':'trusted_template','calls':0})
    judge.review.assert_not_awaited()
    assert run([text],None,locale=locale)[0][0]==text


@pytest.mark.parametrize('text',['こんにちは。僕は30歳だ。','你好。你今天过来了。','「こんにちは。」と君が昨日言ったね。'])
def test_appending_or_quoting_trusted_template_cannot_skip_review(text):
    judge=SimpleNamespace(review=AsyncMock(return_value=judgment(text,'unsupported')))
    (reply,guarded,status),_=run([text,text],judge)
    assert reply!=text and guarded and status['calls']==2


def test_memory_or_force_review_prevents_trusted_template_skip():
    text='こんにちは。';judge=SimpleNamespace(review=AsyncMock(return_value=judgment(text)))
    assert run([text],judge,memories=MEMORIES)[0][2]['calls']==1
    assert run([text],judge,force_review=True)[0][2]['calls']==1


def test_rewrite_to_trusted_template_cannot_reset_guarded_or_review_call_count():
    bad='僕は30歳。';good='こんにちは。'
    judge=SimpleNamespace(review=AsyncMock(side_effect=[judgment(bad,'contradicted'),judgment(good)]))
    (reply,guarded,status),g=run([bad,good],judge)
    assert reply==good and guarded and status['calls']==2
    assert g.generate.await_count==judge.review.await_count==2
