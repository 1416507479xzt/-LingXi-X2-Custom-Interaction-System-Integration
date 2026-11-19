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
        agent.args = NS(enable_robot_motion=True)
        agent._presentation_has_motion = True
        agent._presentation_tasks = set()
        started, release = asyncio.Event(), asyncio.Event()
        async def slow(*args):
            started.set()
            await release.wait()
        agent._dispatch_model_presentation = AsyncMock(side_effect=slow)
        reply = DialogueReply('您好', gesture='wave_hands')
        await asyncio.wait_for(agent._model_presentation(None, 'e', 'i', reply), .1)
        await started.wait()
        self.assertEqual(len(agent._presentation_tasks), 1)
        await agent._model_presentation(None, 'e2', 'i2', reply)
        self.assertEqual(agent._dispatch_model_presentation.await_count, 1)
        release.set()
        await asyncio.gather(*agent._presentation_tasks)
        await asyncio.sleep(0)
        self.assertEqual(agent._presentation_tasks, set())

    def deferred_backend(self):
        backend = object.__new__(AimdkPresentation)
        backend.enable_motion = False
        backend.lock = asyncio.Lock()
        backend.types = {'emoji': NS(Request=lambda: NS())}
        return backend

    async def test_explicit_priority_rejection_retries_once_after_clear_without_raising_priority(self):
        backend = self.deferred_backend()
        backend._call = AsyncMock(side_effect=[
            NS(success=False, message='优先级低于当前播放，操作被忽略, extra: Current priority: 60, request priority: 1'),
            NS(success=True, message='成功')])
        backend._wait_display_clear = AsyncMock(return_value=True)
        results = await backend.dispatch('sympathy', None, lambda: True)
        self.assertEqual(results[0]['status'], 'accepted')
        self.assertEqual(results[0]['attempts'], 2)
        self.assertEqual(results[0]['priority'], 1)
        self.assertEqual(backend._call.await_count, 2)
        backend._wait_display_clear.assert_awaited_once()
        for call in backend._call.call_args_list:
            self.assertEqual(call.args[1].priority, 1)

    async def test_expression_only_plan_still_defers_when_global_motion_is_enabled(self):
        backend = self.deferred_backend()
        backend.enable_motion = True
        backend._call = AsyncMock(side_effect=[NS(success=False,
            message='优先级低于当前播放, Current priority: 60'), NS(success=True, message='成功')])
        backend._wait_display_clear = AsyncMock(return_value=True)
        results = await backend.dispatch('sympathy', None, lambda: True)
        self.assertEqual(results[0]['status'], 'accepted')
        self.assertEqual(results[0]['attempts'], 2)
        self.assertEqual([c.args[0] for c in backend._call.call_args_list], ['emoji','emoji'])

    async def test_arbitrary_nonpreset_motion_is_rejected_before_any_rpc(self):
        backend = self.deferred_backend()
        backend.enable_motion = True
        backend._call = AsyncMock()
        with self.assertRaises(ValueError):
            await backend.dispatch(None, 'walk', lambda: True)
        backend._call.assert_not_awaited()

    async def test_no_clear_event_means_no_retry(self):
        backend = self.deferred_backend()
        backend._call = AsyncMock(return_value=NS(success=False,
            message='优先级低于当前播放, Current priority: 60'))
        backend._wait_display_clear = AsyncMock(return_value=False)
        results = await backend.dispatch('sympathy', None, lambda: True)
        self.assertEqual(results[0]['status'], 'rejected')
        self.assertEqual(results[0]['attempts'], 1)
        backend._call.assert_awaited_once()

    async def test_stale_idle_status_and_high_priority_do_not_allow_retry(self):
        import time
        backend = self.deferred_backend()
        backend.face_subscription = object()
        backend.face_state = {'priority': 0, 'seen_at': time.monotonic()-10}
        backend.ros = NS(spin_once=Mock())
        backend.node = NS(get_clock=lambda: NS(now=lambda: NS(nanoseconds=100)))
        self.assertFalse(await backend._wait_display_clear(
            lambda: True, since=time.monotonic(), timeout=.02))
        backend._on_face_status(NS(priority=0, e_id=1,
                                   header=NS(stamp=NS(sec=0, nanosec=99))))
        self.assertFalse(await backend._wait_display_clear(
            lambda: True, since=0, timeout=.02))
        backend._on_face_status(NS(priority=60, e_id=170,
                                   header=NS(stamp=NS(sec=0, nanosec=101))))
        self.assertFalse(await backend._wait_display_clear(
            lambda: True, since=0, timeout=.02))
        backend._on_face_status(NS(priority=0, e_id=1,
                                   header=NS(stamp=NS(sec=0, nanosec=102))))
        self.assertTrue(await backend._wait_display_clear(
            lambda: True, since=0, timeout=.02))
        self.assertFalse(await backend._wait_display_clear(
            lambda: False, since=0, timeout=.02))

    async def test_cancellation_of_deferred_expression_releases_lock_without_retry(self):
        backend = self.deferred_backend()
        backend._call = AsyncMock(return_value=NS(success=False,
            message='优先级低于当前播放, Current priority: 60'))
        entered = asyncio.Event()
        async def wait(*args, **kwargs):
            entered.set()
            await asyncio.sleep(10)
        backend._wait_display_clear = wait
        task = asyncio.create_task(backend.dispatch('sympathy', None, lambda: True))
        await entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertFalse(backend.lock.locked())
        backend._call.assert_awaited_once()

    async def test_new_turn_replaces_old_expression_wait_including_null_selection(self):
        agent = object.__new__(DoubaoAgent)
        agent.presentation_backend = Mock()
        agent.args = NS(enable_robot_motion=False)
        agent._presentation_tasks = set()
        started = asyncio.Event()
        async def dispatch(*args):
            if args[1] == 'old':
                started.set()
                await asyncio.sleep(10)
        agent._dispatch_model_presentation = AsyncMock(side_effect=dispatch)
        await agent._model_presentation(None, 'old', 'i', DialogueReply('旧轮次'))
        await started.wait()
        old = next(iter(agent._presentation_tasks))
        await agent._model_presentation(None, 'new', 'i', DialogueReply('新轮次'))
        self.assertTrue(old.cancelled())
        await asyncio.gather(*agent._presentation_tasks)
        self.assertEqual(agent._dispatch_model_presentation.await_count, 2)

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
