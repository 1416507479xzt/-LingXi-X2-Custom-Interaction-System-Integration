import json
import unittest
from types import SimpleNamespace

from x2_agent.model_dialogue import ModelDialogue, generate_dialogue, remove_registration_prefix, ensure_interview_closing
from x2_agent.presentation import capabilities


class ReplyStyleTests(unittest.IsolatedAsyncioTestCase):
    def test_observed_registration_prefixes(self):
        cases = {
            "我记下您脖子不舒服啦。别长时间保持同一姿势。": "别长时间保持同一姿势。",
            "您脖子不舒服我记下了。您说。": "您说。",
            "好的，您肚子不舒服的情况我记下了，要是之后有变化可以告诉我。": "要是之后有变化可以告诉我。",
            "我了解您现在腰部也不舒服，多留意腰部的状态。": "多留意腰部的状态。",
            "我知道您现在肚子不舒服了。这样多久了？": "这样多久了？",
            "我记下了。": "",
            "了解您现在的疲惫感啦。您今天的疲惫影响做事了吗？": "您今天的疲惫影响做事了吗？",
        }
        for original, expected in cases.items():
            with self.subTest(original=original):
                self.assertEqual(remove_registration_prefix(original), expected)

    def test_preserve_recall_quotes_questions_and_medical_conditions(self):
        for text in ("我记得您说过脖子疼，后来又说不疼了。",
                     "“我记下了”这句话显得生硬。",
                     "您是想让我记下这个提醒吗？",
                     "如果疼痛持续不缓解，请咨询医护。",
                     "您之前提过腰酸，现在是加重了吗？"):
            self.assertEqual(remove_registration_prefix(text), text)

    async def test_valid_remainder_kept_without_extra_model_call(self):
        calls = []
        async def stream(*args, **kwargs):
            calls.append(1)
            yield "text", json.dumps(dict(intent="other", action="continue",
                reply="我知道您现在肚子不舒服了。这样多久了？", emotion="neutral", gesture=None))
        memory = ModelDialogue()
        answer = await generate_dialogue(SimpleNamespace(stream=stream), "肚子不舒服",
                {**memory.context(), "capabilities": capabilities()}, "model", "key")
        self.assertEqual(answer["reply"], "这样多久了？")
        self.assertEqual(len(calls), 1)
        memory.commit("肚子不舒服", answer)
        self.assertEqual(memory.verbatim_turns[-1], {"user": "肚子不舒服", "assistant": "这样多久了？"})

    async def test_empty_remainder_uses_bounded_repair(self):
        calls = []
        async def stream(prompt, *args, **kwargs):
            calls.append(prompt)
            yield "text", json.dumps(dict(intent="other", action="continue",
                reply="我记下了。" if len(calls) == 1 else "这样多久了？", emotion=None, gesture=None))
        answer = await generate_dialogue(SimpleNamespace(stream=stream), "肚子不舒服",
                {**ModelDialogue().context(), "capabilities": capabilities()}, "model", "key")
        self.assertEqual(answer["reply"], "这样多久了？")
        self.assertEqual(len(calls), 2)
        self.assertIn("registration_only_reply", calls[1])


class InterviewClosingTests(unittest.TestCase):
    def test_observed_caring_endings_do_not_get_another_farewell(self):
        context = {"interview_active": True, "health_rounds": 1}
        for ending in ("有任何不适请及时告诉我。", "若有其他不适，请告诉我。", "如果有不适随时告诉我。", "有其他不舒服，随时跟我说。", "要是疲惫持续没有好转，记得及时和我说。"):
            reply = {"intent": "health", "action": "close", "reply": "您说已经有点影响做事。" + ending}
            with self.subTest(ending=ending):
                self.assertEqual(ensure_interview_closing(reply, context), reply)

    def test_an_invitation_to_explain_is_not_a_caring_ending(self):
        reply = {"intent": "health", "action": "close", "reply": "您刚才告诉我疲惫有点影响做事。"}
        self.assertNotEqual(ensure_interview_closing(reply, {"interview_active": True, "health_rounds": 1}), reply)


class UnmentionedAdviceTests(unittest.IsolatedAsyncioTestCase):
    async def test_fatigue_does_not_receive_reference_neck_back_advice(self):
        memory = ModelDialogue()
        memory.begin()
        memory.commit("我今天感觉有点疲惫。", dict(intent="health", action="followup", reply="睡前可以听音乐放松，这种疲惫影响做事了吗？", emotion=None, gesture=None))
        calls = []
        async def stream(prompt, *args, **kwargs):
            calls.append(prompt)
            reply = "颈部避免长时间保持同一姿势。" if len(calls) == 1 else "已经有点影响做事了，今天先照顾好自己，有需要再叫我。"
            yield "text", json.dumps(dict(intent="health", action="close", reply=reply, emotion=None, gesture=None))
        answer = await generate_dialogue(SimpleNamespace(stream=stream), "有一点影响日常活动。",
            {**memory.context(), "capabilities": capabilities(backend="none")}, "model", "key")
        self.assertEqual(len(calls), 2)
        self.assertNotIn("颈部", answer["reply"])
        self.assertIn("unmentioned_neck_back_advice", calls[1])

    def test_user_mentions_and_assistant_examples_are_distinguished(self):
        from x2_agent.model_dialogue import unmentioned_neck_back_advice
        advice = "颈部避免长时间保持同一姿势。"
        self.assertTrue(unmentioned_neck_back_advice(advice, "有一点影响", [{"user": "疲惫", "assistant": "比如脖子疼"}]))
        self.assertFalse(unmentioned_neck_back_advice(advice, "有一点影响", [{"user": "脖子难受", "assistant": ""}]))


class HealthRecallTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_address_response_does_not_erase_health_quotes(self):
        turns = [{"user": "我腰疼，脖子酸", "assistant": "若受伤请联系医护。"},
                 {"user": "腰已经不酸，现在只是脖子不舒服", "assistant": "知道了。"},
                 {"user": "你记得我哪里住吗", "assistant": "抱歉，我记不清了。"}]
        calls = []
        async def stream(prompt, messages, *args, **kwargs):
            calls.append((prompt, messages))
            reply = "您可以再和我说一下现在哪里不舒服呀。" if len(calls) == 1 else "您现在是脖子不舒服，腰已经不酸了。"
            yield "text", json.dumps(dict(intent="chat" if len(calls) == 1 else "recall", action="continue", reply=reply, emotion=None, gesture=None))
        answer = await generate_dialogue(SimpleNamespace(stream=stream), "你不记得我哪里不舒服了吗？",
            {**ModelDialogue().context(), "verbatim_turns": turns, "capabilities": capabilities(backend="none")}, "model", "key")
        self.assertEqual(len(calls), 2)
        self.assertIn("腰已经不酸", answer["reply"])
        self.assertIn("health_recall_without_history_use", calls[1][0])

    def test_address_queries_and_absent_history_are_not_forced_into_health_recall(self):
        from x2_agent.model_dialogue import missed_health_recall
        turns = [{"user": "脖子疼", "assistant": ""}]
        self.assertFalse(missed_health_recall("请再说一下住址。", "你记得我哪里住吗？", turns))
        self.assertFalse(missed_health_recall("请再说一下。", "你记得我哪里不舒服吗？", []))
