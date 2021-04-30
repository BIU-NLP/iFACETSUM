from QFSE.propositions.utils import find_indices_by_char_idx


def test_find_indices_by_char_idx__example_federal_report():
    sent_text = "'There, the murder rate of 1 for 675 residents in 1995 was twice that of New Orleans, according to a federal report last year on Indian law enforcement.'"
    sentences = ["Another sent text", sent_text]
    span_text = "the murder rate of 1 for 675 residents in 1995...according to a federal report last year on Indian law enforcement."

    sent_idx, span_start_word_idx, span_end_word_idx = find_indices_by_char_idx(sentences, sent_text, span_text)
    assert sent_idx == 1
    assert span_start_word_idx == 1
    assert span_end_word_idx == 27


def test_find_indices_by_char_idx__example_schools():
    sent_text = "'We're still behind, which is affecting our 1 schools, our students.'' Officials at Mesa Elementary estimate that fewer than half of the families with children who attend the school have phone lines to their homes, a problem for emergencies as well as Internet access."
    sentences = ["Another sent text", sent_text]
    span_text = "fewer than half of the families with children...have phone lines to their homes"

    sent_idx, span_start_word_idx, span_end_word_idx = find_indices_by_char_idx(sentences, sent_text, span_text)
    assert sent_idx == 1
    assert span_start_word_idx == 17
    assert span_end_word_idx == 34

