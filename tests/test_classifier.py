from sms_hub.classifier import MessageClassifier


def test_classifies_critical_message():
    classifier = MessageClassifier()
    result = classifier.classify("This is an emergency, help immediately!")
    assert result["classification"] == "critical"
    assert "critical" in result["rationale"].lower()


def test_stabilizes_text_spacing():
    classifier = MessageClassifier()
    result = classifier.classify("Hello    family   ")
    assert result["stabilized_text"] == "Hello family"
    assert result["classification"] == "stable"
