"""Cross-check all documented motion/area pairs through the real adapter.

Fixture transcribed from both official v0.9.0 and 1.1 preset-motion tables.
No ROS, cloud, or physical robot is used.
"""
import asyncio
import json
import unittest
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
from x2_agent.presentation import MOTIONS, GESTURE_MEANINGS, AimdkPresentation, capabilities
from x2_agent.model_dialogue import ModelDialogue, validate_reply

OFFICIAL_PAIRS = {
    (1002,2), (1002,1), (1003,2), (1003,1), (1001,2), (1001,1),
    (1004,2), (1004,1), (3017,11), (1013,2), (1013,1),
    (1007,3), (1007,2), (1007,1), (3008,11), (3011,11),
    (1010,3), (1010,2), (1010,1), (3031,11), (3007,11),
    (1008,2), (1008,1), (3009,11), (1011,2), (1011,1),
    (3001,11), (3024,11), (3025,11)}


class DocumentedMotionTests(unittest.IsolatedAsyncioTestCase):
    def backend(self, mode='STAND_DEFAULT', status=100):
        backend = object.__new__(AimdkPresentation)
        backend.enable_motion = True
        backend.lock = asyncio.Lock()
        backend.last_motion = float('-inf')
        backend.node = NS(get_clock=lambda: NS(now=lambda: NS(to_msg=lambda: 'now')))
        backend.types = {k: NS(Request=lambda: NS(header=NS(stamp=None),
            request=NS(header=NS(stamp=None)), motion=NS(value=0), area=NS(value=0)))
            for k in ('emoji','mode','motion')}
        async def call(kind, request):
            if kind == 'mode':
                return NS(header=NS(code=0), info=NS(action_desc=mode,status=NS(value=status)))
            return NS(response=NS(header=NS(code=0),state=NS(value=400),task_id=0))
        backend._call = AsyncMock(side_effect=call)
        return backend

    def test_official_table_is_complete_without_duplicate_alias_pairs(self):
        self.assertEqual(len(MOTIONS),29)
        self.assertEqual(set(MOTIONS.values()),OFFICIAL_PAIRS)
        self.assertEqual(set(GESTURE_MEANINGS),set(MOTIONS))
        catalog = capabilities(backend='aimdk',enable_motion=True)
        self.assertEqual(set(catalog['gestures']),set(MOTIONS))
        self.assertEqual(catalog['motion_validation']['wave_hands'],'physically_verified')
        self.assertEqual(catalog['motion_validation']['heart_both'],'physically_verified')
        self.assertEqual(catalog['motion_validation']['shake_right'],'documented_not_physically_verified')
        self.assertEqual(capabilities(backend='aimdk')['gestures'],[])
        self.assertEqual(capabilities(False,'aimdk',enable_motion=True)['gestures'],[])
        self.assertNotIn('shake_right',capabilities(backend='unity')['gestures'])

    async def test_each_documented_pair_reaches_one_noninterrupting_current_stamp_rpc(self):
        for name,pair in MOTIONS.items():
            with self.subTest(name=name):
                backend=self.backend()
                result=await backend.dispatch(None,name,lambda:True)
                calls=backend._call.call_args_list
                self.assertEqual([c.args[0] for c in calls],['mode','motion'])
                request=calls[1].args[1]
                self.assertEqual((request.motion.value,request.area.value),pair)
                self.assertFalse(request.interrupt)
                self.assertEqual(request.header.stamp,'now')
                self.assertEqual(request.play_timestamp,0)
                self.assertEqual(result[0]['status'],'accepted')

    async def test_every_motion_is_blocked_outside_stable_stand(self):
        for name in MOTIONS:
            for mode,status in [('PASSIVE_DEFAULT',100),('STAND_DEFAULT',200)]:
                backend=self.backend(mode,status)
                result=await backend.dispatch(None,name,lambda:True)
                self.assertEqual(result[0]['status'],'blocked')
                self.assertEqual([c.args[0] for c in backend._call.call_args_list],['mode'])

    def test_model_may_choose_any_documented_name_or_no_gesture_without_numeric_parameters(self):
        context={**ModelDialogue().context(), 'capabilities':capabilities(backend='aimdk',enable_motion=True)}
        for name in (*MOTIONS,None):
            draft=dict(intent='chat', action='continue', reply='好，我配合您。',emotion='happy',gesture=name)
            self.assertIsNotNone(validate_reply(json.dumps(draft,ensure_ascii=False),context), name)
        draft['gesture']={'motion':1002,'area':2}
        self.assertIsNone(validate_reply(json.dumps(draft),context))


if __name__=='__main__':
    unittest.main()
