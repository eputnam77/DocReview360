import docreview360.search as search


def test_match_all_terms_respects_word_boundaries():
    # Basic positive case for sanity
    assert search._match_all_terms("a cat on a mat", ["cat"])
    # Previously a search for "cat" would match the word "scatter" because the
    # implementation used simple substring checks.  The corrected behavior
    # tokenises the text so partial matches do not count.
    assert not search._match_all_terms("scatter", ["cat"])
