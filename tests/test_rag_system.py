"""PDF extraction, page references, retrieval, replacement and removal."""
import unittest

from tests.helpers import fake_embed, make_pdf, make_profile

import prompts
import rag_system as rag

SYLLABUS = make_pdf([
    "Module one covers python variables loops functions and basic syntax for beginners.",
    "Module two covers sql databases joins aggregation and query optimisation exercises.",
    "Prerequisites include statistics probability and linear algebra before machine learning.",
])
OTHER = make_pdf([
    "Welcome to the cooking handbook with pasta sauces and baking bread at home.",
    "Chapter two lists spices herbs and kitchen equipment for new cooks.",
])


def build(data=SYLLABUS, name="syllabus.pdf"):
    return rag.build_pdf_index(data, name, embed_fn=fake_embed)


class Extraction(unittest.TestCase):
    def test_pages_keep_their_numbers(self):
        extracted = rag.extract_pages(SYLLABUS)
        self.assertEqual(extracted.page_count, 3)
        self.assertEqual([p.number for p in extracted.pages], [1, 2, 3])
        self.assertIn("sql databases", extracted.pages[1].text)

    def test_blank_pages_are_skipped_but_numbering_is_preserved(self):
        extracted = rag.extract_pages(make_pdf(["", "Only the second page has text about gardening."]))
        self.assertEqual([p.number for p in extracted.pages], [2])
        self.assertEqual(extracted.page_count, 2)

    def test_pdf_without_text_gives_a_clear_error(self):
        with self.assertRaises(rag.PdfError) as caught:
            rag.extract_pages(make_pdf(["", ""]))
        self.assertIn("No extractable text", str(caught.exception))

    def test_non_pdf_bytes_give_a_clear_error(self):
        with self.assertRaises(rag.PdfError):
            rag.extract_pages(b"this is not a pdf")

    def test_chunks_never_cross_pages_and_overlap(self):
        pages = [rag.PageText(1, "a" * 2000), rag.PageText(2, "b" * 300)]
        chunks = rag.chunk_pages(pages, size=900, overlap=150)
        self.assertTrue(all(set(c["text"]) <= {"a"} for c in chunks if c["page"] == 1))
        self.assertTrue(all(set(c["text"]) <= {"b"} for c in chunks if c["page"] == 2))
        self.assertEqual([c["page"] for c in chunks], [1, 1, 1, 2])

    def test_bad_chunk_settings_are_rejected(self):
        with self.assertRaises(ValueError):
            rag.chunk_pages([rag.PageText(1, "x")], size=100, overlap=100)


class Retrieval(unittest.TestCase):
    def test_hits_carry_filename_and_page(self):
        index = build()
        hits = index.search("prerequisites statistics probability linear algebra")
        self.assertEqual(hits[0]["page"], 3)
        self.assertEqual(hits[0]["source"], "syllabus.pdf")
        self.assertGreater(hits[0]["score"], 0.15)

    def test_each_topic_maps_to_its_own_page(self):
        index = build()
        self.assertEqual(index.search("sql joins aggregation")[0]["page"], 2)
        self.assertEqual(index.search("python variables loops")[0]["page"], 1)

    def test_unrelated_question_returns_nothing(self):
        self.assertEqual(build().search("quantum chromodynamics lattice gauge"), [])

    def test_blank_query_returns_nothing(self):
        self.assertEqual(build().search("   "), [])

    def test_numpy_fallback_is_reported(self):
        self.assertIn(build().backend, ("numpy", "faiss"))

    def test_sources_summary_and_prompt_formatting_include_pages(self):
        hits = build().search("sql joins aggregation prerequisites statistics", top_k=3)
        summary = rag.summarize_sources(hits)
        self.assertIn("syllabus.pdf p.", summary)
        formatted = prompts.format_reference_excerpts(hits)
        self.assertIn("syllabus.pdf, p. 2", formatted)
        self.assertIn("not instructions", formatted)

    def test_generation_retrieval_uses_the_goal_and_orders_by_page(self):
        state = {}
        rag.set_pdf_index(state, build())
        profile = make_profile(goal="machine learning with python", current_skills="statistics")
        hits = rag.retrieve_for_generation(state, profile)
        self.assertTrue(hits)
        self.assertEqual([h["page"] for h in hits], sorted(h["page"] for h in hits))


class ReplaceAndRemove(unittest.TestCase):
    def test_replacing_a_document_removes_all_old_content(self):
        state = {}
        self.assertIsNone(rag.set_pdf_index(state, build(SYLLABUS, "syllabus.pdf")))
        self.assertEqual(rag.set_pdf_index(state, build(OTHER, "cooking.pdf")), "syllabus.pdf")
        self.assertEqual(rag.retrieve(state, "sql joins aggregation"), [])
        hits = rag.retrieve(state, "pasta sauces baking bread")
        self.assertEqual({h["source"] for h in hits}, {"cooking.pdf"})

    def test_removing_the_uploaded_file_clears_the_index(self):
        state = {}
        index = build()
        rag.set_pdf_index(state, index)
        self.assertEqual(rag.sync_pdf_state(state, index.file_hash), "current")
        self.assertEqual(rag.sync_pdf_state(state, None), "removed")
        self.assertIsNone(rag.get_pdf_index(state))
        self.assertEqual(rag.retrieve(state, "sql joins"), [])

    def test_selecting_a_different_file_clears_the_old_index_immediately(self):
        state = {}
        rag.set_pdf_index(state, build())
        self.assertEqual(rag.sync_pdf_state(state, rag.file_digest(OTHER)), "replaced")
        self.assertIsNone(rag.get_pdf_index(state))

    def test_same_name_but_changed_content_counts_as_replaced(self):
        state = {}
        rag.set_pdf_index(state, build(SYLLABUS, "notes.pdf"))
        self.assertEqual(rag.sync_pdf_state(state, rag.file_digest(OTHER)), "replaced")

    def test_nothing_indexed_means_nothing_to_sync(self):
        self.assertEqual(rag.sync_pdf_state({}, None), "none")
        self.assertEqual(rag.sync_pdf_state({}, "abc"), "none")

    def test_clear_reports_what_was_removed(self):
        state = {}
        rag.set_pdf_index(state, build())
        self.assertEqual(rag.clear_pdf_index(state), "syllabus.pdf")
        self.assertIsNone(rag.clear_pdf_index(state))


if __name__ == "__main__":
    unittest.main()
