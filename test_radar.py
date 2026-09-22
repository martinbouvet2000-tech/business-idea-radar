#!/usr/bin/env python3
"""
Unit tests for Reddit Idea Radar
Run: python -m pytest test_radar.py -v  OR  python test_radar.py
"""

import json
import re
import unittest
from unittest.mock import patch, MagicMock

# Import functions under test
from reddit_idea_radar import (
    pre_score_thread,
    detect_cross_signals,
    validate_idea,
    classify_tiers,
)


# ============================================================================
# HELPERS
# ============================================================================

def make_thread(title="Test thread", selftext="", score=50, comments_count=30,
                top_comments=None, subreddit="testSub", thread_id="abc123"):
    """Factory for thread dicts."""
    return {
        "id": thread_id,
        "subreddit": subreddit,
        "title": title,
        "url": f"https://reddit.com/r/{subreddit}/comments/{thread_id}",
        "comments_count": comments_count,
        "score": score,
        "created_utc": 1700000000,
        "selftext": selftext,
        "top_comments": top_comments or [],
        "_priority": 2,
        "_category": "dev",
    }


def make_idea(tier=1, composite=8.5, title="Test Idea", market_signal=8,
              differentiation=8, solo_executability=9, timing=7,
              source_thread_id="t1"):
    """Factory for idea dicts."""
    return {
        "metadata": {
            "id": f"2025-01-01_{title.lower().replace(' ', '-')}",
            "scanned_date": "2025-01-01",
            "status": "new",
            "source_thread_id": source_thread_id,
        },
        "problem": {
            "title": title,
            "description": "A real problem",
            "type": "FRICTION",
            "pain_evidence": ["quote 1"],
        },
        "market": {"subreddit": "r/test", "thread_url": "https://reddit.com/r/test/1"},
        "scoring": {
            "market_signal": market_signal,
            "differentiation": differentiation,
            "solo_executability": solo_executability,
            "timing": timing,
            "composite": composite,
            "tier": tier,
        },
        "monetization": {"model": "SaaS", "price_point": "$29/month", "break_even_customers": 50},
        "next_actions": ["Contact users"],
    }


# ============================================================================
# a) PRE-SCORING
# ============================================================================

class TestPreScoring(unittest.TestCase):

    def test_pain_keywords_boost_score(self):
        """Threads with pain keywords should score higher."""
        neutral = make_thread(title="Some random discussion")
        painful = make_thread(title="I'm frustrated with this terrible tool, it's broken and annoying")
        self.assertGreater(pre_score_thread(painful), pre_score_thread(neutral))

    def test_multiple_pain_keywords_stack(self):
        """More pain keywords = higher score, capped at 30."""
        one_kw = make_thread(title="frustrated with this")
        three_kw = make_thread(title="frustrated, annoying, and broken")
        self.assertGreater(pre_score_thread(three_kw), pre_score_thread(one_kw))

    def test_noise_keywords_penalize(self):
        """Threads with noise keywords should lose points."""
        clean = make_thread(title="Need a tool for invoicing")
        noisy = make_thread(title="I built my new project, check out my launched app")
        self.assertGreater(pre_score_thread(clean), pre_score_thread(noisy))

    def test_noise_can_zero_out(self):
        """Heavy noise should bring score to 0 (clamped)."""
        very_noisy = make_thread(
            title="hiring job post looking for co-founder check out my i built launched show hn",
            score=1, comments_count=1
        )
        self.assertEqual(pre_score_thread(very_noisy), 0)

    def test_high_engagement_ratio_boosts(self):
        """High comment/vote ratio indicates discussion, should boost score."""
        low_ratio = make_thread(score=1000, comments_count=10)   # ratio 0.01
        high_ratio = make_thread(score=10, comments_count=100)   # ratio 10.0
        self.assertGreater(pre_score_thread(high_ratio), pre_score_thread(low_ratio))

    def test_high_comments_count_bonus(self):
        """50+ comments should get +10 bonus."""
        low = make_thread(comments_count=10, score=10)
        high = make_thread(comments_count=60, score=10)
        diff = pre_score_thread(high) - pre_score_thread(low)
        self.assertGreaterEqual(diff, 5)  # at least some bonus

    def test_pain_in_comments_boosts(self):
        """Comments with payment/need signals should boost score."""
        no_signal = make_thread(top_comments=[
            {"body": "This is just a regular comment about nothing", "score": 5},
        ])
        with_signal = make_thread(top_comments=[
            {"body": "I would pay for this, same problem here, need this badly", "score": 10},
            {"body": "Been looking for exactly this, tried everything", "score": 8},
        ])
        self.assertGreater(pre_score_thread(with_signal), pre_score_thread(no_signal))

    def test_upvote_tiers(self):
        """High upvotes should give incremental bonuses."""
        low = make_thread(score=10, comments_count=0)
        mid = make_thread(score=100, comments_count=0)
        high = make_thread(score=600, comments_count=0)
        s_low = pre_score_thread(low)
        s_mid = pre_score_thread(mid)
        s_high = pre_score_thread(high)
        self.assertGreater(s_high, s_mid)
        self.assertGreater(s_mid, s_low)

    def test_empty_thread_scores_low(self):
        """Empty/minimal thread should score below 20 threshold."""
        empty = make_thread(title="", selftext="", score=1, comments_count=1, top_comments=[])
        self.assertLess(pre_score_thread(empty), 20)

    def test_selftext_pain_counted(self):
        """Pain keywords in selftext (not just title) should boost."""
        title_only = make_thread(title="Help needed", selftext="")
        both = make_thread(title="Help needed", selftext="I'm frustrated, this is broken")
        self.assertGreater(pre_score_thread(both), pre_score_thread(title_only))

    def test_score_never_negative(self):
        """Score should be clamped to 0 minimum."""
        terrible = make_thread(
            title="hiring job post ama meme funny off topic",
            score=0, comments_count=0
        )
        self.assertGreaterEqual(pre_score_thread(terrible), 0)


# ============================================================================
# b) DEDUPLICATION
# ============================================================================

class TestDeduplication(unittest.TestCase):
    """Test the dedup logic used in scraping (seen_ids set filtering)."""

    def _dedup(self, ideas, seen_ids):
        """Simulate the dedup pattern used in the codebase."""
        return [i for i in ideas if i.get("metadata", {}).get("id") not in seen_ids]

    def test_duplicate_ids_removed(self):
        seen = {"idea-1", "idea-2"}
        ideas = [
            make_idea(title="A", source_thread_id="idea-1"),
            make_idea(title="B", source_thread_id="idea-3"),
        ]
        # Patch metadata.id to match seen
        ideas[0]["metadata"]["id"] = "idea-1"
        ideas[1]["metadata"]["id"] = "idea-3"
        result = self._dedup(ideas, seen)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["metadata"]["id"], "idea-3")

    def test_new_ids_pass_through(self):
        seen = {"old-1"}
        ideas = [make_idea(title="New")]
        ideas[0]["metadata"]["id"] = "new-1"
        result = self._dedup(ideas, seen)
        self.assertEqual(len(result), 1)

    def test_empty_seen_set(self):
        seen = set()
        ideas = [make_idea(title="A"), make_idea(title="B")]
        result = self._dedup(ideas, seen)
        self.assertEqual(len(result), 2)

    def test_empty_ideas_list(self):
        seen = {"x", "y"}
        result = self._dedup([], seen)
        self.assertEqual(result, [])

    def test_all_duplicates(self):
        ideas = [make_idea(title="X")]
        ideas[0]["metadata"]["id"] = "dup"
        result = self._dedup(ideas, {"dup"})
        self.assertEqual(len(result), 0)


# ============================================================================
# c) IDEA VALIDATION
# ============================================================================

class TestValidateIdea(unittest.TestCase):

    def test_valid_idea_passes(self):
        idea = make_idea(tier=1, composite=8.0)
        self.assertTrue(validate_idea(idea))

    def test_valid_tier2_passes(self):
        idea = make_idea(tier=2, composite=6.5)
        self.assertTrue(validate_idea(idea))

    def test_string_tier_passes(self):
        """Tier as string "1" or "2" should be accepted."""
        idea = make_idea(tier="1", composite=8.0)
        self.assertTrue(validate_idea(idea))

    def test_missing_scoring_fails(self):
        idea = make_idea()
        del idea["scoring"]
        self.assertFalse(validate_idea(idea))

    def test_scoring_not_dict_fails(self):
        idea = make_idea()
        idea["scoring"] = "high"
        self.assertFalse(validate_idea(idea))

    def test_invalid_tier_fails(self):
        idea = make_idea(tier=3)
        self.assertFalse(validate_idea(idea))

    def test_tier_zero_fails(self):
        idea = make_idea(tier=0)
        self.assertFalse(validate_idea(idea))

    def test_tier_none_fails(self):
        idea = make_idea()
        idea["scoring"]["tier"] = None
        self.assertFalse(validate_idea(idea))

    def test_composite_negative_fails(self):
        idea = make_idea(composite=-1)
        self.assertFalse(validate_idea(idea))

    def test_composite_over_10_fails(self):
        idea = make_idea(composite=11)
        self.assertFalse(validate_idea(idea))

    def test_composite_zero_passes(self):
        idea = make_idea(composite=0)
        self.assertTrue(validate_idea(idea))

    def test_composite_10_passes(self):
        idea = make_idea(composite=10.0)
        self.assertTrue(validate_idea(idea))

    def test_composite_string_fails(self):
        idea = make_idea()
        idea["scoring"]["composite"] = "8.5"
        self.assertFalse(validate_idea(idea))

    def test_missing_problem_title_fails(self):
        idea = make_idea()
        idea["problem"]["title"] = ""
        self.assertFalse(validate_idea(idea))

    def test_missing_problem_dict_fails(self):
        idea = make_idea()
        del idea["problem"]
        self.assertFalse(validate_idea(idea))

    def test_problem_not_dict_fails(self):
        idea = make_idea()
        idea["problem"] = "just a string"
        self.assertFalse(validate_idea(idea))

    def test_not_a_dict_fails(self):
        self.assertFalse(validate_idea("not a dict"))
        self.assertFalse(validate_idea(42))
        self.assertFalse(validate_idea(None))
        self.assertFalse(validate_idea([]))


# ============================================================================
# d) JSON PARSING FROM CLI OUTPUT
# ============================================================================

def parse_cli_json(text: str) -> list:
    """Replicate the JSON parsing logic from analyze_local_batch / analyze_batch."""
    text = text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)

    if text.startswith("["):
        return json.loads(text)

    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        return json.loads(match.group())

    return []


class TestJsonParsing(unittest.TestCase):

    def test_clean_json_array(self):
        raw = '[{"id": 1}, {"id": 2}]'
        result = parse_cli_json(raw)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], 1)

    def test_json_in_markdown_code_block(self):
        raw = '```json\n[{"id": 1}]\n```'
        result = parse_cli_json(raw)
        self.assertEqual(len(result), 1)

    def test_json_in_plain_code_block(self):
        raw = '```\n[{"id": 1}]\n```'
        result = parse_cli_json(raw)
        self.assertEqual(len(result), 1)

    def test_json_embedded_in_text(self):
        raw = 'Here are the results:\n[{"id": 1}]\nEnd of analysis.'
        result = parse_cli_json(raw)
        self.assertEqual(len(result), 1)

    def test_empty_array(self):
        result = parse_cli_json("[]")
        self.assertEqual(result, [])

    def test_empty_string(self):
        result = parse_cli_json("")
        self.assertEqual(result, [])

    def test_invalid_json(self):
        result = parse_cli_json("this is not json at all")
        self.assertEqual(result, [])

    def test_whitespace_around_json(self):
        raw = '   \n  [{"id": 1}]  \n  '
        result = parse_cli_json(raw)
        self.assertEqual(len(result), 1)

    def test_nested_objects(self):
        raw = '[{"scoring": {"tier": 1, "composite": 8.5}}]'
        result = parse_cli_json(raw)
        self.assertEqual(result[0]["scoring"]["tier"], 1)

    def test_multiline_json(self):
        raw = '[\n  {\n    "id": 1\n  },\n  {\n    "id": 2\n  }\n]'
        result = parse_cli_json(raw)
        self.assertEqual(len(result), 2)


# ============================================================================
# e) CROSS-SIGNAL DETECTION
# ============================================================================

class TestCrossSignal(unittest.TestCase):

    def test_overlap_detected(self):
        """Threads with 5+ common meaningful words should get cross-signal."""
        t1 = make_thread(
            title="invoice automation billing platform freelance scheduling payment tracking",
            subreddit="smallbusiness", thread_id="t1"
        )
        t2 = make_thread(
            title="invoice automation billing platform freelance scheduling needed",
            subreddit="Entrepreneur", thread_id="t2"
        )
        result = detect_cross_signals([t1, t2])
        self.assertIn("Entrepreneur", result[0]["cross_signal"]["related_subs"])
        self.assertIn("smallbusiness", result[1]["cross_signal"]["related_subs"])

    def test_stop_words_dont_trigger(self):
        """Common stop words should not cause false positive cross-signals."""
        t1 = make_thread(
            title="How is the weather today for you and me",
            subreddit="sub1", thread_id="t1"
        )
        t2 = make_thread(
            title="What is this about for all of you",
            subreddit="sub2", thread_id="t2"
        )
        result = detect_cross_signals([t1, t2])
        self.assertEqual(result[0]["cross_signal"]["related_subs"], [])

    def test_no_overlap(self):
        """Completely different threads should not be linked."""
        t1 = make_thread(title="Python machine learning framework", subreddit="s1", thread_id="t1")
        t2 = make_thread(title="Restaurant inventory management", subreddit="s2", thread_id="t2")
        result = detect_cross_signals([t1, t2])
        self.assertEqual(result[0]["cross_signal"]["related_subs"], [])
        self.assertEqual(result[1]["cross_signal"]["related_subs"], [])

    def test_same_subreddit_not_linked(self):
        """Threads from same subreddit should not cross-signal each other."""
        t1 = make_thread(
            title="invoice automation billing platform freelance scheduling payment",
            subreddit="sameSub", thread_id="t1"
        )
        t2 = make_thread(
            title="invoice automation billing platform freelance scheduling needed",
            subreddit="sameSub", thread_id="t2"
        )
        result = detect_cross_signals([t1, t2])
        self.assertEqual(result[0]["cross_signal"]["related_subs"], [])

    def test_signal_strength_single_related(self):
        """1-2 related subs should give signal_strength 1.5."""
        t1 = make_thread(title="invoice automation billing platform freelance scheduling payment", subreddit="s1", thread_id="t1")
        t2 = make_thread(title="invoice automation billing platform freelance scheduling needed", subreddit="s2", thread_id="t2")
        result = detect_cross_signals([t1, t2])
        self.assertEqual(result[0]["cross_signal"]["signal_strength"], 1.5)

    def test_signal_strength_multiple_related(self):
        """3+ related subs should give signal_strength 2.0."""
        threads = [
            make_thread(title="invoice automation billing platform freelance scheduling payment tracking", subreddit=f"s{i}", thread_id=f"t{i}")
            for i in range(4)
        ]
        result = detect_cross_signals(threads)
        # Each thread should have 3 related subs (the other 3)
        has_strong = any(t["cross_signal"]["signal_strength"] == 2.0 for t in result)
        self.assertTrue(has_strong)

    def test_short_words_filtered(self):
        """Words <= 3 chars should be ignored."""
        t1 = make_thread(title="the cat sat mat", subreddit="s1", thread_id="t1")
        t2 = make_thread(title="the cat sat mat", subreddit="s2", thread_id="t2")
        result = detect_cross_signals([t1, t2])
        # "the" is stop word, "cat"/"sat"/"mat" are 3 chars (filtered by len > 3)
        self.assertEqual(result[0]["cross_signal"]["related_subs"], [])

    def test_cleanup_removes_terms(self):
        """_terms key should be removed after processing."""
        t1 = make_thread(title="some title", subreddit="s1", thread_id="t1")
        result = detect_cross_signals([t1])
        self.assertNotIn("_terms", result[0])


# ============================================================================
# f) TIER CLASSIFICATION
# ============================================================================

class TestTierClassification(unittest.TestCase):

    def test_tier1_ideas_classified(self):
        ideas = [make_idea(tier=1, composite=8.5)]
        t1, t2 = classify_tiers(ideas)
        self.assertEqual(len(t1), 1)
        self.assertEqual(len(t2), 0)

    def test_tier2_ideas_classified(self):
        ideas = [make_idea(tier=2, composite=6.5)]
        t1, t2 = classify_tiers(ideas)
        self.assertEqual(len(t1), 0)
        self.assertEqual(len(t2), 1)

    def test_mixed_tiers(self):
        ideas = [
            make_idea(tier=1, composite=9.0, title="Best"),
            make_idea(tier=2, composite=7.0, title="Good"),
            make_idea(tier=1, composite=8.0, title="Great"),
            make_idea(tier=2, composite=6.0, title="OK"),
        ]
        t1, t2 = classify_tiers(ideas)
        self.assertEqual(len(t1), 2)
        self.assertEqual(len(t2), 2)

    def test_tier1_sorted_by_composite_desc(self):
        ideas = [
            make_idea(tier=1, composite=7.0, title="Low"),
            make_idea(tier=1, composite=9.5, title="High"),
            make_idea(tier=1, composite=8.0, title="Mid"),
        ]
        t1, _ = classify_tiers(ideas)
        composites = [i["scoring"]["composite"] for i in t1]
        self.assertEqual(composites, [9.5, 8.0, 7.0])

    def test_tier2_sorted_by_composite_desc(self):
        ideas = [
            make_idea(tier=2, composite=6.0),
            make_idea(tier=2, composite=7.5),
        ]
        _, t2 = classify_tiers(ideas)
        self.assertGreater(t2[0]["scoring"]["composite"], t2[1]["scoring"]["composite"])

    def test_string_tier_handled(self):
        """Tier as string should still classify correctly."""
        ideas = [make_idea(tier="1", composite=8.0)]
        t1, t2 = classify_tiers(ideas)
        self.assertEqual(len(t1), 1)

    def test_invalid_tier_ignored(self):
        """Tier 3, 0, or None should not appear in either list."""
        ideas = [
            make_idea(tier=3, composite=5.0),
            make_idea(tier=0, composite=5.0),
        ]
        t1, t2 = classify_tiers(ideas)
        self.assertEqual(len(t1), 0)
        self.assertEqual(len(t2), 0)

    def test_empty_ideas(self):
        t1, t2 = classify_tiers([])
        self.assertEqual(t1, [])
        self.assertEqual(t2, [])

    def test_missing_scoring_skipped(self):
        ideas = [{"problem": {"title": "No scoring"}}]
        t1, t2 = classify_tiers(ideas)
        self.assertEqual(len(t1), 0)
        self.assertEqual(len(t2), 0)


if __name__ == "__main__":
    unittest.main()
