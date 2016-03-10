#!/usr/bin/python
import os, re

# metric names:
disk_bytes    = 'kafka-disk-bytes'
num_logs      = 'kafka-num-logs'

class DiskMetrics(object):
  def __init__(self, collectd, logdirs=None, verbose=False):
    self.collectd = collectd
    self.logdirs = logdirs
    self.verbose = verbose

  def configure_callback(self, conf):
    """called by collectd to configure the plugin. This is called only once"""
    for node in conf.children:
      if node.key == 'LogDirs':
        self.logdirs = node.values[0].split(",")
      elif node.key == 'Verbose':
        self.verbose = bool(node.values[0])
      else:
        self.collectd.warning('kafka-disk plugin: Unknown config key: %s.' % (node.key))
    
    self.current_metrics = {
        disk_bytes  : 0,
        num_logs    : 0,
    }

  def read_callback(self):
    """read the most-recently modified GC log in logdir, then return most recent datapoints from it"""
    if self.logdirs:
      stats = {}
      for logdir in self.logdirs:
        self.add_stats(logdir, stats)

      if stats:
        self.dispatch_metrics(stats)
    else:
      self.collectd.warning('g1gc plugin: skipping because no log directory ("LogDirs") has been configured')


  def add_stats(self, log_dir, stats):
    for dirpath, dirnames, filenames in os.walk(log_dir):
      if dirpath == log_dir:
        continue
      
      partition = dirpath.replace(log_dir, "")
      topic = re.sub(r"-\d+$", "", partition)

      size = 0
      count = 0

      for f in filenames:
        if f.endswith(".log"):
          count += 1
        fp = os.path.join(dirpath, f)
        size += os.path.getsize(fp)

      if topic not in stats:
        stats[topic] = [size, count]
      else:
        stats[topic][0] += size
        stats[topic][1] += count

  def dispatch_metrics(self, topic_stats):
    for topic, stats in topic_stats.items():
      self.create_metric(disk_bytes, topic, stats[0]).dispatch()
      self.create_metric(num_logs, topic, stats[1]).dispatch()

  def create_metric(self, name, topic, value):
    self.log_verbose('Sending value gauge.%s[plugin_instance=%s]=%s' % (name, topic, value))
    return self.collectd.Values(
      plugin='kafka-disk', 
      plugin_instance=topic,
      type="gauge", 
      type_instance=name,
      values=[value])

  def log_verbose(self, msg):
    if self.verbose:
      self.collectd.info('kafka-disk plugin [verbose]: '+msg)

# The following classes are copied from collectd-mapreduce/mapreduce_utils.py
# to launch the plugin manually (./kafka_disk.py) for development
# purposes. They basically mock the calls on the "collectd" symbol
# so everything prints to stdout.
class CollectdMock(object):

  def __init__(self, plugin):
    self.value_mock = CollectdValuesMock
    self.plugin = plugin

  def info(self, msg):
    print 'INFO: %s' % (msg)

  def warning(self, msg):
    print 'WARN: %s' % (msg)

  def error(self, msg):
    print 'ERROR: %s' % (msg)
    sys.exit(1)

  def Values(self, plugin=None, plugin_instance=None, type=None, type_instance=None, values=None):
    return (self.value_mock)()

class CollectdValuesMock(object):

  def dispatch(self):
        print self

  def __str__(self):
    attrs = []
    for name in dir(self):
      if not name.startswith('_') and name is not 'dispatch':
        attrs.append("%s=%s" % (name, getattr(self, name)))
    return "<CollectdValues %s>" % (' '.join(attrs))

if __name__ == '__main__':
  from time import sleep
  collectd = CollectdMock('kafka_disk')
  dm = DiskMetrics(collectd, logdirs=['/mnt2/kafka/', '/mnt3/kafka'], verbose=True)
  dm.read_callback()
else:
  import collectd
  dm = DiskMetrics(collectd)
  collectd.register_config(dm.configure_callback)
  collectd.register_read(dm.read_callback)
