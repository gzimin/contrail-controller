import os
import sys

from haproxy_stats import HaproxyStats
from vrouter.loadbalancer.ttypes import \
    UveLoadbalancerTrace, UveLoadbalancer, UveLoadbalancerStats

LB_BASE_DIR = '/var/lib/contrail/loadbalancer/'

class LoadbalancerStats(object):
    def __init__(self):
       self.driver = HaproxyStats()
       if not self.driver.lbaas_dir:
           self.driver.lbaas_dir = LB_BASE_DIR
       try:
           self.old_pool_uuids = os.listdir(self.driver.lbaas_dir)
       except OSError:
           self.old_pool_uuids = []

    def _uve_get_stats(self, stats):
        obj_stats = UveLoadbalancerStats()
        obj_stats.obj_name = stats['name']
        obj_stats.uuid = stats['name']
        obj_stats.status = stats['status']
        obj_stats.vrouter = stats['vrouter']

        for attr in dir(obj_stats):
            if attr in stats and stats[attr].isdigit():
                setattr(obj_stats, attr, int(stats[attr]))

        return [obj_stats]

    def _uve_get_member_stats(self, stats):
        member_stats = []
        for stat in stats:
            obj_stats = UveLoadbalancerStats()
            obj_stats.obj_name = stat['name']
            obj_stats.uuid = stat['name']
            obj_stats.status = stat['status']
            obj_stats.vrouter = stat['vrouter']
            for attr in dir(obj_stats):
                if attr in stat and stat[attr].isdigit():
                    setattr(obj_stats, attr, int(stat[attr]))
            member_stats.append(obj_stats)
        return member_stats

    def _send_loadbalancer_uve(self):
        try:
            pool_uuids = os.listdir(self.driver.lbaas_dir)
        except OSError:
            return

        # delete stale uves
        for pool_uuid in self.old_pool_uuids:
            if pool_uuid not in pool_uuids:
                uve_lb = UveLoadbalancer(name=pool_uuid, deleted=True)
                uve_lb.virtual_ip_stats = {}
                uve_lb.pool_stats = {}
                uve_lb.member_stats = []
                uve_trace = UveLoadbalancerTrace(data=uve_lb)
                uve_trace.send()
        self.old_pool_uuids = pool_uuids

        # send stats
        for pool_uuid in pool_uuids:
            stats = self.driver.get_stats(pool_uuid)
            if not len(stats) or not 'vip' in stats:
                uve_lb = UveLoadbalancer(name=pool_uuid, deleted=True)
                uve_lb.virtual_ip_stats = {}
                uve_lb.pool_stats = {}
                uve_lb.member_stats = []
                uve_trace = UveLoadbalancerTrace(data=uve_lb)
                uve_trace.send()
                continue

            uve_lb = UveLoadbalancer()
            uve_lb.name = pool_uuid
            uve_lb.pool_stats = {}
            uve_lb.member_stats = []
            uve_lb.virtual_ip_stats = self._uve_get_stats(stats['vip'])
            if 'pool' in stats:
                uve_lb.pool_stats = self._uve_get_stats(stats['pool'])
            if 'members' in stats:
                uve_lb.member_stats = self._uve_get_member_stats(stats['members'])
            uve_trace = UveLoadbalancerTrace(data=uve_lb)
            uve_trace.send()

    def send_loadbalancer_stats(self):
        try:
            self._send_loadbalancer_uve()
        except Exception as e:
            sys.stderr.write('LB stats failure ' + str(e) + '\n')
