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


from glusto.core import Glusto as g
import re
"""
    This file contains the glusterd and other initial gluster
    options like start/stop glusterd and env_setup_servers for
    initial back-end brick preperation
"""


def start_glusterd(servers=''):
    """
        Starts glusterd in all servers if they are not running

        Returns True if glusterd started in all servers
        Returns False if glusterd failed to start in any server

        (Will be enhanced to support systemd in future)
    """
    if servers == '':
        servers = g.config['servers']
    ret, _ = g.run_serial(servers, "pgrep glusterd || service glusterd start")
    return ret


def stop_glusterd(servers=''):
    """
        Stops the glusterd in specified machine(s)

        Returns True if glusterd is stopped in all nodes
        Returns False on failure
    """
    if servers == '':
        servers = g.config['servers']
    ret, _ = g.run_serial("service glusterd stop", servers=servers)
    return ret


#TODO: THIS IS NOT IMPLEMENTED YET. PLEASE DO THIS MANUALLY
#      TILL WE IMPLEMENT THIS PART

def env_setup_servers(snap=True, servers=''):
    """
        Sets up the env for all the tests
        Install all the gluster bits and it's dependencies
        Installs the xfs bits and then formats the backend fs for gluster use

        Returns 0 on success and non-zero upon failing
    """
    g.log.info("The function isn't implemented yet")
    g.log.info("Please setup the bricks manually.")

    if servers == '':
        servers = g.config['servers']

    if not start_glusterd(servers):
        return False

    return True
