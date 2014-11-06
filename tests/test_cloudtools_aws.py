import unittest
import mock

from cloudtools.aws import aws_get_fresh_instances, FRESH_INSTANCE_DELAY, \
    FRESH_INSTANCE_DELAY_JACUZZI, filter_instances_launched_since, \
    reduce_by_freshness, distribute_in_region


class TestFreshInstances(unittest.TestCase):

    def test_aws_get_fresh_instances(self):
        now_ts = 10 * 1000
        with mock.patch("time.time") as m_time:
            with mock.patch("cloudtools.aws.filter_instances_launched_since") \
                    as m_fils:
                m_time.return_value = now_ts
                aws_get_fresh_instances(None, None)
                m_fils.assert_called_once_with(
                    None, now_ts - FRESH_INSTANCE_DELAY)

    def test_aws_get_fresh_jacuzzy_instances(self):
        now_ts = 10 * 1000
        with mock.patch("time.time") as m_time:
            with mock.patch("cloudtools.aws.filter_instances_launched_since") \
                    as m_fils:
                m_time.return_value = now_ts
                aws_get_fresh_instances(None, "fake_slaveset")
                m_fils.assert_called_once_with(
                    None, now_ts - FRESH_INSTANCE_DELAY_JACUZZI)

    def test_filter_instances_launched_since(self):
        # fresh
        i1 = mock.Mock()
        i1.launch_time = "2014-11-01T02:44:03.000Z"
        # launch_time converted to UNIX time
        t1 = 1414809843
        # old
        i2 = mock.Mock()
        i2.launch_time = "2013-11-01T02:44:03.000Z"
        since = t1 - FRESH_INSTANCE_DELAY + 10
        self.assertEqual(filter_instances_launched_since([i1, i2], since),
                         [i1])

    def test_reduce_by_freshness(self):
        instances = []
        # reduce by 100% of fresh (10) and 10% of old (3), 13 in total
        # add 10 fresh instances, 100% to be reduces
        for i in range(10):
            i = mock.Mock()
            i.launch_time = "2014-11-01T02:44:03.000Z"
            instances.append(i)
        # add 20 not fresh instances, 10% to be reduced
        for i in range(30):
            i = mock.Mock()
            i.launch_time = "2013-11-01T02:44:03.000Z"
            instances.append(i)
        # fresh launch_time converted to UNIX time
        t_fresh = 1414809843 - FRESH_INSTANCE_DELAY + 10
        with mock.patch("time.time") as m_time:
            m_time.return_value = t_fresh
            self.assertEqual(87, reduce_by_freshness(100, instances,
                                                     "meh_type", None))

    def test_reduce_by_freshness_jacuzzi(self):
        instances = []
        # reduce by 100% of fresh (10) and 0% of old
        for i in range(10):
            i = mock.Mock()
            i.launch_time = "2014-11-01T02:44:03.000Z"
            instances.append(i)
        for i in range(30):
            i = mock.Mock()
            i.launch_time = "2013-11-01T02:44:03.000Z"
            instances.append(i)
        # fresh launch_time converted to UNIX time
        t_fresh = 1414809843 - FRESH_INSTANCE_DELAY_JACUZZI + 10
        with mock.patch("time.time") as m_time:
            m_time.return_value = t_fresh
            self.assertEqual(90, reduce_by_freshness(
                100, instances, "meh_type", "fake_slaveset"))


class TestDistributeInRegion(unittest.TestCase):

    def test_basic(self):
        count = 50
        regions = ["a", "b", "c"]
        region_priorities = {"a": 2, "b": 3, "c": 5}
        self.assertDictEqual(
            distribute_in_region(count, regions, region_priorities),
            {"a": 10, "b": 15, "c": 25})

    def test_zero(self):
        count = 50
        regions = ["a", "b", "c"]
        region_priorities = {"a": 2, "b": 3, "c": 0}
        self.assertDictEqual(
            distribute_in_region(count, regions, region_priorities),
            {"a": 20, "b": 30, "c": 0})

    def test_total(self):
        count = 6
        regions = ["a", "b", "c"]
        region_priorities = {"a": 20, "b": 30, "c": 0}
        self.assertEqual(sum(distribute_in_region(count, regions,
                                                  region_priorities).values()),
                         count)

    def test_total_priority(self):
        count = 6
        regions = ["a", "b", "c"]
        region_priorities = {"a": 20, "b": 30, "c": 0}
        # make sure that rounding leftover is added to b (highest priority)
        self.assertDictEqual(
            distribute_in_region(count, regions, region_priorities),
            {"a": 2, "b": 4, "c": 0})

    def test_regions_not_in_region_priorities(self):
        count = 10
        regions = ["a", "b", "c"]
        region_priorities = {"a": 20, "b": 30}
        self.assertDictEqual(
            distribute_in_region(count, regions, region_priorities),
            {"a": 4, "b": 6})

    def test_intersection(self):
        count = 10
        regions = ["a", "b", "c"]
        region_priorities = {"a": 20, "d": 30}
        self.assertDictEqual(
            distribute_in_region(count, regions, region_priorities),
            {"a": 10})