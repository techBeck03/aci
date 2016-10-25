"""
Simple application that logs on to the APIC
and clones the target interface policy group
"""
import sys
import re
import json
import acitoolkit.acitoolkit as aci

def prettyPrint(target):
    print json.dumps(target,sort_keys=True,indent=4)

def main():
    description = ('Simple application that logs on to the APIC and clones the target interface policy group')
    creds = aci.Credentials('apic', description)
    creds.add_argument('--qname', help='Filter the query by this name', required=False)
    creds.add_argument('--qdescr', help='Filter the query by this description', required=False)
    creds.add_argument('--pgname', help='Name of the cloned port group', required=True)
    creds.add_argument('--descr', help='Description for the cloned port group', required=False, default="")
    creds.add_argument('--verbose', help='Enable verbose logging', required=False,action='store_true')

    args = creds.get()

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
    else:
        qfilter = ''

    # Class url to query for interface policy groups
    class_url = '/api/node/class/infraAccBndlGrp.json?'+qfilter+'&rsp-subtree=full&rsp-prop-include=config-only'

    ret = session.get(class_url)
    if len(ret.json()["imdata"]) > 1:
        print "%% Error: Multiple matches found:"
        for pg in ret.json()["imdata"]:
            print pg["infraAccBndlGrp"]["attributes"]["dn"]
        exit()
    clone = ret.json()["imdata"][0]
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
        print '%% Success: '+originalName+' successfully cloned to '+args.pgname

    session.close()

if __name__ == '__main__':
    main()
