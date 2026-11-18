import json
from pathlib import Path
import tempfile
import unittest

from x2_agent.agent import parse_args
from x2_agent.agent_config import AgentConfig
from x2_agent.dining_feedback import load_feedback, prepare_transition
from x2_agent.model_dialogue import ModelDialogue


class DiningCliPathTests(unittest.TestCase):
    def test_cli_path_survives_config_and_confirmation_writes_to_that_file(self):
        with tempfile.TemporaryDirectory() as temp:
            records = Path(temp) / "custom" / "confirmed.jsonl"
            config = AgentConfig.from_args(parse_args([
                "--speech-key", "test", "--ark-key", "test", "--competition-mode",
                "--dining-feedback-records", str(records), "--service-data", "custom_services.json"]))
            self.assertEqual(config.dining_feedback_records, str(records))
            self.assertEqual(config.service_data, "custom_services.json")
            memory = ModelDialogue()
            first, _ = prepare_transition("[[DINING_PREPARE|taste|汤|有点咸|少放盐]]", None,
                                          "汤有点咸，下次少放盐")
            memory.commit("汤有点咸，下次少放盐", self.result(first), dining_records_path=config.dining_feedback_records)
            self.assertFalse(records.exists())
            confirmed, error = prepare_transition("[[DINING_CONFIRM]]", memory.pending_dining, "对的，要记录。")
            self.assertIsNone(error)
            memory.commit("对的，要记录。", self.result(confirmed), dining_records_path=config.dining_feedback_records)
            self.assertTrue(records.exists())
            self.assertEqual(len(load_feedback(records)), 1)
            self.assertEqual(load_feedback(records)[0]["item"], "汤")

    @staticmethod
    def result(transition):
        return {"intent": "dining", "action": "continue", "reply": transition["reply"],
                "emotion": None, "gesture": None, "_dining_transition": transition}
