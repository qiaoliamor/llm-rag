"""One shared rewrite budget across rules and semantic review."""
from .dialogue import conflicts,FALLBACK
from .grounding import grounding_conflicts,scene_conflicts
from .memory_source import source_time_conflicts
from .weather import weather_reply_conflicts,weather_fallback
from .emotion import emotion_reply_conflicts,emotion_fallback
from .semantic_review import needs_review,evidence_bundle,review_reply,rewrite_feedback

REWRITE='''\n上次输出违反证据或表达边界。重新回答：删除没有证据的店内动态近况，地点名称照证据完整写出或用代词承接，不缩写地名。长期记忆不证明刚才/今天告诉我，改用不带来源时间的“我记得”，不要编造讲述时间。只用已知事实，以沈砚的自然语气关心，不播报来源/日期，不用您；当前天气只作估计。情绪只是可纠正参考，不诊断、不报分数，尊重自述和倾听偏好。'''


async def generate_checked(provider,history,prompt,query,memories,weather,mood,mood_settings,
                           *,judge=None,review_enabled=True,review_timeout=8):
    evidence=evidence_bundle(history,memories,weather,mood)
    guarded=False;review_calls=0;feedback=''
    status='disabled' if not review_enabled else 'mock_or_unavailable'
    for attempt in range(2):
        reply=await provider.generate(history,prompt+(REWRITE+feedback if attempt else ''))
        role_bad=conflicts(reply,query)
        weather_bad=weather_reply_conflicts(reply,weather)
        mood_bad=emotion_reply_conflicts(reply,mood)
        hard=role_bad or weather_bad or mood_bad
        soft=grounding_conflicts(reply,memories,query) or source_time_conflicts(reply,history)
        flagged=hard or soft
        guarded=guarded or flagged
        review=None
        factual_scene=False
        if judge is not None and review_enabled:
            if needs_review(reply,evidence=memories,weather=weather,mood=mood,flagged=flagged):
                review_calls+=1
                outcome=await review_reply(judge,reply,history,evidence,timeout=review_timeout)
                decision,review=outcome
                if decision in ('unavailable','uncertain'):
                    return FALLBACK,True,{'status':decision,'calls':review_calls,'failure':outcome.failure}
                # A validated high-confidence accept may correct lexical false
                # positives, but cannot override hard role/tool constraints.
                # No trusted dynamic scene provider exists yet: role identity
                # cannot prove an asserted current shop state. Nonfactual
                # conditions/quotes remain eligible for lexical correction.
                factual_scene=bool(review and any(s.kind in ('assertion','epistemic') and scene_conflicts(s.text) for s in review.segments))
                flagged=hard or factual_scene or decision=='revise'
                status='revised' if attempt else 'accepted'
                guarded=guarded or decision=='revise'
            else:status='skipped'
        if not flagged:return reply,guarded,{'status':status,'calls':review_calls}
        feedback=rewrite_feedback(review)
        if attempt:
            if role_bad or soft or factual_scene or (review is not None and review.decision=='revise'):reply=FALLBACK
            elif weather_bad:reply=weather_fallback(weather)
            elif mood_bad:reply=emotion_fallback(mood,mood_settings)
            else:reply=FALLBACK
            return reply,True,{'status':'fallback','calls':review_calls}
    raise AssertionError('unreachable')
