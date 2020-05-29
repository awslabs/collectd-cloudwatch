COLLECTD_COMPILE_PATH = "/opt/collectd/sbin/collectd"
COLLECTD_PATH_KEY = "collectd_path"
VERSION_KEY = "version"
CONFIG_PATH_KEY = "config_path"
SUPPORTED = "version_supported"
RECOMMENDED = "version_recommended"
OUTPUT_KEY = "output"


SAMPLE1 = {
    COLLECTD_PATH_KEY: "/bin/collectd",
    VERSION_KEY: "4.4.1",
    SUPPORTED: False,
    RECOMMENDED: False,
    CONFIG_PATH_KEY: "/etc/collectd.conf",
    OUTPUT_KEY: """Usage: collectd [OPTIONS]

Available options:
  General:
    -C <file>       Configuration file.
                    Default: /etc/collectd.conf
    -t              Test config and exit.
    -T              Test plugin read and exit.
    -P <file>       PID-file.
                    Default: /var/run/collectd.pid
    -f              Don't fork to the background.
    -h              Display help (this message)

Builtin defaults:
  Config file       /etc/collectd.conf
  PID file          /var/run/collectd.pid
  Plugin directory  /usr/lib64/collectd
  Data directory    /var/lib/collectd

collectd 4.4.1, http://collectd.org/
by Florian octo Forster <octo@verplant.org>
for contributions see `AUTHORS'"""
}
SAMPLE2 = {
    COLLECTD_PATH_KEY: "/usr/sbin/collectd",
    VERSION_KEY: "5.4.0",
    SUPPORTED: True,
    RECOMMENDED: False,
    CONFIG_PATH_KEY: "/etc/collectd/collectd.conf",
    OUTPUT_KEY: """Usage: collectd [OPTIONS]

Available options:
  General:
    -C <file>       Configuration file.
                    Default: /etc/collectd/collectd.conf
    -t              Test config and exit.
    -T              Test plugin read and exit.
    -P <file>       PID-file.
                    Default: /var/run/collectd.pid
    -f              Don't fork to the background.
    -h              Display help (this message)

Builtin defaults:
  Config file       /etc/collectd/collectd.conf
  PID file          /var/run/collectd.pid
  Plugin directory  /usr/lib/collectd
  Data directory    /var/lib/collectd

collectd 5.4.0.git, http://collectd.org/
by Florian octo Forster <octo@verplant.org>
for contributions see `AUTHORS'"""
}
SAMPLE3 = {
    COLLECTD_PATH_KEY: COLLECTD_COMPILE_PATH,
    VERSION_KEY: "5.5.3",
    SUPPORTED: True,
    RECOMMENDED: True,
    CONFIG_PATH_KEY: "/opt/collectd/etc/collectd.conf",
    OUTPUT_KEY:  """Usage: collectd [OPTIONS]

Available options:
  General:
    -C <file>       Configuration file.
                    Default: /opt/collectd/etc/collectd.conf
    -t              Test config and exit.
    -T              Test plugin read and exit.
    -P <file>       PID-file.
                    Default: /opt/collectd/var/run/collectd.pid
    -f              Don't fork to the background.
    -h              Display help (this message)

Builtin defaults:
  Config file       /opt/collectd/etc/collectd.conf
  PID file          /opt/collectd/var/run/collectd.pid
  Plugin directory  /opt/collectd/lib/collectd
  Data directory    /opt/collectd/var/lib/collectd

collectd 5.5.3.git, http://collectd.org/
by Florian octo Forster <octo@collectd.org>
for contributions see `AUTHORS'"""
}
SAMPLE4 = {
    COLLECTD_PATH_KEY: COLLECTD_COMPILE_PATH,
    VERSION_KEY: "6.215a.12.beta.321",
    SUPPORTED: True,
    RECOMMENDED: True,
    CONFIG_PATH_KEY: "/opt/collectd/etc/collectd.conf",
    OUTPUT_KEY:  """Usage: collectd [OPTIONS]

Available options:
  General:
    -C <file>       Configuration file.
                    Default: /opt/collectd/etc/collectd.conf
    -t              Test config and exit.
    -T              Test plugin read and exit.
    -P <file>       PID-file.
                    Default: /opt/collectd/var/run/collectd.pid
    -f              Don't fork to the background.
    -h              Display help (this message)

Builtin defaults:
  Config file       /opt/collectd/etc/collectd.conf
  PID file          /opt/collectd/var/run/collectd.pid
  Plugin directory  /opt/collectd/lib/collectd
  Data directory    /opt/collectd/var/lib/collectd

collectd 6.215a.12.beta.321.git, http://collectd.org/
by Florian octo Forster <octo@collectd.org>
for contributions see `AUTHORS'"""
}
