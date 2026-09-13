import json
import unittest
from types import SimpleNamespace

from pymol_chat.agent import PyMOLAgent
from pymol_chat.executor import ExecutionResult


class FakeExecutor:
    def __init__(self):
        self.codes = []

    def scene_summary(self):
        return {"objects": [{"name": "protein", "chains": ["A"], "atoms": 10}]}

    def execute(self, code):
        self.codes.append(code)
        if len(self.codes) == 1:
            return ExecutionResult(False, "", "AttributeError: invalid")
        return ExecutionResult(True, "Executed successfully.")


class FakeResponses:
    def __init__(self):
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        number = len(self.requests)
        if number <= 2:
            call = SimpleNamespace(
                type="function_call",
                name="execute_pymol_python",
                arguments=json.dumps({"code": "cmd.bad()" if number == 1 else "cmd.color('green', 'chain A')"}),
                call_id=f"call-{number}",
            )
            return SimpleNamespace(id=f"response-{number}", output=[call], output_text="")
        return SimpleNamespace(id="response-3", output=[], output_text="Colored chain A green.")


class AgentTests(unittest.TestCase):
    def test_agent_repairs_failed_pymol_call(self):
        agent = object.__new__(PyMOLAgent)
        agent.client = SimpleNamespace(responses=FakeResponses())
        agent.executor = FakeExecutor()
        agent.debug = lambda _message: None
        agent.previous_response_id = None

        answer = agent.ask("Color chain A green")
        self.assertEqual(answer, "Colored chain A green.")
        self.assertEqual(agent.executor.codes, ["cmd.bad()", "cmd.color('green', 'chain A')"])
        self.assertEqual(agent.client.responses.requests[1]["previous_response_id"], "response-1")
        self.assertEqual(agent.client.responses.requests[1]["input"][0]["type"], "function_call_output")
