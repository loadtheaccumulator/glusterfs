#!/usr/bin/env python
#  This file is part of DiSTAF
#  Copyright (C) 2015-2016  Red Hat, Inc. <http://www.redhat.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with this program; if not, write to the Free Software Foundation, Inc.,
#  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""
    Description: Library for gluster NFS-Ganesha operations.
"""

import re
import os
import time
import socket
from collections import OrderedDict
from glusto.core import Glusto as g
from glustolibs.gluster.volume_ops import get_volume_info
from glustolibs.gluster.peer_ops import (peer_probe_servers,
                                         nodes_from_pool_list)


def vol_set_nfs_disable(volname, option=True, mnode=None):
    '''Enables/Disables nfs for the volume.
    Args:
        volname (str): Volume name.
    Kwargs:
        option (Optional[bool]): If True it disables nfs for
            that volume else enables nfs for that volume.
            Default value is True.
        mnode (Optional[str]): Node on which the command has
            to be executed. Default value is g.config['servers'][0]['host'].
    Returns:
        bool: True if successful, False otherwise.
    '''
    if mnode is None:
        mnode = g.config['servers'][0]['host']
    if option:
        volinfo = get_volume_info(volname, mnode)
        nfs_disable = volinfo[volname]['options'].get('nfs.disable')
        if nfs_disable == "on":
            g.log.info(" nfs is already disabled for the volume %s"
                           % volname)
            return True
        ret, _, _ = g.run(mnode, "gluster volume set %s nfs.disable on "
                           "--mode=script" % volname)
        if ret != 0:
            g.log.error("failed to set nfs.disable on %s" % volname)
            return False
    else:
        ret, _, _ = g.run(mnode, "gluster volume set %s nfs.disable off "
                           "--mode=script" % volname)
        if ret != 0:
            return False

    return True


def vol_set_ganesha(volname, option=True, mnode=None):
    '''Enables/Disables ganesha for the volume.
    Args:
        volname (str): Volume name.
    Kwargs:
        option (Optional[bool]): If True it enables ganesha for
            that volume else disables ganesha for that volume.
            Default value is True.
        mnode (Optional[str]): Node on which the command has
            to be executed. Default value is g.config['servers'][0]['host'].
    Returns:
        bool: True if successful, False otherwise.
    '''
    if mnode is None:
        mnode = g.config['servers'][0]['host']
    if option:
        ret = vol_set_nfs_disable(volname)
        if not ret:
            return False
        volinfo = get_volume_info(volname, mnode)
        enable = volinfo[volname]['options'].get('ganesha.enable')
        if enable == "on":
            g.log.info(" ganesha is already enabled for the volume %s"
                           % volname)
            return True
        ret, _, _ = g.run(mnode, "gluster volume set %s ganesha.enable on "
                           "--mode=script" % volname)
        if ret != 0:
            g.log.error("failed to set ganesha.enable on %s" % volname)
            return False
    else:
        ret, _, _ = g.run(mnode, "gluster volume set %s ganesha.enable off "
                           "--mode=script" % volname)
        if ret != 0:
            return False

    return True


def validate_ganesha_ha_status(mnode=None):
    '''Validates Ganesha HA Status.
    Kwargs:
        mnode (Optional[str]): Node on which the command has
            to be executed. Default value is g.config['servers'][0]['host'].
    Returns:
        bool: True if successful(HA status is correct),
            False otherwise.
    '''
    if mnode is None:
        mnode = g.config['servers'][0]['host']
    ret, out, _ = g.run(mnode, "/usr/libexec/ganesha/ganesha-ha.sh --status "
                         "| grep -v 'Online' | cut -d ' ' -f 1 | sed s/"
                         "'-cluster_ip-1'//g | sed s/'-trigger_ip-1'//g")
    if ret != 0:
        g.log.error("failed to execute the ganesha-ha status command")
        return False
    list1 = filter(None, out.split("\n"))

    ret, out, _ = g.run(mnode, "/usr/libexec/ganesha/ganesha-ha.sh --status "
                         "| grep -v 'Online' | cut -d ' ' -f 2")
    if ret != 0:
        g.log.error("failed to execute the ganesha-ha status command")
        return False
    list2 = filter(None, out.split("\n"))

    if list1 == list2:
        g.log.info("ganesha ha status is correct")
        return True

    g.log.error("ganesha ha status is incorrect")
    return False


def set_nfs_ganesha(option=True, mnode=None):
    '''Enables/Disables NFS-Ganesha Cluster
    Kwargs:
        option (Optional[bool]): If True it enables the nfs-ganesha
            HA Cluster, else disables the nfs-ganesha HA Cluster.
            Default value is True.
        mnode (Optional[str]): Node on which the command has
            to be executed. Default value is g.config['servers'][0]['host'].
    Returns:
        bool: True if successful, False otherwise.
    '''
    if mnode is None:
        mnode = g.config['servers'][0]['host']
    servers = nodes_from_pool_list()
    no_of_servers = len(servers)
    if option:
        ret, _, _ = g.run(mnode, "gluster nfs-ganesha enable --mode=script")
        if ret == 0:
            g.log.info("nfs-ganesha enable success")
            time.sleep(45)
            ret, _, _ = g.run(mnode, "pcs status")
            ret = validate_ganesha_ha_status(mnode)
            if ret:
                return True
            else:
                return False
        else:
            g.log.error("nfs-ganesha enable falied")
            return False
    else:
        ret, _, _ = g.run(g.config['servers'][0]['host'], "gluster nfs-ganesha disable "
                           "--mode=script")
        if ret == 0:
            g.log.info("nfs-ganesha disable success")
            time.sleep(10)
            for node in g.config['servers'][0:no_of_servers]:
                ret, _, _ = g.run(node, "pcs status")
            return True
        else:
            g.log.error("nfs-ganesha disable falied")
            return False


def get_host_by_name(servers=None):
    '''Get hostname of the specified servers.
    Kwargs:
        servers (Optional[str]): Get hostnames of the specified servers.
    Returns:
        dict: dict with 'hostname or ip_address" of the server as key and
              'hostname' of the server as value.
    '''
    if servers is None:
        servers = nodes_from_pool_list()

    if not isinstance(servers, list):
        servers = [servers]

    server_hostname_dict = OrderedDict()
    for server in servers:
        server_hostname_dict[server] = socket.gethostbyaddr(server)[0]

    return server_hostname_dict


def create_nfs_passwordless_ssh(snodes=[], guser=None, mnode=None):
    '''Sets up the passwordless ssh between mnode and all other snodes.
    Args:
        snodes (list): List of nodes for which we require passwordless
            ssh from mnode.
    Kwargs:
        guser (Optional[str]): Username . Default value is root.
        mnode (Optional[str]): Node from which we require passwordless
            ssh to snodes. Default value is g.config['servers'][0]['host'].
    Returns:
        bool: True if successfull, False otherwise
    '''
    if guser is None:
        guser = 'root'
    if mnode is None:
        mnode = g.config['servers'][0]['host']
    if not isinstance(snodes, list):
        snodes = [snodes]
    loc = "/var/lib/glusterd/nfs/"
    mconn = g.rpyc_get_connection(mnode, user='root')
    if not mconn.modules.os.path.isfile('/root/.ssh/id_rsa'):
        if not mconn.modules.os.path.isfile('%s/secret.pem' % loc):
            ret, _, _ = g.run(mnode, "ssh-keygen -f /var/lib/glusterd/nfs/"
                               "secret.pem -q -N ''")
            if ret != 0:
                g.log.error("Unable to generate the secret pem file")
                return False
        mconn.modules.os.chmod("%s/secret.pem" % loc, 0600)
        mconn.modules.shutil.copyfile("%s/secret.pem" % loc,
                                      "/root/.ssh/id_rsa")
        mconn.modules.os.chmod("/root/.ssh/id_rsa", 0600)
        g.log.debug("Copying the secret.pem.pub to id_rsa.pub")
        mconn.modules.shutil.copyfile("%s/secret.pem.pub" % loc,
                                      "/root/.ssh/id_rsa.pub")
    else:
        mconn.modules.shutil.copyfile("/root/.ssh/id_rsa",
                                      "%s/secret.pem" % loc)
        mconn.modules.os.chmod("%s/secret.pem" % loc, 0600)
        g.log.debug("Copying the id_rsa.pub to secret.pem.pub")
        mconn.modules.shutil.copyfile("/root/.ssh/id_rsa.pub",
                                      "%s/secret.pem.pub" % loc)
    if not isinstance(snodes, list):
        snodes = [snodes]
    for snode in snodes:
        sconn = g.rpyc_get_connection(snode, user=guser)
        try:
            slocal = sconn.modules.os.path.expanduser('~')
            sfh = sconn.builtin.open("%s/.ssh/authorized_keys" % slocal, "a")
            with mconn.builtin.open("/root/.ssh/id_rsa.pub", 'r') as f:
                for line in f:
                    sfh.write(line)
        except:
            g.log.error("Unable to establish passwordless ssh %s@%s to "
                            "%s@%s" % ('root', mnode, guser, snode))
            return False
        finally:
            sfh.close()
# FIXME:            sconn.close()
# FIXME:    mconn.close()
    time.sleep(30)
    for snode in snodes:
        ret, _, _ = g.run(mnode, "ssh-keyscan -H %s  >> ~/.ssh/known_hosts"
                           % snode)
        if snode != mnode:
            ret, _, _ = g.run(mnode, "scp /var/lib/glusterd/nfs/secret.*  "
                               "%s:/var/lib/glusterd/nfs/" % snode)
            if ret != 0:
                return False

    return True


def validate_ganesha_ha_failover(mnode=None, snodes=None):
    '''Validates HA failover status
    Kwargs:
         mnode (Optional[str]): Node on which the ha status command has
            to be executed. Default value is g.config['servers'][0]['host'].
         snodes (Optional[str]): Node/Nodes on which ganesha process is
            Killed/stopped or Node shutdown
    Returns:
         bool: True if successfull, False otherwise.
    '''
    if mnode is None:
        mnode = g.config['servers'][0]['host']
    if snodes is None:
        snodes = g.config['servers'][1]['host']
    if not isinstance(snodes, list):
        snodes = [snodes]
    ha_flag = True
    ret, out, _ = g.run(mnode, "/usr/libexec/ganesha/ganesha-ha.sh --status "
                         "| grep -v 'Online' | grep -v 'dead' | cut -d ' ' "
                         "-f 1 | sed s/'-cluster_ip-1'//g | sed s/"
                         "'-trigger_ip-1'//g")
    if ret == 0:
        list1 = filter(None, out.split("\n"))
    ret, out, _ = g.run(mnode, "/usr/libexec/ganesha/ganesha-ha.sh --status "
                         "| grep -v 'Online' | grep -v 'dead' | cut -d ' ' "
                         "-f 2 | sed s/'-cluster_ip-1'//g | sed s/"
                         "'-trigger_ip-1'//g")
    if ret == 0:
        list2 = filter(None, out.split("\n"))
    server_hostname_dict = get_host_by_name()
    snodes_hostnames = []
    for snode in snodes:
        snodes_hostnames.append(server_hostname_dict[snode])
    for val1, val2 in zip(list1, list2):
        if val1 in snodes_hostnames:
            if val1 == val2:
                g.log.error("Failover dint happen, wrong failover status "
                                "-> %s %s" % (val1, val2))
                ha_flag = False
            else:
                g.log.info("%s successfully failed over on %s"
                               % (val1, val2))
        else:
            if val1 != val2:
                g.log.error("Failover not required, wrong failover status "
                                "-> %s %s" % (val1, val2))
                ha_flag = False

    return ha_flag


def get_ganesha_ha_failover_nodes(mnode=None, snodes=None):
    '''Returns HA status and dictionary of
    Kwargs:
         mnode (Optional[str]): Node on which the ha status command has
            to be executed. Default value is g.config['servers'][0]['host'].
         snodes (Optional[str]): Node/Nodes on which ganesha process
            is Killed/stopped or Node shutdown
    Returns:
         bool,dict: If successfull True,dict
            False otherwise
    '''
    if mnode is None:
        mnode = g.config['servers'][0]['host']
    if snodes is None:
        snodes = g.config['servers'][1]['host']
    if not isinstance(snodes, list):
        snodes = [snodes]
    ha_flag = True
    tnode = OrderedDict()
    ret, out, _ = g.run(mnode, "/usr/libexec/ganesha/ganesha-ha.sh --status "
                         "| grep -v 'Online' | grep -v 'dead' | cut -d ' ' "
                         "-f 1 | sed s/'-cluster_ip-1'//g | sed s/"
                         "'-trigger_ip-1'//g")
    if ret == 0:
        list1 = filter(None, out.split("\n"))
    ret, out, _ = g.run(mnode, "/usr/libexec/ganesha/ganesha-ha.sh --status "
                         "| grep -v 'Online' | grep -v 'dead' | cut -d ' ' "
                         "-f 2 | sed s/'-cluster_ip-1'//g | sed s/"
                         "'-trigger_ip-1'//g")
    if ret == 0:
        list2 = filter(None, out.split("\n"))
    server_hostname_dict = get_host_by_name()
    snodes_hostnames = []
    for snode in snodes:
        snodes_hostnames.append(server_hostname_dict[snode])
    for val1, val2 in zip(list1, list2):
        if val1 in snodes_hostnames:
            if val1 == val2:
                g.log.error("Failover dint happen, wrong failover status "
                                "-> %s %s" % (val1, val2))
                ha_flag = False
            else:
                tnode[server_hostname_dict[val1]] = server_hostname_dict[val2]
                g.log.info("%s successfully failed over on %s"
                               % (val1, val2))
        else:
            if val1 != val2:
                g.log.error("Failover not required, wrong failover status "
                                "-> %s %s" % (val1, val2))
                ha_flag = False

    return (ha_flag, tnode)


def update_ganesha_ha_conf(no_of_servers=None):
    '''Updates the ganesha-ha.conf file, with VIPs and hostnames.
    Kwargs:
        no_of_servers (Optional[int]): The number of nodes on which we have
            to modify the ganesha-ha.conf file. Default it takes
            the number of servers from the pool list.
    Returns:
        bool: True if successfull, False otherwise.
    '''
    if no_of_servers is None:
        servers = nodes_from_pool_list()
        no_of_servers = len(servers)
    else:
        servers = g.config['servers'][0:no_of_servers]
    server_hostname_dict = get_host_by_name(servers)
    hostnames = server_hostname_dict.values()
    hosts = ','.join(hostnames)
    file_src_path = "/etc/ganesha/ganesha-ha.conf.sample"
    file_dest_path = "/etc/ganesha/ganesha-ha.conf"
    ha_server = g.run(g.config['servers'][0]['host'], "hostname")
    conn = g.rpyc_get_connection(g.config['servers'][0]['host'], "root")
    if conn.modules.os.path.isfile(file_src_path) == True:
        g.log.info("%s file available and should be updated as "
                       "ganesha-ha.conf" % file_src_path)
        try:
            conn.modules.shutil.copy(file_src_path, file_dest_path)
            FH = conn.builtin.open(file_dest_path, "r+")
        except IOError as e:
            g.log.error(e)
            return False
    lines = FH.readlines()
    FH.seek(0)
    FH.truncate()
    for i in range(len(lines)):
        if re.search("HA_NAME", lines[i]) != None:
            lines[i] = re.sub(r'^HA_NAME.*', "HA_NAME=\"G"+str(time.time()) +
                              "\"", lines[i])
        if re.search("HA_VOL_SERVER", lines[i]) != None:
            lines[i] = re.sub(r'^HA_VOL_SERVER.*', "HA_VOL_SERVER=\"" +
                              ha_server[1].strip()+"\"", lines[i])
        if re.search("HA_CLUSTER_NODES", lines[i]) != None:
            lines[i] = re.sub(r'^HA_CLUSTER_NODES.*', "HA_CLUSTER_NODES=\"" +
                              hosts+"\"", lines[i])
        if re.search("VIP_", lines[i]) != None:
            lines[i] = re.sub(r'.*VIP_.*\n', "", lines[i])
    vips = (tc.global_config["gluster"]["cluster_config"]
            ["nfs_ganesha"]["vips"])
    for i in range(no_of_servers):
        lines += "VIP_%s=\"%s\"\n" % (hostnames[i], vips[i])
    FH.write(''.join(lines))
    # create a local copy of this ha.conf file
    f = open("/tmp/ganesha-ha.conf", "w")
    f.write(''.join(lines))
    f.close()
    FH.close()
# FIXME: conn.close()
    # copy this ha.conf file to all the other nodes
    for node in g.config['servers'][1:no_of_servers]:
        ret = g.upload(node, "/tmp/ganesha-ha.conf", file_dest_path)

    return True


def cluster_auth_setup(no_of_servers=None):
    '''Sets the hacluster password, starts pcsd service and runs
       pcs cluster auth command.
    Kwargs:
        no_of_servers (Optional[int]): The number of nodes on which we have
            to setup the HA cluster. Default it takes the number
            of servers from the pool list.
    Returns:
        bool: True if successfull, False otherwise.
    '''
    if no_of_servers is None:
        servers = nodes_from_pool_list()
        no_of_servers = len(servers)
    else:
        servers = g.config['servers'][0:no_of_servers]
    result = True
    for node in g.config['servers'][0:no_of_servers]:
        ret, _, _ = g.run(node, "echo hacluster | passwd --stdin hacluster")
        if ret != 0:
            g.log.error("unable to set password for hacluster on %s"
                            % node)
            return False
        else:
            ret, _, _ = g.run(node, "service pcsd start")
            if ret != 0:
                tc.looger.error("service pcsd start command failed on %s"
                                % node)
                return False
    server_hostname_dict = get_host_by_name(servers)
    for node in g.config['servers'][0:no_of_servers]:
        val = ""
        for key in server_hostname_dict:
            val += server_hostname_dict[key]
            val += " "
        ret, _, _ = g.run(node, "pcs cluster auth %s -u hacluster -p "
                           "hacluster" % val)
        if ret != 0:
                g.log.error("pcs cluster auth command failed on %s" % node)
                result = False

    return result


def setup_nfs_ganesha(no_of_servers=None):
    '''Setup NFS-Ganesha HA cluster.
    Kwargs:
        no_of_servers (Optional[int]): The number of nodes on which we have
            to setup the HA cluster. Default it takes the number
            of servers from the pool list.
    Returns:
        bool: True if successfull, False otherwise.
    '''
    if ('setup_nfs_ganesha' in tc.global_flag and
            tc.global_flag['setup_nfs_ganesha'] == True):
        g.log.debug("The setup nfs-ganesha is already setup, returning...")
        return True
    if no_of_servers is None:
        servers = g.config['servers']
        no_of_servers = len(servers)
    servers = g.config['servers'][0:no_of_servers]
    no_of_servers = int(no_of_servers)
    # Step 1: Peer probe
    ret = peer_probe_servers(g.config['servers'][1:no_of_servers], mnode=g.config['servers'][0]['host'])
    if not ret:
        return False
    # Step 2: Passwordless ssh for nfs
    ret = create_nfs_passwordless_ssh(snodes=g.config['servers'][0:no_of_servers],
                                      mnode=g.config['servers'][0]['host'])
    if ret:
        g.log.info("passwordless ssh between nodes successfull")
    else:
        g.log.error("passwordless ssh between nodes unsuccessfull")
        return False
    # Step 3: Update ganesha-ha.conf file
    ret = update_ganesha_ha_conf(no_of_servers)
    if ret:
        g.log.info("ganesha-ha.conf files succeessfully updated on all "
                       "the nodes")
    else:
        g.log.error("ganesha-ha.conf files not succeessfully updated on "
                        "all the nodes")
        return False
    # Step 4: Cluster setup
    ret = cluster_auth_setup(no_of_servers)
    if ret:
        g.log.info("successfull cluster setup")
    else:
        g.log.error("unsuccessfull cluster setup")
        return False
    # Step 5: Using CLI to create shared volume
    ret, _, _ = g.run(g.config['servers'][0]['host'], "gluster v list | grep "
                       "'gluster_shared_storage'")
    if ret != 0:
        ret, _, _ = g.run(g.config['servers'][0]['host'], "gluster volume set all "
                           "cluster.enable-shared-storage enable")
        if ret != 0:
            g.log.error("shared volume creation unsuccessfull")
            return False
        else:
            g.log.info("shared volume creation successfull")
            time.sleep(10)
    else:
        g.log.info("shared volume already exists")
    time.sleep(60)
    # Step 6: Enable NFS-Ganesha
    ret = set_nfs_ganesha(True)
    if ret:
        g.log.info("gluster nfs-ganesha enable success")
    else:
        g.log.error("gluster nfs-ganesha enable failed")
        return False
    # Setting globalflag to True
    tc.global_flag["setup_nfs_ganesha"] = True

    return True


def teardown_nfs_ganesha_setup(mnode=None):
    '''Teardowns the NFS-Ganesha HA setup.
    Kwargs:
        mnode (Optional[str]): Node on which the command has
            to be executed. Default value is g.config['servers'][0]['host'].
    Returns:
        bool: True if successful, False otherwise.
    '''
    if mnode is None:
        mnode = g.config['servers'][0]['host']
    # Step 1: Disable NFS-Ganesha
    ret = set_nfs_ganesha(False)
    if ret:
        g.log.info("gluster nfs-ganesha disable success")
    else:
        g.log.error("gluster nfs-ganesha disable failed")
        return False
    # Step 2: Using CLI to delete the shared volume
    ret, _, _ = g.run(mnode, "gluster volume set all "
                       "cluster.enable-shared-storage disable --mode=script")
    if ret != 0:
        g.log.error("shared volume deletion unsuccessfull")
        return False
    else:
        g.log.info("shared volume deletion successfull")
    # Setting globalflag to False
    tc.global_flag["setup_nfs_ganesha"] = False

    return True
