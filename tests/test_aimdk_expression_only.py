"""Expression-only operation never imports or calls motion services."""
import asyncio
import sys
import unittest
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, Mock, patch

from x2_agent.agent import DoubaoAgent, parse_args
from x2_agent.agent_config import AgentConfig
from x2_agent.model_dialogue import DialogueReply
from x2_agent.presentation import AimdkPresentation, capabilities


class ExpressionOnlyTests(unittest.IsolatedAsyncioTestCase):
    def test_cli_config_keeps_motion_disabled_unless_explicitly_selected(self):
        with patch.dict('os.environ', {'DOUBAO_SPEECH_API_KEY': 'offline', 'ARK_API_KEY': 'offline'}):
            args = parse_args(['--competition-mode', '--presentation-backend', 'aimdk',
                               '--enable-robot-presentation'])
            config = AgentConfig.from_args(args)
            self.assertFalse(config.enable_robot_motion)
            args.enable_robot_motion = True
            self.assertTrue(AgentConfig.from_args(args).enable_robot_motion)
        with self.assertRaises(ValueError):
            AgentConfig(speech_key='offline', ark_key='offline', enable_robot_motion=True)

    def test_default_catalog_has_expressions_and_no_gestures(self):
        catalog = capabilities(backend='aimdk')
        self.assertIn('happy', catalog['emotions'])
        self.assertEqual(catalog['gestures'], [])
        self.assertEqual(catalog['explanation_gestures'], [])
        self.assertEqual(catalog['gesture_meanings'], {})

    def test_constructor_needs_only_playemoji_types(self):
        ros = NS(init=Mock(), shutdown=Mock())
        context = NS(ok=lambda: True)
        node = NS(create_client=Mock(return_value=Mock()), destroy_node=Mock())
        modules = {'rclpy': ros, 'rclpy.context': NS(Context=lambda: context),
                   'rclpy.node': NS(Node=Mock(return_value=node)),
                   'aimdk_msgs': NS(), 'aimdk_msgs.srv': NS(PlayEmoji=NS())}
        with patch.dict(sys.modules, modules):
            backend = AimdkPresentation()
            self.assertFalse(backend.enable_motion)
            self.assertEqual(set(backend.clients), {'emoji'})
            node.create_client.assert_called_once()
            backend.close()
            ros.shutdown.assert_called_once_with(context=context)

    async def test_disabled_motion_does_not_query_or_write_even_when_plan_has_gesture(self):
        backend = object.__new__(AimdkPresentation)
        backend.enable_motion = False
        backend.lock = asyncio.Lock()
        backend.types = {'emoji': NS(Request=lambda: NS())}
        backend._call = AsyncMock(return_value=NS(success=True))
        results = await backend.dispatch('happy', 'wave_hands', lambda: True)
        self.assertEqual(results[0]['status'], 'accepted')
        self.assertEqual(results[1]['status'], 'blocked')
        backend._call.assert_awaited_once()
        self.assertEqual(backend._call.call_args.args[0], 'emoji')

    async def test_rejected_emoji_keeps_server_reason_and_request_parameters(self):
        backend = object.__new__(AimdkPresentation)
        backend.enable_motion = False
        backend.lock = asyncio.Lock()
        backend.types = {'emoji': NS(Request=lambda: NS())}
        backend._call = AsyncMock(return_value=NS(success=False, message='priority conflict'))
        results = await backend.dispatch('sympathy', None, lambda: True)
        self.assertEqual(results[0]['status'], 'rejected')
        self.assertEqual(results[0]['message'], 'priority conflict')
        self.assertEqual((results[0]['emotion_id'], results[0]['mode'],
                          results[0]['priority']), (120, 1, 1))
        backend._call.assert_awaited_once()

    async def test_missing_response_is_unknown_without_retry(self):
        backend = object.__new__(AimdkPresentation)
        backend.enable_motion = False
        backend.lock = asyncio.Lock()
        backend.types = {'emoji': NS(Request=lambda: NS())}
        backend._call = AsyncMock(return_value=None)
        results = await backend.dispatch('happy', None, lambda: True)
        self.assertEqual(results[0]['status'], 'unknown')
        self.assertEqual(results[0]['reason'], 'service_unavailable_or_response_timeout')
        backend._call.assert_awaited_once()

    async def test_ros_wait_does_not_block_speech_and_duplicate_plans_are_not_queued(self):
        agent = object.__new__(DoubaoAgent)
        agent.presentation_backend = Mock()
        agent._presentation_tasks = set()
        started, release = asyncio.Event(), asyncio.Event()
        async def slow(*args):
            started.set()
            await release.wait()
        agent._dispatch_model_presentation = AsyncMock(side_effect=slow)
        reply = DialogueReply('您好')
        await asyncio.wait_for(agent._model_presentation(None, 'e', 'i', reply), .1)
        await started.wait()
        self.assertEqual(len(agent._presentation_tasks), 1)
        await agent._model_presentation(None, 'e2', 'i2', reply)
        self.assertEqual(agent._dispatch_model_presentation.await_count, 1)
        release.set()
        await asyncio.gather(*agent._presentation_tasks)
        await asyncio.sleep(0)
        self.assertEqual(agent._presentation_tasks, set())

    async def test_close_cancels_inflight_expression_before_destroying_ros(self):
        agent = object.__new__(DoubaoAgent)
        task = asyncio.create_task(asyncio.sleep(10))
        agent._presentation_tasks = {task}
        agent._llm_warm = agent._tts_warm = None
        agent.tts = NS(close=AsyncMock())
        agent.llm = NS(close=AsyncMock())
        agent.presentation_backend = NS(close=Mock())
        agent.args = NS()
        await agent.close()
        self.assertTrue(task.cancelled())
        agent.presentation_backend.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
