import unittest
from coach_context import model_history, validate_coach_citations


class CoachContextTests(unittest.TestCase):
    def test_replaced_pdf_context_is_not_sent_to_model(self):
        msgs = [
            {"role": "user", "content": "General question"},
            {"role": "assistant", "content": "ZEBRA-ALPHA fact", "doc_hash": "A"},
            {"role": "assistant", "content": "QUOKKA-BETA fact", "doc_hash": "B"},
        ]
        sent = " ".join(m["content"] for m in model_history(msgs, "B"))
        self.assertIn("QUOKKA-BETA", sent)
        self.assertNotIn("ZEBRA-ALPHA", sent)
        self.assertIn("General", sent)   # general chat is kept

    def test_after_removal_no_document_messages_are_sent(self):
        msgs = [{"role": "assistant", "content": "ZEBRA-ALPHA", "doc_hash": "A"}]
        self.assertEqual(model_history(msgs, None), [])

    def test_invented_citation_is_removed_valid_one_kept(self):
        hits = [{"source": "guide.pdf", "page": 3}]
        ans = "Ok [source: guide.pdf, p. 3] and [source: other.pdf, p. 99]"
        out = validate_coach_citations(ans, hits, "A")
        self.assertIn("[source: guide.pdf, p. 3]", out)
        self.assertNotIn("other.pdf", out)
        self.assertIn("[unverified reference removed]", out)

    def test_citations_are_stripped_when_no_pdf_is_active(self):
        out = validate_coach_citations("Hi [source: x.pdf, p. 1]", [], None)
        self.assertNotIn("source:", out)

    def test_valid_paren_citation_is_kept(self):
        hits = [{"source": "guide.pdf", "page": 3}]
        out = validate_coach_citations("See (guide.pdf, p. 3).", hits, "A")
        self.assertIn("(guide.pdf, p. 3)", out)

    def test_invalid_paren_filename_is_removed(self):
        hits = [{"source": "guide.pdf", "page": 3}]
        out = validate_coach_citations("See (other.pdf, p. 3).", hits, "A")
        self.assertNotIn("other.pdf", out)
        self.assertIn("[unverified reference removed]", out)

    def test_invalid_paren_page_is_removed(self):
        hits = [{"source": "guide.pdf", "page": 3}]
        out = validate_coach_citations("See (guide.pdf, p. 9).", hits, "A")
        self.assertNotIn("p. 9", out)
        self.assertIn("[unverified reference removed]", out)

    def test_paren_citations_stripped_when_no_pdf_active(self):
        out = validate_coach_citations("Hi (x.pdf, p. 1) there", [], None)
        self.assertNotIn("x.pdf", out)


if __name__ == "__main__":
    unittest.main()