import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location('motion_probe', Path(__file__).resolve().parents[1] / 'scripts/aimdk_motion_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ProbeTests(unittest.TestCase):
    def setup_probe(self, mode='STAND_DEFAULT', status=100, completed=True):
        node = Mock()
        services = NS(GetMcAction=NS(Request=lambda: NS(request=NS(header=NS(stamp=None)))),
                      SetMcPresetMotion=NS(Request=lambda: NS(header=NS(stamp=None),
                          area=NS(value=0), motion=NS(value=0))))
        read, write = Mock(), Mock()
        for client in (read, write):
            client.wait_for_service.return_value = True
            client.call_async.return_value.done.return_value = True
        read.call_async.return_value.result.return_value = NS(header=NS(code=0),
            info=NS(action_desc=mode, status=NS(value=status)))
        write.call_async.return_value.done.return_value = completed
        write.call_async.return_value.result.return_value = NS(response=NS(
            header=NS(code=0), task_id=17, state=NS(value=400)))
        node.create_client.side_effect = [read, write]
        return node, services, read, write

    def test_default_never_creates_motion_client(self):
        node, services, read, write = self.setup_probe()
        result = probe.probe(Mock(), node, services)
        self.assertEqual(result['motion_requests'], 0)
        node.create_client.assert_called_once()
        write.call_async.assert_not_called()

    def test_passive_or_transition_blocks_motion_even_with_execute(self):
        for mode, status in [('PASSIVE_DEFAULT',100), ('STAND_DEFAULT',200)]:
            node, services, read, write = self.setup_probe(mode, status)
            result = probe.probe(Mock(), node, services, execute=True)
            self.assertEqual(result['motion_result'], 'blocked_not_stable_stand')
            node.create_client.assert_called_once()
            write.call_async.assert_not_called()

    def test_single_current_stamp_request_and_complete_task_receipt(self):
        node, services, read, write = self.setup_probe()
        result = probe.probe(Mock(), node, services, execute=True)
        write.call_async.assert_called_once()
        request = write.call_async.call_args.args[0]
        self.assertIs(request.header.stamp, node.get_clock().now().to_msg.return_value)
        self.assertEqual((request.area.value, request.motion.value, request.interrupt,
                          request.play_timestamp), (2,1002,False,0))
        self.assertEqual(result['task_response'], {'code':0, 'task_id':17, 'state':400})
        self.assertEqual(result['motion_requests'], 1)

    def test_timeout_is_unknown_and_never_resends(self):
        node, services, read, write = self.setup_probe(completed=False)
        result = probe.probe(Mock(), node, services, execute=True)
        self.assertEqual(result['motion_result'], 'response_timeout_unknown')
        write.call_async.assert_called_once()
        write.remove_pending_request.assert_called_once()
        self.assertEqual(result['motion_requests'], 1)


if __name__ == '__main__':
    unittest.main()
