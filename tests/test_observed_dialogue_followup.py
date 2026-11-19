import json
import unittest
from types import SimpleNamespace

from x2_agent.model_dialogue import ModelDialogue, brief_positive_status, generate_dialogue
from x2_agent.presentation import capabilities


class ObservedDialogueTests(unittest.IsolatedAsyncioTestCase):
    async def generate(self, user, drafts):
        calls = []
        async def stream(*args, **kwargs):
            draft = drafts[min(len(calls), len(drafts) - 1)]
            calls.append(args)
            yield "text", json.dumps(draft, ensure_ascii=False)
        memory = ModelDialogue()
        memory.begin()
        answer = await generate_dialogue(SimpleNamespace(stream=stream), user,
            {**memory.context(), "capabilities": capabilities()}, "m", "k")
        return answer, calls

    async def test_positive_status_repairs_impairment_assumption(self):
        base = dict(intent="health", action="followup", emotion=None, gesture=None)
        answer, calls = await self.generate("今天感觉不错", [
            {**base, "reply": "这种状态有没有影响您今天的日常安排呀？"},
            {**base, "reply": "今天状态不错真好，您最近休息和胃口怎么样？"}])
        self.assertEqual(len(calls), 2)
        self.assertNotIn("影响", answer["reply"])

    async def test_healthy_followup_needs_no_retry(self):
        answer, calls = await self.generate("今天感觉不错", [dict(intent="health",
            action="followup", reply="今天状态不错真好，您最近休息和胃口怎么样？",
            emotion=None, gesture=None)])
        self.assertEqual(len(calls), 1)
        self.assertIsNotNone(answer)

    def test_actual_symptom_is_not_classified_as_healthy(self):
        for user in ("还好，就是腰酸", "今天不错但是头疼", "还可以，不过没睡好"):
            self.assertFalse(brief_positive_status(user))

    async def test_unavailable_gesture_does_not_keep_false_promise(self):
        base = dict(intent="other", action="continue", emotion=None)
        answer, calls = await self.generate("给我比个心", [
            {**base, "reply": "好呀，这就为您比个心。", "gesture": "heart_both"},
            {**base, "reply": "我先陪您聊一会儿，稍后再做动作。", "gesture": None}])
        self.assertEqual(len(calls), 2)
        self.assertIsNone(answer["gesture"])
        self.assertNotIn("这就", answer["reply"])

    async def test_criticism_does_not_invent_hearing_problem(self):
        base = dict(intent="chat", action="continue", emotion=None, gesture=None)
        answer, calls = await self.generate("你在说什么东西啊？", [
            {**base, "reply": "抱歉刚才的问题您没听清，我再问一次。"},
            {**base, "reply": "刚才我表达不妥，您状态不错是好事。"}])
        self.assertEqual(len(calls), 2)
        self.assertNotIn("没听清", answer["reply"])
