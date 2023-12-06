from samm.metric import InstanceMetric, Tag

def test_metric():
	metricstr = InstanceMetric("metric1", 10, tags={"name": "test1", "instance": "test2"})
	assert str(metricstr) == "metric1{name=\"test1\",instance=\"test2\"} 10\n"

def test_metric_string():
	metricstr = InstanceMetric("metric1", "value", tags={"name": "test1", "instance": "test2"})
	assert str(metricstr) == "metric1{name=\"test1\",instance=\"test2\"} -1\n"

def test_metric_mapping():
	metricstr = InstanceMetric("metric1", "value", tags={"name": "test1", "instance": "test2"},
		value_mapping={ "value": 1, "*": 0 })
	assert str(metricstr) == "metric1{name=\"test1\",instance=\"test2\"} 1\n"
	metricstr = InstanceMetric("metric1", "value1", tags={"name": "test1", "instance": "test2"},
		value_mapping={ "value": 1, "*": 0 })
	assert str(metricstr) == "metric1{name=\"test1\",instance=\"test2\"} 0\n"

def test_tag():
	assert str(Tag("name", "test1")) == "name=\"test1\""
