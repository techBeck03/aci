"""
This script leverages the acitoolkit to clone an existing
interface policy group specified by name, description, or
selected from a printed list.


The script will query for username and password when run, or could be provided
via command line arguments.

Args:
(o) - optional
(e) - mutually exclusive

--qname          (e) Name used to filter query for the target interface policy group
--qdescr         (e) Name used to filter query for the target interface policy group
--listSelect     (e) Select the target policy group from a list
--listFilter     (o) Wildcard filter used on description field to build pg list
--pgname         (o) Name of the newly cloned policy group
--descr          (o) Description of the newly cloned policy group
--verbose        (o) Enable verbose logging

This script leverages the acitoolkit.  https://github.com/datacenter/acitoolkit.git

Usage Examples:
Clone by policy group name
python aci-clone-int-policy-group.py --qname aci-esx-02-vpc --pgname aci-esx-06-vpc

Clone by policy group description
python aci-clone-int-policy-group.py --qdescr esx-template --pgname aci-esx-06-vpc

Select policy group to clone from a list of all existing interface policy groups
python aci-clone-int-policy-group.py --listSelect --pgname aci-esx-06-vpc

Select policy group to clone with "template" somewhere in the description
python aci-clone-int-policy-group.py --listSelect --listFilter template --pgname aci-esx-06-vpc

"""
import sys
import os
import re
import json
import acitoolkit.acitoolkit as aci

def prettyPrint(target):
    print json.dumps(target,sort_keys=True,indent=4)

def main():
    description = ('Simple application that logs on to the APIC and clones the target interface policy group')
    creds = aci.Credentials('apic', description)
    group = creds.add_mutually_exclusive_group(required=True)
    group.add_argument('--qname', help='Filter the query by name')
    group.add_argument('--qdescr', help='Filter the query by description')
    group.add_argument('--listSelect', help='Select the target policy from a list',action='store_true')
    creds.add_argument('--listFilter', help='Wildcard filter used on description field to build pg list ', required=False, default="")
    creds.add_argument('--pgname', help='Name of the cloned policy group', required=False,default="")
    creds.add_argument('--descr', help='Description for the cloned policy group', required=False, default="")
    creds.add_argument('--verbose', help='Enable verbose logging', required=False,action='store_true')

    args = creds.get()
    if not args.pgname:
        args.pgname = raw_input("\nPlease enter a name for the new policy group: ")
    # Login to APIC
    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        sys.exit(0)

    # Setup query filters
    if args.qname:
        qfilter = 'query-target-filter=and(eq(infraAccBndlGrp.name,"'+args.qname+'"))'
    elif args.qdescr:
        qfilter = 'query-target-filter=and(eq(infraAccBndlGrp.descr,"'+args.qdescr+'"))'
    elif args.listSelect:
        qfilter = 'query-target-filter=and(wcard(infraAccBndlGrp.descr,"'+args.listFilter+'"))'
    else:
        qfilter = ''

    # Class url to query for interface policy groups
    class_url = '/api/node/class/infraAccBndlGrp.json?'+qfilter+'&rsp-subtree=full&rsp-prop-include=config-only'

    # Send get request to APIC and validate results
    ret = session.get(class_url)
    if len(ret.json()["imdata"]) < 1:
        print "%% Error: No matching policy group found:"
        exit()
    if len(ret.json()["imdata"]) > 1 and not args.listSelect:
        print "%% Error: Multiple matches found:"
        for pg in ret.json()["imdata"]:
            print pg["infraAccBndlGrp"]["attributes"]["dn"]
        exit()
    if not args.listSelect:
        # Grab the json response containing the policy group
        clone = ret.json()["imdata"][0]
    else:
        os.system('cls')
        while True:
            for index,pg in enumerate(ret.json()["imdata"]):
                print str(index + 1)+') '+pg["infraAccBndlGrp"]["attributes"]["name"]
            selected = raw_input("\n\nPlease select interface policy group to be cloned: ")
            if int(selected) > 0 and int(selected) <= len(ret.json()["imdata"]):
                # Grab the json response containing the policy group
                clone = ret.json()["imdata"][int(selected) - 1]
                break
            else:
                os.system('cls')
                print '****Invalid selection please select a number from the list below****'

    # Grab the original name of the cloned profile
    originalName = clone["infraAccBndlGrp"]["attributes"]["name"]

    # Rename clone properties
    clone["infraAccBndlGrp"]["attributes"]["dn"] = re.sub(r"(?<=accbundle[-]).*",args.pgname,clone["infraAccBndlGrp"]["attributes"]["dn"])
    clone["infraAccBndlGrp"]["attributes"]["name"] = args.pgname
    clone["infraAccBndlGrp"]["attributes"]["rn"] = 'accbundle-'+args.pgname
    clone["infraAccBndlGrp"]["attributes"]["status"] = "created"
    clone["infraAccBndlGrp"]["attributes"]["descr"] = args.descr

    # Print clone json object
    if args.verbose:
        prettyPrint(clone)

    # Push cloned interface policy group to APIC
    postUrl = '/api/node/mo/uni/infra/funcprof/accbundle-'+args.pgname+'.json'
    resp = session.push_to_apic(postUrl,clone)

    if not resp.ok:
        print('%% Error: Could not push configuration to APIC')
        print(resp.text)
    else:
        print "\n%% Success: "+originalName+' successfully cloned to '+args.pgname+"\n\n"

    session.close()

if __name__ == '__main__':
    main()
