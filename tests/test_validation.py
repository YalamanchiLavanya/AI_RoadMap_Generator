"""Plan validation, JSON parsing, and the generate_roadmap() pipeline."""
import json
import unittest

from tests.helpers import (
    FakeClient, Sleeper, TEST_SETTINGS, clone, make_plan, make_profile, plan_script, split_text,
)

from roadmap_engine import (
    GenerationError,
    PlanParseError,
    PlanValidationError,
    assess_time_budget,
    extract_json,
    fit_hours_to_budget,
    generate_roadmap,
    normalize_plan,
    validate_plan,
    week_hours,
)


class ValidatePlan(unittest.TestCase):
    def test_valid_plan_passes(self):
        result = validate_plan(make_plan(4, 8), 8, 4)
        self.assertTrue(result.ok, result.errors)

    def test_wrong_number_of_weeks(self):
        result = validate_plan(make_plan(3, 8), 8, 4)
        self.assertTrue(any("exactly 4 weeks" in e for e in result.errors))

    def test_week_over_the_hour_limit(self):
        plan = make_plan(4, 8)
        plan["weeks"][1]["activities"][0]["hours"] = 9
        result = validate_plan(plan, 8, 4)
        self.assertTrue(any("Week 2 uses 13 h" in e and "limit is 8 h" in e for e in result.errors))

    def test_missing_milestone_and_activities(self):
        plan = make_plan(4, 8)
        plan["weeks"][0]["milestone"] = ""
        plan["weeks"][2]["activities"] = []
        errors = " ".join(validate_plan(plan, 8, 4).errors)
        self.assertIn("Week 1 has no milestone", errors)
        self.assertIn("Week 3 has no activities", errors)

    def test_missing_sections_are_reported(self):
        plan = make_plan(4, 8)
        for key in ("overview", "skill_gaps", "portfolio_project", "next_steps"):
            plan.pop(key)
        errors = " ".join(validate_plan(plan, 8, 4).errors)
        for fragment in ("overview", "skill_gaps", "portfolio_project", "next_steps"):
            self.assertIn(fragment, errors)

    def test_week_numbers_must_be_in_order(self):
        plan = make_plan(4, 8)
        plan["weeks"][1]["week"] = 5
        self.assertTrue(any("Week numbers" in e for e in validate_plan(plan, 8, 4).errors))

    def test_unrealistic_goal_must_say_what_is_achievable(self):
        plan = make_plan(4, 8, realistic=False)
        plan["feasibility"]["achievable_outcome"] = ""
        self.assertTrue(any("achievable_outcome" in e for e in validate_plan(plan, 8, 4).errors))
        plan["feasibility"]["achievable_outcome"] = "Write basic queries."
        self.assertTrue(validate_plan(plan, 8, 4).ok)

    def test_plan_without_any_resources_fails(self):
        plan = make_plan(4, 8)
        for week in plan["weeks"]:
            week["resources"] = []
        self.assertTrue(any("no learning resources" in e for e in validate_plan(plan, 8, 4).errors))

    def test_underused_week_is_only_a_warning(self):
        result = validate_plan(make_plan(4, 8, per_week=2), 8, 4)
        self.assertTrue(result.ok)
        self.assertTrue(any("uses only" in w for w in result.warnings))

    def test_limits_are_checked(self):
        self.assertFalse(validate_plan(make_plan(4, 8), 99, 4).ok)
        self.assertFalse(validate_plan(make_plan(4, 8), 8, 99).ok)


class FitHours(unittest.TestCase):
    def test_small_overage_is_scaled_down_and_reported(self):
        plan = make_plan(4, 8)
        plan["weeks"][0]["activities"][0]["hours"] = 4.5  # week total 8.5 (6% over)
        notes = fit_hours_to_budget(plan, 8)
        self.assertLessEqual(week_hours(plan["weeks"][0]), 8)
        self.assertEqual(len(notes), 1)
        self.assertIn("Week 1", notes[0])

    def test_large_overage_is_left_for_validation(self):
        plan = make_plan(4, 8)
        plan["weeks"][0]["activities"][0]["hours"] = 9
        self.assertEqual(fit_hours_to_budget(plan, 8), [])
        self.assertGreater(week_hours(plan["weeks"][0]), 8)


class ParsingAndNormalising(unittest.TestCase):
    def test_extract_json_handles_fences_and_prose(self):
        self.assertEqual(extract_json('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(extract_json('Here you go: {"a": 1} Enjoy'), {"a": 1})

    def test_extract_json_rejects_garbage_and_truncation(self):
        for text in ("no json here", '{"weeks": [{"week": 1,', ""):
            with self.subTest(text=text), self.assertRaises(PlanParseError):
                extract_json(text)

    def test_normalize_coerces_loose_types(self):
        raw = make_plan(2, 8)
        raw["weeks"][0]["activities"][0].update({"hours": "2.5h", "type": "WATCH"})
        raw["weeks"][0]["resources"][0]["url"] = "null"
        raw["feasibility"]["realistic"] = "true"
        plan, _ = normalize_plan(raw)
        activity = plan["weeks"][0]["activities"][0]
        self.assertEqual(activity["hours"], 2.5)
        self.assertEqual(activity["type"], "learn")
        self.assertIsNone(plan["weeks"][0]["resources"][0]["url"])
        self.assertIs(plan["feasibility"]["realistic"], True)


class TimeBudget(unittest.TestCase):
    def test_job_ready_goal_with_few_hours_is_flagged(self):
        note = assess_time_budget(make_profile(goal="Become a Data Analyst", hours_per_week=8, duration_weeks=8))
        self.assertIn("64 hours", note)
        self.assertIn("NOT realistic", note)

    def test_small_skill_goal_is_not_flagged(self):
        self.assertIsNone(assess_time_budget(make_profile(goal="Learn Python basics", hours_per_week=4, duration_weeks=4)))

    def test_enough_hours_is_not_flagged(self):
        profile = make_profile(goal="Become a Data Analyst", hours_per_week=20, duration_weeks=16, level="Intermediate")
        self.assertIsNone(assess_time_budget(profile))


class GenerateRoadmap(unittest.TestCase):
    def generate(self, scripts, profile=None, **kwargs):
        client = FakeClient(scripts)
        result = generate_roadmap(
            client, profile or make_profile(), settings=TEST_SETTINGS, sleep=Sleeper(), **kwargs
        )
        return client, result

    def test_valid_plan_on_first_try(self):
        client, result = self.generate([plan_script(make_plan(4, 8))])
        self.assertEqual(len(client.calls), 1)
        self.assertFalse(result.repaired)
        self.assertEqual(len(result.plan["weeks"]), 4)
        self.assertEqual(result.plan["constraints"], {"hours_per_week": 8, "duration_weeks": 4})

    def test_prompt_states_limits_and_asks_for_json(self):
        client, _ = self.generate([plan_script(make_plan(4, 8))])
        prompt = client.calls[0]["contents"][0]["parts"][0]["text"]
        self.assertIn("hard limit): 8", prompt)
        self.assertIn("return exactly 4 weeks", prompt)
        self.assertEqual(client.calls[0]["config"]["response_mime_type"], "application/json")

    def test_invalid_plan_is_repaired_once(self):
        bad = make_plan(4, 8)
        bad["weeks"][2]["activities"][0]["hours"] = 12  # far over the limit
        client, result = self.generate([plan_script(bad), plan_script(make_plan(4, 8))])
        self.assertEqual(len(client.calls), 2)
        self.assertTrue(result.repaired)
        repair_prompt = client.calls[1]["contents"][-1]["parts"][0]["text"]
        self.assertIn("Week 3 uses", repair_prompt)

    def test_plan_that_stays_invalid_is_rejected_not_shown(self):
        bad = make_plan(4, 8)
        bad["weeks"][0]["milestone"] = ""
        with self.assertRaises(PlanValidationError) as caught:
            self.generate([plan_script(bad), plan_script(bad)])
        self.assertTrue(any("Week 1 has no milestone" in e for e in caught.exception.errors))

    def test_truncated_json_triggers_a_repair_request(self):
        truncated = split_text(json.dumps(make_plan(4, 8)))[:2]
        client, result = self.generate([truncated, plan_script(make_plan(4, 8))])
        self.assertEqual(len(client.calls), 2)
        self.assertIn("not valid JSON", client.calls[1]["contents"][-1]["parts"][0]["text"])
        self.assertTrue(result.repaired)

    def test_slightly_over_hours_are_fixed_without_another_model_call(self):
        plan = make_plan(4, 8)
        plan["weeks"][1]["activities"][0]["hours"] = 4.5
        client, result = self.generate([plan_script(plan)])
        self.assertEqual(len(client.calls), 1)
        self.assertTrue(any("Week 2" in n for n in result.notes))
        self.assertLessEqual(week_hours(result.plan["weeks"][1]), 8)

    def test_unrealistic_target_prompt_and_result(self):
        profile = make_profile(goal="Become a Data Analyst", hours_per_week=8, duration_weeks=4)
        client, result = self.generate([plan_script(make_plan(4, 8, realistic=False))], profile)
        prompt = client.calls[0]["contents"][0]["parts"][0]["text"]
        self.assertIn("probably NOT realistic", prompt)
        self.assertFalse(result.plan["feasibility"]["realistic"])
        self.assertTrue(result.plan["feasibility"]["achievable_outcome"])
        self.assertEqual(result.warnings, [])

    def test_model_calling_an_unrealistic_goal_realistic_raises_a_warning(self):
        profile = make_profile(goal="Become a Data Analyst", hours_per_week=8, duration_weeks=4)
        _, result = self.generate([plan_script(make_plan(4, 8, realistic=True))], profile)
        self.assertTrue(any("looks small" in w for w in result.warnings))

    def test_invalid_profile_is_rejected_before_calling_the_model(self):
        client = FakeClient([])
        with self.assertRaises(ValueError):
            generate_roadmap(client, make_profile(goal="  "), settings=TEST_SETTINGS)
        self.assertEqual(client.calls, [])

    def test_api_failure_surfaces_a_friendly_error(self):
        with self.assertRaises(GenerationError) as caught:
            self.generate([RuntimeError("401 API key not valid")])
        self.assertIn("API key", str(caught.exception))

    def test_interrupted_stream_never_produces_a_duplicated_plan(self):
        pieces = plan_script(make_plan(4, 8))
        interrupted = pieces[:1] + [RuntimeError("503 unavailable")]
        client, result = self.generate([interrupted, plan_script(make_plan(4, 8))])
        self.assertEqual(len(client.calls), 2)
        self.assertEqual([w["week"] for w in result.plan["weeks"]], [1, 2, 3, 4])

    def test_source_pages_are_limited_to_retrieved_pages(self):
        plan = make_plan(4, 8)
        plan["weeks"][0]["source_pages"] = [2, 99]
        hits = [{"source": "syllabus.pdf", "page": 2, "text": "SQL basics", "score": 0.5}]
        _, result = self.generate([plan_script(plan)], hits=hits)
        self.assertEqual(result.plan["weeks"][0]["source_pages"], [2])
        self.assertEqual(result.plan["reference"], {"filename": "syllabus.pdf", "pages": [2]})

    def test_page_references_are_dropped_when_no_pdf_was_used(self):
        plan = make_plan(4, 8)
        plan["weeks"][0]["source_pages"] = [3]
        _, result = self.generate([plan_script(plan)])
        self.assertEqual(result.plan["weeks"][0]["source_pages"], [])
        self.assertNotIn("reference", result.plan)


if __name__ == "__main__":
    unittest.main()
