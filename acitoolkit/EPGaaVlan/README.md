# EPGaaVlan

This script leverages the acitoolkit to configure network centric policy using either manually passed arguments or through a csv.

# Pre-requisites

This script leverages the ACI Toolkit which must be installed prior to running.

- https://github.com/datacenter/acitoolkit.git

# Usage Examples

### Deploy from csv with flooding enabled and routing disabled
```
python EPGaaVLAN.py --netTenant "common" `
                    --appTenant "Network-Centric-Prod" `
                    --anp "Network-EPGs" `
                    --vlanPool "Network-Centric-Prod-VLANs" `
                    --vrf "Prod" `
                    --csv prod_vlans.csv `
                    --enableFlooding
```
### Deploy from csv with routing enabled and flooding disabled
```
python EPGaaVLAN.py --netTenant "common" `
                    --appTenant "Network-Centric-Prod" `
                    --anp "Network-EPGs" `
                    --vlanPool "Network-Centric-Prod-VLANs" `
                    --vrf "Prod" `
                    --csv prod_vlans.csv `
                    --enableRouting
```
### Deploy single epg-vlan with flooding enabled and routing disabled
```
python EPGaaVLAN.py --netTenant "common" `
                    --appTenant "Network-Centric-Prod" `
                    --anp "Network-EPGs" `
                    --vlanPool "Network-Centric-Prod-VLANs" `
                    --vrf "Prod" `
                    --vlanNumber "100" `
                    --vlanName "10.100.1.0_24-Dev-Network" `
                    --vlanDescr "imported from vlan-100" `
                    --gateway "10.100.1.1/24" `
                    --enableFlooding
```
