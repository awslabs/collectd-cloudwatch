# CloudWatch collectd plugin

The [CloudWatch](http://aws.amazon.com/cloudwatch/) collectd plugin is a publishing extension for [collectd](https://collectd.org/), an open source statistic gathering daemon. With our extension all configured collectd metrics are automatically published to CloudWatch. This plugin allows monitoring of servers and applications within and outside of EC2 instances.
The plugin offers additional functionality for EC2 customers such as automatic discovery of Instance ID and AWS region.

## Attention: collectd python plugin is required for some collectd distribution.
*  For example: for redhat distribution, run "yum install -y collectd-python".

## Installation
 * Download [installation script](https://github.com/awslabs/collectd-cloudwatch/blob/master/src/setup.py), place it on the instance and execute it:
```
chmod u+x setup.py
sudo ./setup.py
```

 * Follow on screen instructions

## Configuration

### Plugin specific configuration
The default location of the configuration file used by collectd-cloudwatch plugin is: `/opt/collectd-plugins/cloudwatch/config/plugin.conf`.  The parameters in this file are optional when plugin is executed on EC2 instance. This file allows modification of the following parameters:
 * __credentials_path__ - Used to point to AWS account configuration file
 * __arn_role__ - Used when you want to explicitly assume a role using AWS STS (Security Token Service).
 * __region__ - Manual override for [region](http://docs.aws.amazon.com/general/latest/gr/rande.html#cw_region)  used to publish metrics
 * __host__ - Manual override for EC2 Instance ID and Host information propagated by collectd
 * __proxy_server_name__ - Manual override for proxy server name, used by plugin to connect aws cloudwatch at *.amazonaws.com.
 * __proxy_server_port__ - Manual override for proxy server port, used by plugin to connect aws cloudwatch at *.amazonaws.com.
 * __enable_high_resolution_metrics__ - The storage resolution is for high resolution support
 * __flush_interval_in_seconds__ - The flush_interval_in_seconds is used for flush interval, it means how long plugin should flush the metrics to Cloudwatch
 * __whitelist_pass_through__ - Used to enable potentially unsafe regular expressions. By default regex such as a line containing `.*` or `.+` only is automatically disabled in the whitelist configuration.
  Setting this value to True may result in a large number of metrics being published. Before changing this parameter, read [pricing information](https://aws.amazon.com/cloudwatch/pricing/) to understand how to estimate your bill.
 * __push_asg__ - Used to include the Auto-Scaling Group as a dimension for all metrics (see `Adding additional dimensions to metrics` below for details)
 * __push_constant__ - Used to include a Fixed dimension (see `constant_dimension_value` below) on all metrics. Useful for collating all metrics of a certain type (see `Adding additional dimensions to metrics` below for details)
 * __constant_dimension_value__ - Used to specify the value for the Fixed dimension (see `Adding additional dimensions to metrics` below for details)
 * __debug__ - Provides verbose logging of metrics emitted to CloudWatch

#### Example configuration file
```
credentials_path = "/home/user/.aws/credentials"
arn_role = "arn:aws:test:eu-west-1:1234567890:role/to_assume"
region = "us-west-1"
host = "Server1"
proxy_server_name = "http://myproxyserver.com"
proxy_server_port = "8080"
whitelist_pass_through = False
push_asg = False
push_constant = True
constant_dimension_value = "ALL"
debug = False
enable_high_resolution_metrics = False
flush_interval_in_seconds = 60
```


##### Adding additional dimensions to metrics
We support adding both the ASG name to dimensions, as well as a "fixed dimension". Fixed dimensions are an additional value that will be added all metrics.

###### Example configuration file
    push_constant = True
    constant_dimension_value = "MyConstantValueHere"

The above configuraton will result in all metrics being pushed with "FixedDimension" : "MyConstantValueHere"

###### Example configuration file
    push_constant = True
    constant_dimension_value = "MyConstantValueHere"

The above configuraton will result in all metrics being pushed with "FixedDimension" : "MyConstantValueHere"

###### Example configuration file
    push_asg = False

The above configuration will push the AutoScaling Group name for metrics as well

### AWS account configuration
The account configuration is optional for EC2 instances with IAM Role attached. By default the AWS account configuration file is expected to be stored in: `/opt/collectd-plugins/cloudwatch/config/.aws/credentials`.
The following parameters can be configured in the above file:
 * __aws_access_key__ - Access Key ID for account with permissions to write to CloudWatch
 * __aws_secret_key__ - Secret Access Key for the above account

#### Example configuration file
```
aws_access_key = valid_access_key
aws_secret_key = valid_secret_key
```

### Assuming role using AWS STS(Security toke service)
By setting __arn_role__ in configuration you can explicitly assume a role. It's helpful when you want to send metrics from an account to another account.
Suppose you want send a metric from an EC2 instance in `account_A` to cloudwatch in `account_B`. Then, You should define a role in the `account_A` with
proper policies accessing cloudwatch of the `account A` and then create another role in the `account B` with a policy which grants assuming role already
defined in the `account_A`. Finally, attached the later role one to your EC2 IAM role. For more information visit [aws sts assume role](http://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html) documentation.

### Whitelist configuration
The CloudWatch collectd plugin allows users to select metrics to be published. This is done by adding metric names or regular expressions written in [python regex syntax](https://docs.python.org/2/library/re.html#regular-expression-syntax) to the whitelist config file. The default location of this configuration is: `/opt/collectd-plugins/cloudwatch/config/whitelist.conf`.

##### Warning:
1. In order to send all metrics from collectd directly to CloudWatch you can add the following rule to the whitelist.conf: `.*`
2. The metric names in CloudWatch are slightly different from the metric key used in the white list.

#### Example configuration:
```
swap--swap-free
memory--memory-.*
df-.*-percent_bytes-used
```

##### Effect:
1. Only the swap.swap.free metric will be published from all swap metrics
2. All memory metrics will be published
1. The df.percent_bytes.used metric will be published for every file system reported by df plugin


## Usage
Once the plugin is configured correctly, restart collectd to load new configuration.
```
sudo /etc/init.d/collectd restart
```

From now on your collectd metrics will be published to CloudWatch.

## Troubleshooting
Our plugin uses collectd logfile plugin. In order to enable logging in collectd, modify the collectd.conf to contain the following section:
```
LoadPlugin logfile

<Plugin logfile>
       LogLevel info
       File "/var/log/collectd.log"
       Timestamp true
       PrintSeverity false
</Plugin>
```
The collectd log can be filtered for CloudWatch plugin events using grep:
```
grep "[AmazonCloudWatchPlugin]" /var/log/collectd.log
```

## Contributing

1. Create your fork by clicking Fork button on top of the page.
2. Download your repository: `git clone https://github.com/USER/cloudwatch-collectd-plugin.git`
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'My new feature description'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request

## License
The MIT License (MIT)

Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
