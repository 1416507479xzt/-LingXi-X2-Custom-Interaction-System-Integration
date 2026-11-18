import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from x2_agent.agent import DoubaoAgent, acknowledge_wake_greeting
from x2_agent.competition_flow import HealthGreetingFlow
from x2_agent.gateway import T


class FirstWakeTests(unittest.IsolatedAsyncioTestCase):
    def test_ack_preserves_question_and_does_not_duplicate_greeting(self):
        self.assertEqual(acknowledge_wake_greeting("您好，今天感觉怎么样？"),
                         "您好，我在呢。今天感觉怎么样？")
        for text in ("您好，我在呢。今天感觉怎么样？", "您好，我听着呢。今天状态怎么样？"):
            self.assertEqual(acknowledge_wake_greeting(text), text)

    async def test_first_wake_speaks_ack_then_status_and_repeated_wake_keeps_progress(self):
        for result in (dict(reply="您好，今天感觉怎么样？", emotion=None, gesture=None), None):
            agent = object.__new__(DoubaoAgent)
            agent.args = SimpleNamespace(greeting="", health_semantic="model", app_id="test",
                                         llm_model="model", ark_key="key")
            agent.health_flow = HealthGreetingFlow()
            agent._competition_greeted = False
            agent._tts_seq = 0
            agent.robot_cid = "test"
            agent.llm = None
            agent._model_context = lambda **kwargs: {}
            agent.send = AsyncMock()
            agent._model_presentation = AsyncMock()
            spoken = []
            async def speech(texts):
                async for text in texts:
                    spoken.append(text)
                    yield b"\0\0"
            agent.speech_stream = speech
            with patch("x2_agent.agent.generate_dialogue", new=AsyncMock(return_value=result)) as model:
                await agent.greet(None)
                self.assertEqual(spoken, [])
                await agent.greet(None, wake_triggered=True)
                self.assertEqual(model.await_count, 1)
                self.assertEqual(len(spoken), 1)
                self.assertTrue(spoken[0].startswith("您好，我在呢。"))
                self.assertIn("今天", spoken[0])
                self.assertTrue(spoken[0].endswith("？"))
                text_frames = [call.args[1] for call in agent.send.await_args_list
                               if call.args[1]["type"] == T["llm_delta"]]
                self.assertEqual(text_frames[0]["text"], spoken[0])
                self.assertEqual(agent.health_flow.model_dialogue.verbatim_turns[-1]["assistant"], spoken[0])
                agent.health_flow.model_dialogue.health_rounds = 1
                await agent.greet(None, wake_triggered=True)
                self.assertEqual(len(spoken), 1)
                self.assertEqual(model.await_count, 1)
                self.assertEqual(agent.health_flow.model_dialogue.health_rounds, 1)
