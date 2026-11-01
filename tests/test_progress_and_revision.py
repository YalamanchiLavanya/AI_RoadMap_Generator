"""Progress tracking, export/import, and roadmap-revision state changes."""
import json
import unittest

from tests.helpers import (
    FakeClient, Sleeper, TEST_SETTINGS, clone, make_plan, make_profile, plan_script,
)

import prompts
import progress
from roadmap_engine import (
    PlanValidationError,
    generate_roadmap,
    plan_to_markdown,
    revise_roadmap,
)


def loaded_state(weeks=4, hours=8):
    state = {}
    progress.init_state(state)
    plan = make_plan(weeks, hours)
    progress.load_plan(state, plan, make_profile(hours_per_week=hours, duration_weeks=weeks).to_dict())
    return state


def revised_plan_json(plan, *, hours=None, summary=("Week 2: shortened practice",)):
    revised = clone(plan)
    revised["weeks"][1]["activities"][1] = {"task": "Short practice set", "type": "practice", "hours": 2}
    if hours:
        revised["constraints"]["hours_per_week"] = hours
    revised["change_summary"] = list(summary)
    return revised


class Tasks(unittest.TestCase):
    def test_tasks_are_built_from_activities_and_milestones(self):
        tasks = progress.tasks_from_plan(make_plan(4, 8))
        self.assertEqual(len(tasks), 4 * 3)  # 2 activities + 1 milestone per week
        self.assertEqual(tasks[0]["id"], "w1-1")
        self.assertEqual(tasks[2]["type"], "milestone")
        self.assertTrue(all(not t["done"] for t in tasks))

    def test_stats_and_current_week(self):
        state = loaded_state()
        for task in state["tasks"][:3]:  # all of week 1
            task["done"] = True
        state["tasks"][3]["done"] = True  # one task of week 2
        stats = progress.progress_stats(state["tasks"])
        self.assertEqual((stats["done"], stats["total"], stats["percent"]), (4, 12, 33))
        self.assertEqual(stats["current_week"], 2)
        self.assertEqual(stats["per_week"][1], {"done": 3, "total": 3})

    def test_custom_tasks_validate_and_deduplicate(self):
        tasks = []
        self.assertEqual(progress.add_custom_task(tasks, "  ")[0], False)
        self.assertEqual(progress.add_custom_task(tasks, "Read a blog", 2)[0], True)
        self.assertEqual(progress.add_custom_task(tasks, "read   a BLOG", 2), (False, "This task already exists."))
        self.assertEqual(progress.add_custom_task(tasks, "Read a blog")[0], True)  # different week scope
        self.assertEqual([t["id"] for t in tasks], ["c1", "c2"])

    def test_summary_text_lists_completed_and_open_tasks(self):
        state = loaded_state()
        state["tasks"][0]["done"] = True
        text = progress.progress_summary_text(state["tasks"])
        self.assertIn("1 of 12 tasks done", text)
        self.assertIn("Completed tasks: Study topic 1", text)
        self.assertIn("Open tasks:", text)
        self.assertNotIn("behind schedule", text)

    def test_coach_prompt_receives_completion_status(self):
        state = loaded_state()
        state["tasks"][0]["done"] = True
        messages = prompts.build_chat_messages(
            "outline text", progress.progress_summary_text(state["tasks"]), [], "Am I on track?"
        )
        context = messages[1]["content"]
        self.assertIn("Completed tasks: Study topic 1", context)
        self.assertEqual(messages[-1]["content"], "Am I on track?")

    def test_ui_only_notes_are_not_sent_to_the_model(self):
        history = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "applied!", "kind": "note"},
            {"role": "assistant", "content": "hello"},
        ]
        self.assertEqual([m["content"] for m in prompts.history_for_llm(history)], ["hi", "hello"])


class ExportImport(unittest.TestCase):
    def test_round_trip_keeps_plan_progress_and_custom_tasks(self):
        state = loaded_state()
        state["tasks"][0]["done"] = True
        progress.add_custom_task(state["tasks"], "My own task", 3)
        state["tasks"][-1]["done"] = True

        restored = progress.import_progress(progress.export_progress(state))
        self.assertEqual(restored["plan"]["weeks"], state["roadmap_plan"]["weeks"])
        self.assertEqual(restored["profile"]["goal"], "Learn SQL for reporting")
        done = {t["name"] for t in restored["tasks"] if t["done"]}
        self.assertEqual(done, {"Study topic 1", "My own task"})

    def test_import_into_a_new_session_restores_everything(self):
        source = loaded_state()
        source["tasks"][1]["done"] = True
        fresh = {}
        progress.init_state(fresh)
        progress.load_imported(fresh, progress.import_progress(progress.export_progress(source)))
        self.assertEqual(fresh["roadmap_plan"]["weeks"], source["roadmap_plan"]["weeks"])
        self.assertTrue(fresh["tasks"][1]["done"])

    def test_bad_files_are_rejected_with_clear_messages(self):
        good = json.loads(progress.export_progress(loaded_state()))
        broken_plan = clone(good)
        broken_plan["plan"]["weeks"][0]["milestone"] = ""
        wrong_version = {**good, "schema_version": 99}
        wrong_app = {**good, "app": "something-else"}
        cases = {
            "not json": "{{{",
            "wrong app": json.dumps(wrong_app),
            "wrong version": json.dumps(wrong_version),
            "invalid plan": json.dumps(broken_plan),
            "no plan": json.dumps({**good, "plan": None}),
        }
        for name, text in cases.items():
            with self.subTest(name), self.assertRaises(progress.ProgressImportError):
                progress.import_progress(text)

    def test_tampered_done_flags_cannot_invent_tasks(self):
        data = json.loads(progress.export_progress(loaded_state()))
        data["tasks"].append({"id": "x", "week": 1, "name": "Injected", "done": True, "source": "plan"})
        restored = progress.import_progress(json.dumps(data))
        self.assertNotIn("Injected", [t["name"] for t in restored["tasks"]])


class RevisionFlow(unittest.TestCase):
    def draft(self, state, scripts, instruction="Cut week 2 practice", **kwargs):
        client = FakeClient(scripts)
        revision = revise_roadmap(
            client, state["roadmap_plan"], state["plan_profile"], instruction,
            settings=TEST_SETTINGS, sleep=Sleeper(), **kwargs,
        )
        return client, revision

    def test_drafting_does_not_change_the_displayed_plan(self):
        state = loaded_state()
        before = plan_to_markdown(state["roadmap_plan"], state["plan_profile"])
        _, revision = self.draft(state, [plan_script(revised_plan_json(state["roadmap_plan"]))])
        progress.stage_revision(state, revision, "Cut week 2 practice")
        self.assertEqual(plan_to_markdown(state["roadmap_plan"], state["plan_profile"]), before)
        self.assertIsNotNone(state["pending_revision"])
        self.assertEqual(revision.changed_weeks, [2])
        self.assertEqual(revision.change_summary, ["Week 2: shortened practice"])

    def test_apply_updates_display_download_and_tracker_together(self):
        state = loaded_state()
        state["tasks"][0]["done"] = True  # week 1 task completed before the revision
        _, revision = self.draft(state, [plan_script(revised_plan_json(state["roadmap_plan"]))])
        progress.stage_revision(state, revision, "Cut week 2 practice")
        progress.apply_pending_revision(state)

        markdown = progress.plan_markdown_for_state(state)
        self.assertIn("Short practice set", markdown)
        self.assertNotIn("Practice topic 2", markdown)
        task_names = [t["name"] for t in state["tasks"]]
        self.assertIn("Short practice set", task_names)
        self.assertNotIn("Practice topic 2", task_names)
        # the same plan feeds the download text, the tracker and the export file
        exported = json.loads(progress.export_progress(state))
        self.assertEqual(exported["plan"]["weeks"], state["roadmap_plan"]["weeks"])
        self.assertEqual(exported["plan_version"], 2)

    def test_completed_tasks_survive_a_revision(self):
        state = loaded_state()
        state["tasks"][0]["done"] = True
        progress.add_custom_task(state["tasks"], "Own task", 1)
        _, revision = self.draft(state, [plan_script(revised_plan_json(state["roadmap_plan"]))])
        progress.stage_revision(state, revision, "x")
        progress.apply_pending_revision(state)
        by_name = {t["name"]: t["done"] for t in state["tasks"]}
        self.assertTrue(by_name["Study topic 1"])
        self.assertFalse(by_name["Short practice set"])
        self.assertIn("Own task", by_name)

    def test_apply_adds_a_ui_note_and_clears_the_pending_draft(self):
        state = loaded_state()
        _, revision = self.draft(state, [plan_script(revised_plan_json(state["roadmap_plan"]))])
        progress.stage_revision(state, revision, "x")
        progress.apply_pending_revision(state)
        self.assertIsNone(state["pending_revision"])
        self.assertEqual(state["messages"][-1]["kind"], "note")
        self.assertIn("version 2", state["messages"][-1]["content"])

    def test_discard_leaves_everything_unchanged(self):
        state = loaded_state()
        original = clone(state["roadmap_plan"])
        _, revision = self.draft(state, [plan_script(revised_plan_json(state["roadmap_plan"]))])
        progress.stage_revision(state, revision, "x")
        progress.discard_pending_revision(state)
        self.assertEqual(state["roadmap_plan"], original)
        self.assertEqual(state["plan_version"], 1)
        with self.assertRaises(ValueError):
            progress.apply_pending_revision(state)

    def test_a_revision_may_lower_the_weekly_hours(self):
        state = loaded_state(4, 8)
        revised = clone(state["roadmap_plan"])
        for week in revised["weeks"]:
            week["activities"] = [{"task": f"Core task {week['week']}", "type": "learn", "hours": 5}]
        revised["constraints"]["hours_per_week"] = 5
        revised["change_summary"] = ["All weeks cut to 5 h"]
        _, revision = self.draft(state, [plan_script(revised)], instruction="I only have 5 hours a week now")
        progress.stage_revision(state, revision, "x")
        progress.apply_pending_revision(state)
        self.assertEqual(state["plan_profile"]["hours_per_week"], 5)
        self.assertEqual(state["roadmap_plan"]["constraints"]["hours_per_week"], 5)

    def test_revision_that_breaks_the_new_limit_is_rejected_and_state_is_untouched(self):
        state = loaded_state(4, 8)
        original = clone(state["roadmap_plan"])
        too_long = clone(original)
        too_long["constraints"]["hours_per_week"] = 5  # but the weeks still use 8 h
        with self.assertRaises(PlanValidationError):
            self.draft(state, [plan_script(too_long), plan_script(too_long)])
        self.assertEqual(state["roadmap_plan"], original)
        self.assertIsNone(state["pending_revision"])

    def test_revision_prompt_contains_progress_request_and_plan(self):
        state = loaded_state()
        state["tasks"][0]["done"] = True
        client, _ = self.draft(
            state, [plan_script(revised_plan_json(state["roadmap_plan"]))],
            instruction="Make week 2 lighter", progress_text=progress.progress_summary_text(state["tasks"]),
            history=[{"role": "user", "content": "Week 2 feels heavy"}],
        )
        prompt = client.calls[0]["contents"][0]["parts"][0]["text"]
        self.assertIn("Make week 2 lighter", prompt)
        self.assertIn("Completed tasks: Study topic 1", prompt)
        self.assertIn("Week 2 feels heavy", prompt)
        self.assertIn("Study topic 2", prompt)

    def test_empty_instruction_is_rejected(self):
        with self.assertRaises(ValueError):
            revise_roadmap(
                FakeClient([]), make_plan(), make_profile().to_dict(), "  ", settings=TEST_SETTINGS
            )

    def test_new_generation_resets_chat_tasks_and_draft(self):
        state = loaded_state()
        state["messages"].append({"role": "user", "content": "hi"})
        state["tasks"][0]["done"] = True
        state["pending_revision"] = {"plan": {}}
        client = FakeClient([plan_script(make_plan(4, 8))])
        result = generate_roadmap(client, make_profile(), settings=TEST_SETTINGS, sleep=Sleeper())
        progress.load_plan(state, result.plan, make_profile().to_dict())
        self.assertEqual(state["messages"], [])
        self.assertIsNone(state["pending_revision"])
        self.assertFalse(any(t["done"] for t in state["tasks"]))


if __name__ == "__main__":
    unittest.main()
