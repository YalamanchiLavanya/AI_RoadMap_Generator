"""Streaming and retry behaviour of generate_response() / collect_text()."""
import unittest

from tests.helpers import FakeClient, Sleeper, TEST_SETTINGS

from roadmap_engine import (
    GenerationError,
    StreamInterruptedError,
    collect_text,
    friendly_error_message,
    generate_response,
    is_retryable_error,
    split_messages,
)

MESSAGES = [
    {"role": "system", "content": "You are a coach."},
    {"role": "user", "content": "Make a plan."},
]


def run(client, sleeper=None, **kwargs):
    sleeper = sleeper or Sleeper()
    return list(generate_response(client, MESSAGES, settings=TEST_SETTINGS, sleep=sleeper, **kwargs))


class RetryRules(unittest.TestCase):
    def test_retry_happens_when_failure_comes_before_any_text(self):
        client = FakeClient([RuntimeError("503 Service Unavailable"), ["Hello ", "world"]])
        sleeper = Sleeper()
        pieces = run(client, sleeper)
        self.assertEqual("".join(pieces), "Hello world")
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(sleeper.delays, [1.0])

    def test_failure_after_text_is_not_retried_and_nothing_repeats(self):
        """Regression: a retry used to start the answer again after text had appeared."""
        client = FakeClient([
            ["Week 1: Python basics\n", RuntimeError("503 unavailable")],
            ["Week 1: Python basics\n", "Week 2: Pandas\n"],  # must never be requested
        ])
        received = []
        with self.assertRaises(StreamInterruptedError) as caught:
            for piece in generate_response(client, MESSAGES, settings=TEST_SETTINGS, sleep=Sleeper()):
                received.append(piece)
        self.assertEqual(len(client.calls), 1, "no automatic restart after text was emitted")
        self.assertEqual("".join(received).count("Week 1"), 1)
        self.assertEqual(caught.exception.partial_text, "Week 1: Python basics\n")

    def test_collect_text_clears_partial_output_before_restarting(self):
        client = FakeClient([
            ["Week 1: Python basics\n", RuntimeError("503 unavailable")],
            ["Week 1: Python basics\n", "Week 2: Pandas\n"],
        ])
        resets, shown = [], []
        text = collect_text(
            client, MESSAGES, settings=TEST_SETTINGS, sleep=Sleeper(),
            on_chunk=shown.append, on_reset=lambda: resets.append(True),
        )
        self.assertEqual(text, "Week 1: Python basics\nWeek 2: Pandas\n")
        self.assertEqual(text.count("Week 1"), 1)
        self.assertEqual(len(resets), 1)
        self.assertEqual(shown[-1], text)

    def test_collect_text_gives_up_after_the_restart_limit(self):
        client = FakeClient([
            ["partial one", RuntimeError("503")],
            ["partial two", RuntimeError("503")],
        ])
        with self.assertRaises(StreamInterruptedError) as caught:
            collect_text(client, MESSAGES, settings=TEST_SETTINGS, sleep=Sleeper(), max_restarts=1)
        self.assertEqual(caught.exception.partial_text, "partial two")

    def test_rate_limit_is_retried_then_reported_clearly(self):
        client = FakeClient([RuntimeError("429 RESOURCE_EXHAUSTED")] * 3)
        sleeper = Sleeper()
        with self.assertRaises(GenerationError) as caught:
            run(client, sleeper)
        self.assertEqual(len(client.calls), 3)
        self.assertEqual(sleeper.delays, [1.0, 2.0])
        self.assertIn("rate limit", str(caught.exception).lower())
        self.assertTrue(caught.exception.retryable)

    def test_invalid_api_key_is_not_retried(self):
        client = FakeClient([RuntimeError("403 PERMISSION_DENIED: API key not valid")])
        sleeper = Sleeper()
        with self.assertRaises(GenerationError) as caught:
            run(client, sleeper)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(sleeper.delays, [])
        self.assertIn("API key", str(caught.exception))
        self.assertFalse(caught.exception.retryable)

    def test_empty_responses_are_retried(self):
        client = FakeClient([[""], [], ["finally"]])
        self.assertEqual("".join(run(client)), "finally")
        self.assertEqual(len(client.calls), 3)

    def test_all_empty_responses_fail_with_a_clear_message(self):
        client = FakeClient([[], [], []])
        with self.assertRaises(GenerationError) as caught:
            run(client)
        self.assertIn("empty response", str(caught.exception).lower())

    def test_non_streaming_mode_works_and_retries_before_text(self):
        client = FakeClient([RuntimeError("503"), ["whole answer"]])
        self.assertEqual("".join(run(client, stream=False)), "whole answer")
        self.assertEqual(len(client.calls), 2)


class RequestShape(unittest.TestCase):
    def test_json_mode_sets_response_mime_type_and_limits(self):
        client = FakeClient([["{}"]])
        run(client, json_mode=True)
        config = client.calls[0]["config"]
        self.assertEqual(config["response_mime_type"], "application/json")
        self.assertEqual(config["max_output_tokens"], TEST_SETTINGS.max_output_tokens)
        self.assertEqual(config["system_instruction"], "You are a coach.")
        self.assertEqual(client.calls[0]["model"], "test-model")

    def test_split_messages_merges_consecutive_roles_and_extracts_system(self):
        system, contents = split_messages([
            {"role": "system", "content": "S1"},
            {"role": "user", "content": "roadmap"},
            {"role": "user", "content": "excerpts"},
            {"role": "assistant", "content": "ok"},
            {"role": "user", "content": "question"},
            {"role": "user", "content": ""},
        ])
        self.assertEqual(system, "S1")
        self.assertEqual([c["role"] for c in contents], ["user", "model", "user"])
        self.assertEqual(contents[0]["parts"][0]["text"], "roadmap\n\nexcerpts")

    def test_no_user_message_is_rejected(self):
        with self.assertRaises(ValueError):
            list(generate_response(FakeClient([]), [{"role": "system", "content": "x"}], settings=TEST_SETTINGS))


class ErrorClassification(unittest.TestCase):
    def test_retryable_and_friendly_messages(self):
        cases = [
            (RuntimeError("503 UNAVAILABLE"), True, "temporarily unavailable"),
            (RuntimeError("429 quota exceeded"), True, "rate limit"),
            (RuntimeError("404 models/foo is not found"), False, "model was not found"),
            (RuntimeError("401 API key not valid"), False, "API key"),
            (TimeoutError("timed out"), True, "network problem"),
            (RuntimeError("something odd"), False, "request failed"),
        ]
        for error, retryable, fragment in cases:
            with self.subTest(error=str(error)):
                self.assertEqual(is_retryable_error(error), retryable)
                self.assertIn(fragment.lower(), friendly_error_message(error).lower())


if __name__ == "__main__":
    unittest.main()
