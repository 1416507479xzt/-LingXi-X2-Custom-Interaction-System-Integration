"""Read-only PC2 motion diagnosis. Never creates a client for motion writes."""
import importlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
READ_SERVICES = ("GetMcAction", "GetSystemState")
SCHEMA_SERVICES = ("SetMcPresetMotion", "GetMcAction", "GetSystemState",
                   "GetMcMotions", "GetMcPresetMotionState")


def service_path(name):
    if name not in READ_SERVICES:
        raise ValueError("Only motion/system state reads are permitted")
    return "/aimdk_5Fmsgs/srv/" + name


def query_once(ros, node, name, service_type, timeout=3):
    client = node.create_client(service_type, service_path(name))
    try:
        if not client.wait_for_service(timeout_sec=timeout):
            return {"status": "unavailable"}
        request = service_type.Request()
        # Match the official read-only example's current timestamp.
        common = getattr(request, "request", getattr(request, "header", None))
        if common is not None and hasattr(common, "header"):
            common.header.stamp = node.get_clock().now().to_msg()
        future = client.call_async(request)
        try:
            ros.spin_until_future_complete(node, future, timeout_sec=timeout)
            if not future.done():
                client.remove_pending_request(future)
                future.cancel()
                return {"status": "timeout", "attempts": 1}
            response = future.result()
            return {"status": "response", "attempts": 1, "value": str(response)[:6000]}
        except Exception as exc:
            return {"status": "error", "error_type": type(exc).__name__}
    finally:
        node.destroy_client(client)


def main():
    report = {"scope": "PC2 read-only; no motion or mode writes; no SDK changes"}
    try:
        ros = importlib.import_module("rclpy")
        messages = importlib.import_module("aimdk_msgs")
        services = importlib.import_module("aimdk_msgs.srv")
    except ImportError as exc:
        print("无法导入机载ROS/SDK，请先 source /home/agi/aimdk/install/local_setup.bash；", type(exc).__name__)
        return 1
    report["sdk_python_path"] = messages.__file__
    version = Path("/home/agi/aimdk/version")
    report["sdk_version"] = version.read_text(encoding="utf-8").strip() if version.is_file() else "not found"
    report["interfaces"] = {}
    for name in SCHEMA_SERVICES:
        service_type = getattr(services, name, None)
        report["interfaces"][name] = (None if service_type is None else {
            "request": service_type.Request.get_fields_and_field_types(),
            "response": service_type.Response.get_fields_and_field_types()})
    report["installed_preset_examples"] = [str(p) for p in
        Path("/home/agi/aimdk/src/py_examples").rglob("*preset*motion*.py")][:10]
    ros.init()
    node = ros.create_node("eldercare_motion_readonly_diagnostic")
    try:
        # One node only; allow discovery without spawning many CLI nodes.
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            ros.spin_once(node, timeout_sec=.1)
        owners = {}
        targets = {"/aimdk_5Fmsgs/srv/" + name for name in SCHEMA_SERVICES}
        report["discovery_errors"] = []
        for name, namespace in sorted(set(node.get_node_names_and_namespaces())):
            try:
                advertised = node.get_service_names_and_types_by_node(name, namespace)
            except Exception as exc:
                report["discovery_errors"].append({"node": name, "error_type": type(exc).__name__})
                continue
            for path, types in advertised:
                if path in targets:
                    owners.setdefault(path, []).append({"node": namespace.rstrip("/") + "/" + name,
                                                       "types": types})
        report["service_providers"] = owners
        report["queries"] = {}
        for name in READ_SERVICES:
            service_type = getattr(services, name, None)
            report["queries"][name] = ({"status": "type_missing"} if service_type is None else
                query_once(ros, node, name, service_type))
    finally:
        node.destroy_node()
        if ros.ok():
            ros.shutdown()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
