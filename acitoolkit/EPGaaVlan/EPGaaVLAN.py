from acitoolkit import *
import json
import os
import csv

description='ACIToolkit script for configuring Network-Centric ACI Policies from existing VLANs'
creds = Credentials('apic', description)
creds.add_argument('--vlanPool', help='Vlan Pool Name', required=True)
creds.add_argument('--vlanNumber', help='Vlan Number', required=False)
creds.add_argument('--vlanDescription', help='Vlan Description', required=False)
creds.add_argument('--networkTenant', help='Network Tenant', required=True)
creds.add_argument('--vrf', help='vrf', required=True)
creds.add_argument('--applicationTenant', help='Application Tenant',required=True)
creds.add_argument('--applicationNetworkProfile', help='Application Network Profile',required=True)
creds.add_argument('--vlanName', help='VLAN/EPG Name',required=False)
creds.add_argument('--csv', help='csv filename for import',required=False)
creds.add_argument('--enableRouting', help='Enable unicast routing within BD',required=False, action='store_true')
creds.add_argument('--enableFlooding', help='Enable flooding within BD',required=False, action='store_true')
creds.add_argument('--gatewayIP', help='X.X.X.X/X Gateway IP',required=False)
creds.add_argument('--apicUrl', help='APIC URL',required=True)
creds.add_argument('--apicUsername', help='APIC Username',required=True)
creds.add_argument('--apicPassword', help='APIC Password',required=True)
creds.add_argument('--vzany', help='Use VZAny',required=False,action='store_true')
args = creds.get()

if args["csv"] is None and (args["vlanNumber"] is None or args["vlanName"] is None or args["gatewayIP"] is None):
    creds.error("Either a csv or specific vlan #, vlan name, and gateway IP is required.  Please see help for details")

def prettyPrint(target):
    print json.dumps(target.get_json(),sort_keys=True,indent=4)

def CreateEpgVlan(vlanName, description, gatewayIP):
    bd_net1 = BridgeDomain(vlanName,networkTenant)
    bd_net1.add_context(vrf)
    bd_net1.set_description(description)

    if (args["enableRouting"]):
        net1 = Subnet("",bd_net1)
        net1.set_addr(gatewayIP)
        net1.set_scope("private")
    else:
        bd_net1.set_unicast_route("no")

    if (args["enableFlooding"]):
        bd_net1.set_unknown_mac_unicast("flood")
        bd_net1.set_arp_flood("yes")

    epg_net1 = EPG(vlanName,app)
    epg_net1.add_bd(bd_net1)

    if (args["vzany"]):
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

networkTenant = Tenant(args["networkTenant"])
vrf = Context(args["vrf"],networkTenant)
appTenant = Tenant(args["applicationTenant"])

app = AppProfile(args["applicationNetworkProfile"],appTenant)
vlan_list = []
if args["csv"] is not None:
    with open(args["csv"], 'rb') as f:
        reader = csv.reader(f)
        vlan_csv = list(reader)
    for vlan in vlan_csv:
        if vlan[0].isdigit():
            CreateEpgVlan(vlan[1], vlan[2], vlan[3])
            vlan_list.append(int(vlan[0]))
else:
    CreateEpgVlan(args["vlanName"], args["vlanDescription"], args["gatewayIP"])
    vlan_list.append(int(args["vlanNumber"]))

# Login to APIC
session = aci.Session(args.url, args.login, args.password)
resp = session.login()
if not resp.ok:
    print('%% Could not login to APIC')
    sys.exit(0)

prettyPrint(networkTenant)
print networkTenant.push_to_apic(session)
appTenant.push_to_apic(session)
for vlan_range in list(GetVlanGroups(vlan_list)):
    vlans = NetworkPool(args["vlanPool"], "vlan", str(vlan_range[0]), str(vlan_range[1]), 'static')
    session.push_to_apic(vlans.get_url(), vlans.get_json())
session.close()

'''
Prod
PS C:\Users\robbeck> py -2 .\EPGaaVLAN.py --networkTenant "common" --applicationTenant "Network-Centric-Prod" --applicationNetworkProfile "Network-EPGs" --vlanPool "Network-Centric-Prod-VLANs" --vrf "Prod" --csv prod_vlans.csv --enableRouting
Dev
PS C:\Users\robbeck> py -2 .\EPGaaVLAN.py --networkTenant "common" --applicationTenant "Basic-Tenant-DMZ" --applicationNetworkProfile "Network-EPGs" --vlanPool "Network-Centric-DMZ-VLANs" --vrf "DMZ" --csv dev_vlans.csv --enableRouting
'''
