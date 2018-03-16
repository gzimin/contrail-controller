#
# Copyright (c) 2015 Juniper Networks, Inc. All rights reserved.
#

from gevent import monkey
monkey.patch_all()

from nodemgr.common.event_manager import EventManager, EventManagerTypeInfo
from nodemgr.common.cassandra_manager import CassandraManager
from pysandesh.sandesh_base import sandesh_global
from sandesh_common.vns.ttypes import Module


class DatabaseEventManager(EventManager):
    def __init__(self, config, unit_names):
        type_info = EventManagerTypeInfo(
            package_name = 'contrail-database',
            object_table = "ObjectDatabaseInfo",
            module_type = Module.DATABASE_NODE_MGR,
            supervisor_serverurl = supervisor_serverurl,
            third_party_processes =  {
                "cassandra" : "Dcassandra-pidfile=.*cassandra\.pid",
                "zookeeper" : "org.apache.zookeeper.server.quorum.QuorumPeerMain"
            },
            sandesh_packages = ['database.sandesh'])
        super(DatabaseEventManager, self).__init__(config, type_info, rule_file,
            sandesh_global, unit_names)
        self.hostip = config.hostip
        self.db_port = config.db_port
        self.minimum_diskgb = config.minimum_diskgb
        self.contrail_databases = config.contrail_databases
        # TODO: try to understand is next needed for analytics db and use it or remove
        #self.cassandra_repair_interval = config.cassandra_repair_interval
        self.cassandra_mgr = CassandraManager(
            config.cassandra_repair_logdir, 'analytics',
            config.contrail_databases, config.hostip, config.minimum_diskgb,
            config.db_port, config.db_jmx_port, self.process_info_manager)

    def get_failbits_nodespecific_desc(self, fail_status_bits):
        description = ""
        if fail_status_bits & self.FAIL_STATUS_DISK_SPACE:
            description += "Disk for analytics db is too low," + \
                " cassandra stopped."
        if fail_status_bits & self.FAIL_STATUS_SERVER_PORT:
            if description != "":
                description += " "
            description += "Cassandra state detected DOWN."
        if fail_status_bits & self.FAIL_STATUS_DISK_SPACE_NA:
            description += "Disk space for analytics db not retrievable."
        return description

    def do_periodic_events(self):
        self.cassandra_mgr.database_periodic(self)
        super(DatabaseEventManager, self).do_periodic_events()
