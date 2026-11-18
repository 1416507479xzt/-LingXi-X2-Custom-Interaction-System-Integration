"""Paid synthetic dining conversation -> isolated JSONL -> real local HTTP page."""
import argparse
import asyncio
import http.client
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from feedback_dashboard import make_handler
from x2_agent.agent_config import AgentConfig
from x2_agent.dining_feedback import load_feedback
from x2_agent.life_assistance import load_context
from x2_agent.llm import LlmClient
from x2_agent.model_dialogue import ModelDialogue, generate_dialogue
from x2_agent.presentation import capabilities


def get_page(port):
    client = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        client.request("GET", "/")
        response = client.getresponse()
        return response.status, response.read().decode("utf-8")
    finally:
        client.close()


async def run(args):
    config = AgentConfig.from_env()
    llm = LlmClient(config.ark_api_url)
    memory = ModelDialogue()
    rows = []
    cases = [("今天食堂的汤有点咸，希望下次少放盐。", 0),
             ("对，就这样记录。", 1), ("食堂以后能做清蒸鱼吗？", 1),
             ("好的，记下来吧。", 2), ("今天食堂的菜有点辣。", 2),
             ("这条先不提交了。", 2), ("今天食堂有什么菜？", 2), ("确认提交。", 2)]
    try:
        with tempfile.TemporaryDirectory() as temp:
            records = Path(temp) / "feedback.jsonl"
            with ThreadingHTTPServer(("127.0.0.1", 0), make_handler(records)) as server:
                thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=.01), daemon=True)
                thread.start()
                try:
                    for turn, (utterance, expected_count) in enumerate(cases, 1):
                        started = time.perf_counter()
                        answer = await generate_dialogue(llm, utterance,
                            {**memory.context(), "capabilities": capabilities(backend="none"),
                             "life_assistance": load_context()}, config.llm_model, config.ark_key)
                        if answer:
                            memory.commit(utterance, answer, dining_records_path=records)
                        else:
                            memory.remember_unanswered(utterance)
                        saved = load_feedback(records)
                        status, page = await asyncio.to_thread(get_page, server.server_port)
                        row = {"turn": turn, "user": utterance, "answer": answer,
                               "generation_and_save_ms": round((time.perf_counter() - started) * 1000),
                               "record_count": len(saved), "expected_count": expected_count,
                               "http_status": status, "page_contains_saved_items": all(r["item"] in page for r in saved)}
                        rows.append(row)
                        print(json.dumps(row, ensure_ascii=False), flush=True)
                    final_records = load_feedback(records)
                finally:
                    server.shutdown()
                    thread.join(timeout=1)
            passed = (all(r["answer"] is not None and r["record_count"] == r["expected_count"] and r["http_status"] == 200
                          and r["page_contains_saved_items"] for r in rows)
                      and len(final_records) == 2 and final_records[0]["item"] == "汤"
                      and final_records[0]["observation"] == "有点咸"
                      and final_records[0]["request"] == "少放盐"
                      and final_records[1]["item"] == "清蒸鱼")
            report = {"model": config.llm_model, "passed": passed, "turns": rows, "records": final_records,
                      "scope": "Synthetic text and local HTTP only; robot microphone/TTS/SSH tunnel not tested"}
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print("食堂文本/存储/网页检查：" + ("通过" if passed else "存在未通过项"))
            return passed
    finally:
        await llm.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Allow paid model calls; never uses real feedback file")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.live:
        parser.error("--live is required; this uses the configured API account")
    sys.exit(0 if asyncio.run(run(args)) else 1)
