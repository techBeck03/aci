"""
This script leverages the acitoolkit to configure network centric policy using
either manually passed arguments or through a csv.


The script will query for username and password when run, or could be provided
via command line arguments.

Args:
(m) - mandatory
(o) - optional

--anp               (m) Application Network Profile for net-centric EPGs
--appTenant         (m) Application Tenant for net-centric EPGs
--csv               (o) csv filename for import
--enableFlooding    (o) Enable flooding within BD
--enableRouting     (o) Enable unicast routing within BD
--gateway           (o) X.X.X.X/X Gateway IP
--netTenant         (o) Network Tenant for net-centric bridge domains and vrf
--vlanDescr         (o) Vlan Description (used on bridge domain)
--vlanName          (o) VLAN/EPG Name
--vlanNumber        (o) Vlan Number
--vlanPool          (m) Vlan Pool Name
--vrf               (m) VRF used for net-centric bridge domains
--vzany             (o) Use VZAny (not recommended)

This script leverages the acitoolkit.  https://github.com/datacenter/acitoolkit.git

Usage Examples:
Deploy from csv with flooding enabled and routing disabled
python EPGaaVLAN.py --netTenant "common" \
                    --appTenant "Network-Centric-Prod" \
                    --anp "Network-EPGs" \
                    --vlanPool "Network-Centric-Prod-VLANs" \
                    --vrf "Prod" \
                    --csv prod_vlans.csv \
                    --enableFlooding

Usage Examples:
Deploy from csv with routing enabled and flooding disabled
python EPGaaVLAN.py --netTenant "common" \
                    --appTenant "Network-Centric-Prod" \
                    --anp "Network-EPGs" \
                    --vlanPool "Network-Centric-Prod-VLANs" \
                    --vrf "Prod" \
                    --csv prod_vlans.csv \
                    --enableRouting

Usage Examples:
Deploy single epg-vlan with flooding enabled and routing disabled
python EPGaaVLAN.py --netTenant "common" \
                    --appTenant "Network-Centric-Prod" \
                    --anp "Network-EPGs" \
                    --vlanPool "Network-Centric-Prod-VLANs" \
                    --vrf "Prod" \
                    --vlanNumber "100" \
                    --vlanName "10.100.1.0_24-Dev-Network" \
                    --vlanDescr "imported from vlan-100" \
                    --gateway "10.100.1.1/24" \
                    --enableFlooding
"""
from acitoolkit import *
import json
import os
import csv

description='ACIToolkit script for configuring Network-Centric ACI Policies from existing VLANs'
creds = Credentials('apic', description)
creds.add_argument('--anp', help='Application Network Profile',required=True)
creds.add_argument('--appTenant', help='Application Tenant',required=True)
creds.add_argument('--csv', help='csv filename for import',required=False)
creds.add_argument('--enableFlooding', help='Enable flooding within BD',required=False, action='store_true')
creds.add_argument('--enableRouting', help='Enable unicast routing within BD',required=False, action='store_true')
creds.add_argument('--gateway', help='X.X.X.X/X Gateway IP',required=False)
creds.add_argument('--netTenant', help='Network Tenant', required=True)
creds.add_argument('--vlanDescr', help='Vlan Description', required=False)
creds.add_argument('--vlanName', help='VLAN/EPG Name',required=False)
creds.add_argument('--vlanNumber', help='Vlan Number', required=False)
creds.add_argument('--vlanPool', help='Vlan Pool Name', required=True)
creds.add_argument('--vrf', help='vrf', required=True)
creds.add_argument('--vzany', help='Use VZAny',required=False,action='store_true')

args = creds.get()

# Validate arguments
if args.csv is None and (args.vlanNumber is None or args.vlanName is None or args.gateway is None):
    creds.error("Either a csv or specific vlan #, vlan name, and gateway IP is required.  Please see help for details")

def prettyPrint(target):
    print json.dumps(target.get_json(),sort_keys=True,indent=4)

# Function for creating network centric aci policies
def CreateEpgVlan(vlanName, description, gateway):
    bd_net1 = BridgeDomain(vlanName,networkTenant)
    bd_net1.add_context(vrf)
    # Requires modified ACItoolkit
    bd_net1.set_description(description)

    if (args.enableRouting):
        net1 = Subnet("",bd_net1)
        net1.set_addr(gateway)
        net1.set_scope("private")
    else:
        bd_net1.set_unicast_route("no")

    if (args.enableFlooding):
        bd_net1.set_unknown_mac_unicast("flood")
        bd_net1.set_arp_flood("yes")

    epg_net1 = EPG(vlanName,app)
    epg_net1.add_bd(bd_net1)

    if (args.vzany):
        filter = Filter("Permit-All",networkTenant)
        entry = FilterEntry("Permit-All",filter)

        contract = Contract("Permit-All",networkTenant)
        subject = ContractSubject("Permit-All",contract)
        subject.add_filter(filter)

        any_epg = AnyEPG('any-epg',vrf)
        any_epg.consume(contract)
        any_epg.provide(contract)

    else:
        filter = Filter("Permit-All",appTenant)
        entry = FilterEntry("Permit-All",filter)

        contract = Contract("Permit-All",appTenant)
        subject = ContractSubject("Permit-All",contract)
        subject.add_filter(filter)

        epg_net1.consume(contract)
        epg_net1.provide(contract)

def GetVlanGroups(vlans):
    first = last = vlans[0]
    for n in vlans[1:]:
        if n - 1 == last: # Part of the group, bump the end
            last = n
        else: # Not part of the group, yield current group and start a new
            yield first, last
            first = last = n
    yield first, last # Yield the last group

networkTenant = Tenant(args.netTenant)
vrf = Context(args.vrf, networkTenant)
appTenant = Tenant(args.appTenant)

app = AppProfile(args.anp, appTenant)
vlan_list = []
if args.csv is not None:
    with open(args.csv, 'rb') as f:
        reader = csv.reader(f)
        vlan_csv = list(reader)
    for vlan in vlan_csv:
        if vlan[0].isdigit():
            CreateEpgVlan(vlan[1], vlan[2], vlan[3])
            vlan_list.append(int(vlan[0]))
else:
    CreateEpgVlan(args.vlanName, args.vlanDescr, args.gateway)
    vlan_list.append(int(args.vlanNumber))

# Login to APIC
session = Session(args.url, args.login, args.password)
resp = session.login()
if not resp.ok:
    print('%% Could not login to APIC')
    sys.exit(0)

prettyPrint(networkTenant)
print networkTenant.push_to_apic(session)
appTenant.push_to_apic(session)
for vlan_range in list(GetVlanGroups(vlan_list)):
    vlans = NetworkPool(args.vlanPool, "vlan", str(vlan_range[0]), str(vlan_range[1]), 'static')
    session.push_to_apic(vlans.get_url(), vlans.get_json())
session.close()
