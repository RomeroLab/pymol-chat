import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pymol_chat.agent import PyMOLAgent, can_confirm_directly, TOOLS, MAX_TOOL_ROUNDS
from pymol_chat.executor import ExecutionResult, PyMOLExecutor


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
    def test_real_executor_silent_success_uses_shortcut(self):
        agent, _, _ = self.make_fast_agent()
        agent.executor = PyMOLExecutor()
        with (
            patch.object(agent.executor, "scene_summary", return_value={}),
            patch("pymol_chat.executor.cmd.count_atoms", return_value=10),
            patch("pymol_chat.executor.cmd.color"),
            patch("pymol_chat.executor.cmd.deselect"),
        ):
            self.assertEqual(agent.ask("Color green"), "I've colored the protein green.")
        self.assertEqual(agent.client.responses.create.call_count, 1)
        self.assertEqual(json.loads(agent.pending_outputs[0]["output"])["output"], "")

    def test_visual_tool_unavailable_even_if_requested(self):
        self.assertEqual([tool["name"] for tool in TOOLS], ["execute_pymol_python"])
        agent, response, final = self.make_fast_agent()
        response.output[0].name = "inspect_viewport"
        response.output[0].arguments = "{}"
        self.assertEqual(agent.ask("Look"), final.output_text)
        agent.executor.capture_viewport.assert_not_called()
        agent.executor.execute.assert_not_called()
        request = agent.client.responses.create.call_args.kwargs
        self.assertIn("disabled", request["input"][0]["output"])
        self.assertNotIn("input_image", json.dumps(request))

    def test_command_budget_finishes_with_text_and_retains_context(self):
        agent, response, final = self.make_fast_agent(confirmation=None)
        agent.client.responses.create.side_effect = [response] * MAX_TOOL_ROUNDS + [final]
        self.assertEqual(agent.ask("Complex request"), final.output_text)
        self.assertEqual(agent.executor.execute.call_count, MAX_TOOL_ROUNDS)
        request = agent.client.responses.create.call_args.kwargs
        self.assertEqual(request["tool_choice"], "none")
        self.assertFalse(request["parallel_tool_calls"])
        self.assertIn("unfinished", request["instructions"])
        self.assertEqual(request["input"][0]["type"], "function_call_output")
        self.assertEqual(agent.previous_response_id, final.id)

    def test_no_execution_past_command_budget(self):
        agent, response, _ = self.make_fast_agent(confirmation=None)
        agent.client.responses.create.side_effect = [response] * (MAX_TOOL_ROUNDS + 1)
        with self.assertRaisesRegex(RuntimeError, "command limit"):
            agent.ask("Keep going")
        self.assertEqual(agent.executor.execute.call_count, MAX_TOOL_ROUNDS)

    def test_reasoning_defaults_to_medium_and_allows_override(self):
        for override, expected in [(None, "medium"), ("low", "low")]:
            with self.subTest(override=override), patch.dict(os.environ), patch("pymol_chat.agent.model", return_value="gpt-5.6-sol"):
                os.environ.pop("OPENAI_REASONING_EFFORT", None)
                if override is not None:
                    os.environ["OPENAI_REASONING_EFFORT"] = override
                agent, _, _ = self.make_fast_agent()
                agent.ask("Color green")
                self.assertEqual(agent.client.responses.create.call_args.kwargs["reasoning"], {"effort": expected})

    def make_fast_agent(self, result=None, code=None, confirmation="I've colored the protein green."):
        code = code or "assert cmd.count_atoms('protein') > 0\ncmd.color('green', 'protein')"
        call = SimpleNamespace(type="function_call", name="execute_pymol_python",
            arguments=json.dumps({"code": code, "success_reply": confirmation}), call_id="call-fast")
        response = SimpleNamespace(id="fast", output=[call], output_text="")
        final = SimpleNamespace(id="final", output=[], output_text="Reviewed result.")
        agent = object.__new__(PyMOLAgent)
        agent.client = SimpleNamespace(responses=Mock())
        agent.client.responses.create.side_effect = [response, final]
        agent.executor = Mock()
        agent.executor.scene_summary.return_value = {}
        agent.executor.execute.return_value = result or ExecutionResult(True, "")
        agent.debug = Mock()
        agent.previous_response_id = None
        agent.pending_outputs = []
        return agent, response, final

    def test_fast_confirmation_and_next_turn_continuity(self):
        agent, _, _ = self.make_fast_agent()
        self.assertEqual(agent.ask("Color green"), "I've colored the protein green.")
        self.assertEqual(agent.client.responses.create.call_count, 1)
        self.assertEqual(agent.ask("What did you do?"), "Reviewed result.")
        request = agent.client.responses.create.call_args.kwargs
        self.assertEqual(request["previous_response_id"], "fast")
        self.assertEqual(request["input"][0]["call_id"], "call-fast")
        self.assertTrue(json.loads(request["input"][0]["output"])["ok"])
        self.assertEqual(request["input"][1]["role"], "assistant")
        self.assertEqual(request["input"][2]["role"], "user")
        self.assertEqual(agent.pending_outputs, [])
        messages = [call.args[0] for call in agent.debug.call_args_list]
        self.assertEqual(len(messages), 2)
        self.assertTrue(messages[0].startswith(">>> "))
        self.assertTrue(json.loads(messages[1])["ok"])

    def test_failure_output_and_measurements_require_review(self):
        for result, code, reply in [
            (ExecutionResult(False, "", "empty selection"), None, "Done"),
            (ExecutionResult(True, "distance 2.1"), None, "Done"),
            (ExecutionResult(True, ""), "assert cmd.count_atoms('protein') > 0\ncmd.distance('d','a','b')", "Done"),
            (ExecutionResult(True, ""), None, None),
        ]:
            with self.subTest(result=result, code=code, reply=reply):
                agent, _, _ = self.make_fast_agent(result, code, reply)
                self.assertEqual(agent.ask("Request"), "Reviewed result.")
                self.assertEqual(agent.client.responses.create.call_count, 2)

    def test_multiple_calls_and_repair_never_shortcut(self):
        agent, response, final = self.make_fast_agent()
        response.output.append(SimpleNamespace(**{**vars(response.output[0]), "call_id": "other"}))
        self.assertEqual(agent.ask("Change both"), "Reviewed result.")
        agent, response, final = self.make_fast_agent()
        agent.client.responses.create.side_effect = [response, response, final]
        agent.executor.execute.side_effect = [ExecutionResult(False, "", "failed"), ExecutionResult(True, "")]
        self.assertEqual(agent.ask("Change"), "Reviewed result.")
        self.assertEqual(agent.client.responses.create.call_count, 3)

    def test_pending_results_survive_network_failure(self):
        agent, _, final = self.make_fast_agent()
        agent.ask("Color green")
        saved = list(agent.pending_outputs)
        agent.client.responses.create.side_effect = [RuntimeError("offline"), final]
        with self.assertRaises(RuntimeError):
            agent.ask("Next")
        self.assertEqual(agent.previous_response_id, "fast")
        self.assertEqual(agent.pending_outputs, saved)
        agent.ask("Try again")
        self.assertEqual(agent.client.responses.create.call_args.kwargs["input"][:2], saved)

    def test_execution_results_survive_failed_followup_without_reexecution(self):
        for result in [ExecutionResult(True, "measured 4.2"), ExecutionResult(False, "partly changed", "failed")]:
            with self.subTest(result=result):
                agent, response, final = self.make_fast_agent(result=result, confirmation=None)
                agent.client.responses.create.side_effect = [response, RuntimeError("offline"), final]
                with self.assertRaisesRegex(RuntimeError, "offline"):
                    agent.ask("Change the scene")
                self.assertEqual(agent.previous_response_id, response.id)
                self.assertEqual(json.loads(agent.pending_outputs[0]["output"]), json.loads(result.as_json()))
                agent.ask("What happened?")
                self.assertEqual(agent.executor.execute.call_count, 1)
                request = agent.client.responses.create.call_args.kwargs
                self.assertEqual(request["previous_response_id"], response.id)
                self.assertEqual(request["input"][0]["call_id"], "call-fast")
                self.assertEqual(agent.pending_outputs, [])

    def test_latest_repair_results_survive_final_summary_failure(self):
        agent, response, final = self.make_fast_agent(confirmation=None)
        repair = SimpleNamespace(id="repair", output=[SimpleNamespace(**{**vars(response.output[0]), "call_id": "call-repair"})], output_text="")
        agent.client.responses.create.side_effect = [response, repair, RuntimeError("offline"), final]
        agent.executor.execute.side_effect = [ExecutionResult(False, "", "failed"), ExecutionResult(True, "repaired")]
        with self.assertRaisesRegex(RuntimeError, "offline"):
            agent.ask("Change")
        self.assertEqual(agent.previous_response_id, "repair")
        self.assertEqual(agent.pending_outputs[0]["call_id"], "call-repair")
        agent.ask("Continue")
        self.assertEqual(agent.executor.execute.call_count, 2)

    def test_shortcut_rejects_unchecked_conditional_and_async_code(self):
        for code in ["cmd.color('green','none')", "assert True\ncmd.color('green','all')", "assert True\ncmd.fetch('4hhb')",
                     "assert True\nif False: cmd.color('green','all')",
                     "assert True\nprint(cmd.count_atoms('all'))"]:
            self.assertFalse(can_confirm_directly(code))

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
