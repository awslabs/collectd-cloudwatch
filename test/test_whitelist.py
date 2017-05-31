import os
import unittest
from tempfile import gettempdir

from mock import mock_open, patch, Mock, call

from cloudwatch.modules.configuration.confighelper import ConfigHelper
from cloudwatch.modules.configuration.whitelist import Whitelist, WhitelistConfigReader, BlockedMetricLogger


class WhitelistTest(unittest.TestCase):
    CONFIG_DIR = "./test/config_files/"
    BLOCKED_METRIC_PATH = gettempdir() + "/blocked_metrics"
    EMPTY_WHITELIST_FILE = CONFIG_DIR + "empty_whitelist.conf"
    TEST_LITERAL_WHITELIST_FILE = CONFIG_DIR + "literal_whitelist.conf"
    TEST_REGEX_WHITELIST_FILE = CONFIG_DIR + "regex_whitelist.conf"
    INVALID_REGEX_WHITELIST_FILE = CONFIG_DIR + "invalid_regex_whitelist.conf"
    PASS_THROUGH_WHITELIST_FILE = CONFIG_DIR + "pass_through_whitelist.conf"
    WHITELISTED_METRICS_IN_LITERAL_WHITELIST_FILE = ["df-root-percent_bytes-free", "df-root-percent_bytes-used",
                                                     "memory--memory-used", "memory--memory-free", "swap--swap-used",
                                                     "swap--swap-free"]
    WHITELISTED_SAMPLE_METRICS_IN_REGEX_WHITELIST_FILE = ["df-root-percent_bytes-used", "df-test-percent_bytes-used",
                                                          "memory--memory-used", "memory--memory-slab",
                                                          "swap-whitelisted", "swap--swap-free"]
    UNSAFE_REGEXES = ["^.*$", "^.+$", "^invalid- .*$", "^.* -invalid$", "^invalid- .* -invalid$", "^invalid- .+$",
                      "^.+ -invalid$", "^invalid- .+ -invalid$"]
    SAFE_REGEXES = ["^.*-valid$", "^valid-.*-valid$", "^valid-.*$","^.+-valid$", "^valid-.+-valid$", "^valid-.+$"]

    def setUp(self):
        ConfigHelper.BLOCKED_METRIC_PATH = self.BLOCKED_METRIC_PATH

    def test_blocked_file_is_created(self):
        BlockedMetricLogger(self.BLOCKED_METRIC_PATH)
        self.assertTrue(os.path.exists(self.BLOCKED_METRIC_PATH))

    def test_whitelist_file_is_created(self):
        temp_whitelist_file = gettempdir() + "/whitelist.conf"
        logger_mock = Mock()
        WhitelistConfigReader._LOGGER = logger_mock
        if os.path.exists(temp_whitelist_file):
            os.remove(temp_whitelist_file)
        whitelist = Whitelist(WhitelistConfigReader(temp_whitelist_file, pass_through_allowed=True).get_regex_list(), self.BLOCKED_METRIC_PATH)
        logger_mock.warning.assert_called_with("The whitelist configuration file was not detected at " +
                                               temp_whitelist_file + ". Creating new file.")
        self.assertTrue(os.path.exists(temp_whitelist_file))
        self.assertFalse(whitelist.is_whitelisted("memory--memory.free"))
        os.remove(temp_whitelist_file)

    def test_blocked_metric_logger_logs_issues_with_opening_file(self):
        mopen = mock_open()
        mopen.side_effect = IOError(13, "Permission denied")
        logger_mock = Mock()
        BlockedMetricLogger._LOGGER = logger_mock
        expected_logger_calls = [call("Could not create list of blocked metrics '" + self.BLOCKED_METRIC_PATH + "'. Reason: [Errno 13] Permission denied"),
                                 call("Could not update list of blocked metrics '" + self.BLOCKED_METRIC_PATH +
                                 "' with metric: 'test-metric'. Reason: [Errno 13] Permission denied")]
        with patch("cloudwatch.modules.configuration.whitelist.open", mopen, create=True):
            whitelist = Whitelist(WhitelistConfigReader(self.EMPTY_WHITELIST_FILE, pass_through_allowed=True).get_regex_list(), self.BLOCKED_METRIC_PATH)
            self.assertFalse(whitelist.is_whitelisted("test-metric"))
        logger_mock.warning.assert_has_calls(expected_logger_calls)

    def test_whitelist_config_reader_logs_issues_with_opening_files(self):
        mopen = mock_open()
        mopen.side_effect = IOError(13, "Permission denied")
        logger_mock = Mock()
        WhitelistConfigReader._LOGGER = logger_mock
        expected_logger_calls = [call("Could not open whitelist file '" + self.EMPTY_WHITELIST_FILE + "'. Reason: [Errno 13] Permission denied")]
        with patch("cloudwatch.modules.configuration.whitelist.open", mopen, create=True):
            Whitelist(WhitelistConfigReader(self.EMPTY_WHITELIST_FILE, pass_through_allowed=True).get_regex_list(), self.BLOCKED_METRIC_PATH)
            logger_mock.warning.assert_has_calls(expected_logger_calls)

    def test_empty_whitelist_blocks_metrics(self):
        test_metric = "test-metric"
        whitelist = Whitelist(WhitelistConfigReader(self.EMPTY_WHITELIST_FILE, pass_through_allowed=True).get_regex_list(), self.BLOCKED_METRIC_PATH)
        self.assertFalse(whitelist.is_whitelisted(test_metric))
        self.assertTrue(test_metric in self._get_data_from_blocked_list())

    def test_blocked_metric_is_written_only_once(self):
        mopen = mock_open()
        with patch("cloudwatch.modules.configuration.whitelist.open", mopen, create=True):
            whitelist = Whitelist(WhitelistConfigReader(self.EMPTY_WHITELIST_FILE, pass_through_allowed=True).get_regex_list(), self.BLOCKED_METRIC_PATH)
            self.assertFalse(whitelist.is_whitelisted("test-metric"))
            self.assertFalse(whitelist.is_whitelisted("test-metric"))
        mopen.assert_called_with(self.BLOCKED_METRIC_PATH, 'a')
        handle = mopen()
        handle.write.assert_called_with("test-metric\n")

    def test_all_whitelisted_metrics_pass(self):
        whitelist = Whitelist(WhitelistConfigReader(self.TEST_LITERAL_WHITELIST_FILE, pass_through_allowed=False).get_regex_list(), self.BLOCKED_METRIC_PATH)
        for metric in self.WHITELISTED_METRICS_IN_LITERAL_WHITELIST_FILE:
            self.assertTrue(whitelist.is_whitelisted(metric))
        self.assertFalse(whitelist.is_whitelisted("test-metric"))

    def test_whitelist_regex_works(self):
        whitelist = Whitelist(WhitelistConfigReader(self.TEST_REGEX_WHITELIST_FILE, pass_through_allowed=False).get_regex_list(), self.BLOCKED_METRIC_PATH)
        for metric in self.WHITELISTED_SAMPLE_METRICS_IN_REGEX_WHITELIST_FILE:
            self.assertTrue(whitelist.is_whitelisted(metric))
        self.assertFalse(whitelist.is_whitelisted("df-root-percent_bytes-free"))

    def test_whitelist_regex_does_not_match_partial_strings(self):
        whitelist = Whitelist(WhitelistConfigReader(self.TEST_REGEX_WHITELIST_FILE, pass_through_allowed=False).get_regex_list(), self.BLOCKED_METRIC_PATH)
        whitelisted_metric = "df-test-percent_bytes-used"
        self.assertTrue(whitelist.is_whitelisted(whitelisted_metric))
        self.assertFalse(whitelist.is_whitelisted("prefix-" + whitelisted_metric))
        self.assertFalse(whitelist.is_whitelisted(whitelisted_metric + "-suffix"))

    def test_invalid_regex_line_is_handled_gracefully_and_logged(self):
        logger_mock = Mock()
        WhitelistConfigReader._LOGGER = logger_mock
        whitelist = Whitelist(WhitelistConfigReader(self.INVALID_REGEX_WHITELIST_FILE, pass_through_allowed=False).get_regex_list(), self.BLOCKED_METRIC_PATH)
        expected_logger_calls = [call("The whitelist rule: 'df-.**-percent_bytes-used' is invalid, reason: multiple repeat"),
                                 call("The whitelist rule: 'swap-*+' is invalid, reason: multiple repeat")]
        logger_mock.warning.assert_has_calls(expected_logger_calls)
        self.assertEqual(2, logger_mock.warning.call_count)
        self.assertFalse(whitelist.is_whitelisted("swap-swap-free"))
        self.assertFalse(whitelist.is_whitelisted("df-test-percent_bytes-used"))
        self.assertTrue(whitelist.is_whitelisted("memory--memory-free"))

    def test_whitelist_blocks_unsafe_regexes_with_pass_through_disabled(self):
        whitelist_regexes = WhitelistConfigReader(self.PASS_THROUGH_WHITELIST_FILE, pass_through_allowed=False).get_regex_list()
        for unsafe_regex in self.UNSAFE_REGEXES:
            self.assertFalse(unsafe_regex in whitelist_regexes)
        for safe_regex in self.SAFE_REGEXES:
            self.assertTrue(safe_regex in whitelist_regexes)

    def test_whiteslist_dont_block_unsafe_regexes_with_pass_through_enabled(self):
        whitelist_regexes = WhitelistConfigReader(self.PASS_THROUGH_WHITELIST_FILE, pass_through_allowed=True).get_regex_list()
        for unsafe_regex in self.UNSAFE_REGEXES:
            self.assertTrue(unsafe_regex in whitelist_regexes)
        for safe_regex in self.SAFE_REGEXES:
            self.assertTrue(safe_regex in whitelist_regexes)

    def test_unsafe_regexes_are_logged_with_pass_through_disabled(self):
        logger_mock = Mock()
        WhitelistConfigReader._LOGGER = logger_mock
        WhitelistConfigReader(self.PASS_THROUGH_WHITELIST_FILE, pass_through_allowed=False).get_regex_list()
        logger_mock.warning.assert_called_with("The unsafe whitelist rule: 'invalid- .+ -invalid' was disabled. Revisit the rule "
                                               "or change whitelist_pass_through option in the plugin configuration.")

    def _get_data_from_blocked_list(self):
        with open(self.BLOCKED_METRIC_PATH) as fd:
            return fd.read()

    def tearDown(self):
        try:
            os.remove(ConfigHelper.BLOCKED_METRIC_PATH)
        except OSError:
            pass  # Most likely open was patched and the blocked file doesn't exist
