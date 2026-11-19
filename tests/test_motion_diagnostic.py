"""Only the two read interfaces may be queried, including on timeout."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location("motion_diagnostic", Path(__file__).resolve().parents[1] / "scripts" / "aimdk_motion_diagnostic.py")
diag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diag)


class ReadOnlyTests(unittest.TestCase):
    def test_write_names_are_rejected_before_client_creation(self):
        for name in ('SetMcPresetMotion', 'SetMcAction', 'SetMcInputSource', 'MigrateSystemState'):
            node = Mock()
            with self.assertRaises(ValueError):
                diag.query_once(Mock(), node, name, Mock())
            node.create_client.assert_not_called()

    def test_timeout_is_single_read_and_cleans_pending_request(self):
        future = Mock()
        future.done.return_value = False
        client = Mock()
        client.wait_for_service.return_value = True
        client.call_async.return_value = future
        node = Mock()
        node.create_client.return_value = client
        result = diag.query_once(Mock(), node, 'GetMcAction', NS(Request=lambda: NS()))
        self.assertEqual(result, {'status': 'timeout', 'attempts': 1})
        client.call_async.assert_called_once()
        client.remove_pending_request.assert_called_once_with(future)
        future.cancel.assert_called_once()
        node.destroy_client.assert_called_once_with(client)

    def test_missing_service_sends_no_request(self):
        node = Mock()
        client = node.create_client.return_value
        client.wait_for_service.return_value = False
        result = diag.query_once(Mock(), node, 'GetSystemState', Mock())
        self.assertEqual(result['status'], 'unavailable')
        client.call_async.assert_not_called()
        node.destroy_client.assert_called_once_with(client)

    def test_both_read_header_layouts_get_current_stamp(self):
        for field in ('request', 'header'):
            node = Mock()
            client = node.create_client.return_value
            client.wait_for_service.return_value = True
            client.call_async.return_value.done.return_value = True
            common = NS(header=NS(stamp=None))
            request = NS(**{field: common})
            diag.query_once(Mock(), node, 'GetSystemState' if field == 'header' else 'GetMcAction',
                            NS(Request=lambda: request))
            self.assertIs(common.header.stamp, node.get_clock().now().to_msg.return_value)
            client.call_async.assert_called_once_with(request)

    def test_read_response_is_preserved_and_client_destroyed(self):
        node = Mock()
        client = node.create_client.return_value
        client.wait_for_service.return_value = True
        future = client.call_async.return_value
        future.done.return_value = True
        future.result.return_value = 'STAND_DEFAULT status=100'
        result = diag.query_once(Mock(), node, 'GetMcAction', NS(Request=lambda: NS()))
        self.assertEqual(result['value'], 'STAND_DEFAULT status=100')
        client.call_async.assert_called_once()
        node.destroy_client.assert_called_once_with(client)


if __name__ == '__main__':
    unittest.main()
