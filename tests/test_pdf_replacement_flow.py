"""Integration: PDF A -> replaced by PDF B -> removed, across rag_system + coach_context."""
import unittest

import coach_context as cc
import rag_system as rag
from tests.helpers import fake_embed, make_pdf

PDF_A = make_pdf([
    "Zebra handbook page one explains zebra stripes and savanna migration routes.",
    "Zebra handbook page two lists zebra herd behaviour and watering holes.",
])
PDF_B = make_pdf([
    "Quokka guide page one describes quokka habitat on Rottnest Island.",
    "Quokka guide page two covers quokka diet and breeding seasons.",
])


def index_for(data, name):
    return rag.build_pdf_index(data, name, embed_fn=fake_embed)


def sent_to_model(messages, state, uploaded_hash):
    """Mimic app.py: sync the uploader with the index, then filter coach history."""
    rag.sync_pdf_state(state, uploaded_hash)
    index = rag.get_pdf_index(state)
    active_hash = uploaded_hash if index is not None else None
    return " ".join(m["content"] for m in cc.model_history(messages, active_hash))


class ReplacementFlow(unittest.TestCase):
    def test_pdf_a_then_b_then_removed(self):
        state, messages = {}, []

        # Stage 1: PDF A indexed, coach answers from it
        a = index_for(PDF_A, "zebra.pdf")
        rag.set_pdf_index(state, a)
        hits_a = rag.retrieve(state, "zebra stripes savanna migration")
        self.assertTrue(hits_a)
        self.assertEqual({h["source"] for h in hits_a}, {"zebra.pdf"})
        messages += [
            {"role": "user", "content": "General: how many hours per week?"},
            {"role": "assistant", "content": "ZEBRA-FACT from A (zebra.pdf, p. 1)",
             "doc_hash": a.file_hash, "doc_name": "zebra.pdf"},
        ]
        self.assertIn("ZEBRA-FACT", sent_to_model(messages, state, a.file_hash))

        # Stage 2: user selects PDF B in the uploader (not indexed yet)
        b_hash = rag.file_digest(PDF_B)
        text = sent_to_model(messages, state, b_hash)
        self.assertIsNone(rag.get_pdf_index(state))
        self.assertEqual(rag.retrieve(state, "zebra stripes"), [])
        self.assertNotIn("ZEBRA-FACT", text)
        self.assertIn("General", text)

        # Stage 3: B indexed; A is unreachable and not sent to the model
        b = index_for(PDF_B, "quokka.pdf")
        rag.set_pdf_index(state, b)
        self.assertEqual(rag.retrieve(state, "zebra stripes savanna migration"), [])
        hits_b = rag.retrieve(state, "quokka habitat Rottnest Island")
        self.assertEqual({h["source"] for h in hits_b}, {"quokka.pdf"})
        messages += [{"role": "assistant", "content": "QUOKKA-FACT from B (quokka.pdf, p. 1)",
                      "doc_hash": b.file_hash, "doc_name": "quokka.pdf"}]
        text = sent_to_model(messages, state, b.file_hash)
        self.assertIn("QUOKKA-FACT", text)
        self.assertNotIn("ZEBRA-FACT", text)
        self.assertIn("General", text)

        # A citation to the old file is rejected against B's hits
        out = cc.validate_coach_citations(
            "x (zebra.pdf, p. 1) y (quokka.pdf, p. 1)", hits_b, b.file_hash)
        self.assertNotIn("(zebra.pdf, p. 1)", out)
        self.assertIn("(quokka.pdf, p. 1)", out)

        # Stage 4: PDF removed; nothing document-derived remains
        text = sent_to_model(messages, state, None)
        self.assertIsNone(rag.get_pdf_index(state))
        self.assertEqual(rag.retrieve(state, "quokka habitat"), [])
        self.assertNotIn("QUOKKA-FACT", text)
        self.assertNotIn("ZEBRA-FACT", text)
        self.assertIn("General", text)

    def test_removal_with_no_prior_pdf_is_harmless(self):
        state = {}
        self.assertEqual(sent_to_model([{"role": "user", "content": "hi"}], state, None), "hi")


if __name__ == "__main__":
    unittest.main()