"""Tests for quality classifiers (slop_detector, content_classifier)."""
import pytest
from quality.slop_detector import is_likely_ai_slop
from quality.content_classifier import is_marketing_or_news


TECHNICAL_TEXT = """
Kubernetes pod scheduling involves multiple steps. The kube-scheduler evaluates
node affinity rules, taints and tolerations, and resource requests/limits. When
a pod is created, the scheduler filters nodes based on predicates like
PodFitsResources and PodFitsHostPorts. Then it scores remaining nodes using
priority functions such as LeastRequestedPriority and BalancedResourceAllocation.
The node with the highest score is selected for pod placement.

Here's an example of a Kubernetes deployment configuration:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.14.2
        ports:
        - containerPort: 80
```

The deployment controller ensures the desired number of pods are running.
If a node fails, pods are rescheduled to healthy nodes automatically.
This is achieved through the control plane components: kube-apiserver,
kube-controller-manager, kube-scheduler, and etcd for cluster state storage.
"""


SLOPPY_TEXT = """
In today's rapidly evolving digital landscape, it is more important than ever
to leverage cutting-edge solutions that empower your team to achieve their
goals. Our revolutionary platform provides a comprehensive suite of tools
designed to supercharge your workflow and unlock your true potential.

We believe that by harnessing the power of innovation, we can transform the
way you do business. Our state-of-the-art technology enables seamless
integration with your existing infrastructure, providing a holistic approach
to digital transformation. It is crucial to understand that in this fast-paced
world, staying ahead of the curve is not just an option, but a necessity.

That's why we're excited to announce this game-changing solution that will
revolutionize the industry. Join thousands of satisfied customers who have
already experienced the transformative power of our platform. The future is
here, and it's time to embrace it. Don't get left behind in this era of
unprecedented technological advancement. Contact us today to learn more
about how we can help your business thrive in the digital age.
"""

SHORT_TEXT = "Hello world. This is a short text."


class TestSlopDetector:
    def test_technical_text_scores_low(self):
        score, reason = is_likely_ai_slop(TECHNICAL_TEXT)
        assert score < 0.5, f"Expected low slop score, got {score}: {reason}"

    def test_sloppy_text_scores_high(self):
        score, reason = is_likely_ai_slop(SLOPPY_TEXT)
        assert score > 0.5, f"Expected high slop score, got {score}: {reason}"

    def test_short_text_scores_low(self):
        score, reason = is_likely_ai_slop(SHORT_TEXT)
        assert score < 0.5, f"Expected low score for short text, got {score}: {reason}"
        assert "only" in reason.lower() or "words" in reason.lower()

    def test_returns_tuple(self):
        result = is_likely_ai_slop(TECHNICAL_TEXT)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], float)
        assert isinstance(result[1], str)

    def test_score_between_zero_and_one(self):
        for text in [TECHNICAL_TEXT, SLOPPY_TEXT, SHORT_TEXT]:
            score, _ = is_likely_ai_slop(text)
            assert 0.0 <= score <= 1.0, f"Score {score} out of range for: {text[:30]}"


class TestMarketingClassifier:
    def test_technical_not_marketing(self):
        score, reason = is_marketing_or_news("Kubernetes Deployment Guide", TECHNICAL_TEXT)
        assert score < 0.6, f"Expected low marketing score, got {score}: {reason}"

    def test_marketing_text_scores_higher(self):
        score, reason = is_marketing_or_news("Revolutionary AI Platform Changes Everything", SLOPPY_TEXT)
        assert score > 0.5

    def test_returns_tuple(self):
        result = is_marketing_or_news("Test Title", TECHNICAL_TEXT)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], float)
        assert isinstance(result[1], str)
