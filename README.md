# Kafka disk usage metrics for Collectd

A [CollectD](http://collectd.org) plugin to collect kafka disk usage metrics. Uses CollectD's [Python plugin](http://collectd.org/documentation/manpages/collectd-python.5.shtml).

####Configuration parameters
- **`LogDirs`**: Kafka log dirs, as defined in server.properties. Comma-separated list. (REQUIRED: no default).
- **`Verbose`**: if `true`, print verbose logging (`false`).
