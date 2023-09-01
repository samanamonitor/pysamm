from samm.metric import InstanceMetric, Tag

def test_metric():
	metricstr = InstanceMetric("metric1", 10, tags={"name": "test1", "instance": "test2"})
	assert str(metricstr) == "metric1{name=\"test1\",instance=\"test2\"} 10\n"

def test_tag():
	assert str(Tag("name", "test1")) == "name=\"test1\""
