"""Duplicate issue finder using TF-IDF and cosine similarity (scikit-learn).

TF-IDF turns each issue's text into a vector where rare, meaningful words weigh more than common
ones. Two issues about the same problem share those words, so their vectors point the same way, and
cosine similarity (1.0 = same direction, 0.0 = nothing in common) measures it.
"""
from dataclasses import dataclass
from itertools import combinations
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class Match:
    issue_id: int
    title: str
    score: float


def issue_text(issue: dict[str, Any]) -> str:
    return f"{issue['title']} {issue.get('description', '')}"


class DuplicateFinder:
    def __init__(self, issues: list[dict[str, Any]], threshold: float = 0.26) -> None:
        if not issues:
            raise ValueError("Need at least one issue")
        self.issues = issues
        self.threshold = threshold
        # Character n-grams (3-5 letters inside word boundaries) cope with word forms:
        # "crash"/"crashes", "sync"/"synchronization". Plain word tokens scored clearly worse (see docs).
        self.vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
        self.matrix = self.vectorizer.fit_transform([issue_text(i) for i in issues])

    def similar_to(self, text: str, top_n: int = 5) -> list[Match]:
        """Rank existing issues by similarity to a new report (title + description text)."""
        scores = cosine_similarity(self.vectorizer.transform([text]), self.matrix)[0]
        ranked = sorted(zip(self.issues, scores, strict=True), key=lambda p: -p[1])
        return [Match(i["id"], i["title"], round(float(s), 3)) for i, s in ranked[:top_n] if s >= self.threshold]

    def all_pairs(self) -> list[tuple[int, int, float]]:
        """Every pair of existing issues whose similarity reaches the threshold."""
        sims = cosine_similarity(self.matrix)
        pairs = []
        for a, b in combinations(range(len(self.issues)), 2):
            if sims[a][b] >= self.threshold:
                pairs.append((self.issues[a]["id"], self.issues[b]["id"], round(float(sims[a][b]), 3)))
        return sorted(pairs, key=lambda p: -p[2])


@dataclass
class Evaluation:
    threshold: float
    precision: float
    recall: float
    f1: float
    true_positives: int
    false_positives: int
    false_negatives: int


def evaluate(issues: list[dict[str, Any]], true_pairs: list[list[int]], threshold: float) -> Evaluation:
    """Compare predicted duplicate pairs with a human-labelled set."""
    expected = {frozenset(p) for p in true_pairs}
    predicted = {frozenset((a, b)) for a, b, _ in DuplicateFinder(issues, threshold).all_pairs()}
    tp = len(expected & predicted)
    fp = len(predicted - expected)
    fn = len(expected - predicted)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return Evaluation(threshold, round(precision, 3), round(recall, 3), round(f1, 3), tp, fp, fn)


def sweep(issues: list[dict[str, Any]], true_pairs: list[list[int]], thresholds: list[float]) -> list[Evaluation]:
    return [evaluate(issues, true_pairs, t) for t in thresholds]
