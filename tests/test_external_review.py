import unittest
import tempfile
from pathlib import Path

from research.workflow.external_review import ExternalReviewClient, ExternalReviewResult
from research.workflow.priors import NegativePriors


SAMPLE_REVIEW_TEXT = """
摘要
本文研究了一个狭义且实用动机的问题：当部署缺失率可能与开发率不同时，如何在固定的线性流水线中选择表回归。

优势
实验严谨性与验证：透明、预先注册的框架，诚实报告正面、无效和负面结果。

弱点
- 核心等式已有：所用恒等式与线性预测变量的期望损失/丢弃代数是直接表亲，缺乏理论新意。
- 实证范围窄：仅在四个小型UCI数据集上测试，仅通过简单线性回归，维度较小。
- 池外更强的模型主导：非线性模型（如GBDT）主导所有候选，在弱池中挑选收益微弱。

作者提问
- 你的推导和选择规则能否扩展到各特征的异构缺失率p_j？
- 为什么把所有候选人的训练缺失率定在0.1？

总体评估
预计得分：
4.4/10
（已校准至ICLR等级）
这是一篇谨慎、诚实且执行良好的应用论文，重新利用已知的预期损失代数...
"""


class TestExternalReview(unittest.TestCase):

    def test_parse_review_markdown(self):
        res = ExternalReviewClient.parse_review_markdown(SAMPLE_REVIEW_TEXT, token="test_token_123", venue="ICLR")
        self.assertEqual(res.score, 4.4)
        self.assertEqual(res.venue, "ICLR")
        self.assertGreaterEqual(len(res.weaknesses), 2)
        self.assertTrue(any("核心等式" in w for w in res.weaknesses))
        self.assertGreaterEqual(len(res.questions), 1)

    def test_sync_to_negative_priors_on_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            priors_path = Path(d) / "priors.json"
            priors = NegativePriors(priors_path)
            res = ExternalReviewClient.parse_review_markdown(SAMPLE_REVIEW_TEXT, token="tok", venue="ICLR")

            prior = ExternalReviewClient.sync_to_priors(res, priors, "Mask-Integrated Linear Selection")
            self.assertIsNotNone(prior)
            self.assertIn("4.4", prior.rejection_source)
            self.assertIn("核心等式", prior.failure_mode)

            # Saved file reflects new prior
            reloaded = NegativePriors(priors_path)
            self.assertTrue(any("mask_integrated" in p.id for p in reloaded.priors))

    def test_high_score_does_not_create_negative_prior(self):
        high_review = ExternalReviewResult(
            token="high_tok",
            venue="ICLR",
            score=8.5,
            summary="Great work",
            strengths=["Novel"],
            weaknesses=[],
            questions=[],
            raw_markdown="Score: 8.5/10"
        )
        priors = NegativePriors()
        initial_len = len(priors.priors)
        res = ExternalReviewClient.sync_to_priors(high_review, priors, "Strong Novel Paper")
        self.assertIsNone(res)
        self.assertEqual(len(priors.priors), initial_len)


if __name__ == '__main__':
    unittest.main()
