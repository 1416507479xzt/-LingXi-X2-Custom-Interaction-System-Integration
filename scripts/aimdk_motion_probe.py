"""PC2-only, one-shot right-hand wave probe; default is a read-only mode query.

Use --execute only after preparing stable stand and a clear arm workspace.
No retries, SDK replacement, mode switching, or PC1 access.
"""
import argparse
import json


def call_once(ros, node, service_type, service_name, make_request, timeout):
    client = node.create_client(service_type, service_name)
    try:
        if not client.wait_for_service(timeout_sec=5):
            return None, 'service_unavailable'
        request = make_request()  # Timestamp is taken after service discovery.
        future = client.call_async(request)
        try:
            ros.spin_until_future_complete(node, future, timeout_sec=timeout)
            if not future.done():
                client.remove_pending_request(future)
                future.cancel()
                return None, 'response_timeout_unknown'
            response = future.result()
            return response, 'response' if response is not None else 'empty_response_unknown'
        except Exception as exc:
            return None, 'response_error_unknown:' + type(exc).__name__
    finally:
        node.destroy_client(client)


def probe(ros, node, services, execute=False):
    report = {'scope': 'PC2; right wave at most once; no mode change',
              'execute_requested': execute, 'motion_requests': 0}
    def mode_request():
        request = services.GetMcAction.Request()
        request.request.header.stamp = node.get_clock().now().to_msg()
        return request
    state, result = call_once(ros, node, services.GetMcAction,
        '/aimdk_5Fmsgs/srv/GetMcAction', mode_request, 3)
    report['mode_query'] = result
    if state is None:
        report['motion_result'] = 'blocked_mode_not_confirmed'
        return report
    report['mode'] = {'code': state.header.code, 'action_desc': state.info.action_desc,
                      'status': state.info.status.value}
    if not execute:
        report['motion_result'] = 'disabled_read_only'
        return report
    if (state.header.code != 0 or state.info.action_desc != 'STAND_DEFAULT'
            or state.info.status.value != 100):
        report['motion_result'] = 'blocked_not_stable_stand'
        return report
    def motion_request():
        request = services.SetMcPresetMotion.Request()
        request.area.value = 2
        request.motion.value = 1002
        request.interrupt = False
        request.play_timestamp = 0
        request.header.stamp = node.get_clock().now().to_msg()
        report['motion_requests'] = 1
        print('稳定站立已核对；发送一次右手挥手，使用当前请求时间戳；不自动重发。', flush=True)
        return request
    response, result = call_once(ros, node, services.SetMcPresetMotion,
        '/aimdk_5Fmsgs/srv/SetMcPresetMotion', motion_request, 8)
    report['motion_result'] = result
    if response is not None:
        report['task_response'] = {'code': response.response.header.code,
            'task_id': response.response.task_id, 'state': response.response.state.value}
    report['completion'] = 'Requires observing the robot; service response is not motion completion'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', help='额外允许单次右手挥手；默认只读查询')
    args = parser.parse_args()
    try:
        import rclpy
        import aimdk_msgs.srv as services
    except ImportError:
        parser.exit(1, '请在PC2先 source /home/agi/aimdk/install/local_setup.bash\n')
    rclpy.init()
    node = rclpy.create_node('eldercare_single_wave_probe')
    try:
        print(json.dumps(probe(rclpy, node, services, args.execute), ensure_ascii=False, indent=2))
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
