import sys
import logging
import requests
from datetime import datetime, time, timezone
from iyp import BaseCrawler

# URL to MANRS csv file
URL = 'https://www.manrs.org/wp-json/manrs/v1/csv/4'
ORG = 'MANRS'
NAME = 'manrs.members'

class Crawler(BaseCrawler):
    def __init__(self, organization, url, name):
        """Fetch nodes for MANRS actions (create them if they are not in IYP).""" 
    
        # connect to IYP database
        super().__init__(organization, url, name)

        self.manrs_qid = self.iyp.get_node(
                                        'Organization',
                                        { 'name': 'MANRS' },
                                        create=True
                                        )
        
        # Actions defined by MANRS
        self.actions = [
              {
                'label': 'MANRS Action 1: Filtering',
                'description': 'Prevent propagation of incorrect routing information'
              },
              { 
                'label': 'MANRS Action 2: Anti-spoofing',
                'description': 'Prevent traffic with spoofed source IP addresses'
              },
              {
                'label': 'MANRS Action 3: Coordination',
                'description': 'Facilitate global operational communication and coordination'
              },
              {
                'label': 'MANRS Action 4: Global Validation',
                'description': 'Facilitate routing information on a global scale'
              }
            ]

        # Get the ID for the four items representing MANRS actions
        for action in self.actions:
            action['qid'] = self.iyp.get_node(
                                            'ManrsAction',
                                            {
                                                'name': action['label'],
                                                'description': action['description']
                                            },
                                            create=True
                                           )

        # Reference information for data pushed to IYP
        self.reference = {
            'reference_name': NAME,
            'reference_org': ORG,
            'reference_url': URL,
            'reference_time': datetime.combine(datetime.utcnow(), time.min, timezone.utc)
            }



    def run(self):
        """Fetch networks information from MANRS and push to wikibase. """

        req = requests.get(URL)
        if req.status_code != 200:
            sys.exit('Error while fetching MANRS csv file')

        for i, row in enumerate( req.text.splitlines() ):
            # Skip the header
            if i == 0:
                continue

            self.update_net(row)
            sys.stderr.write(f'\rProcessed {i} organizations')


    def update_net(self, one_line):
        """Add the network to wikibase if it's not already there and update its
        properties."""

        _, areas, asns, act1, act2, act3, act4 = [col.strip() for col in one_line.split(',')]

        # Properties
        statements = [ 
                ['MEMBER_OF', self.manrs_qid, self.reference],
                ] 

        # set countries
        for cc in areas.split(';'):
            country_qid = self.iyp.get_node('Country', {'country_code': cc}, create=True)
            statements.append([ 'COUNTRY', country_qid, self.reference])

        # set actions
        for i, action_bool in enumerate([act1, act2, act3, act4]):
            if action_bool == 'Yes':
                statements.append([ 'IMPLEMENT', self.actions[i]['qid'], self.reference])

        # Commit to IYP
        for asn in asns.split(';'):
            if asn:     # ignore organizations with no ASN
                # Get the AS QID (create if AS is not yet registered) and commit changes
                as_qid = self.iyp.get_node('AS', {'asn': str(asn)}, create=True) 
                self.iyp.add_links( as_qid, statements )
        
# Main program
if __name__ == '__main__':

    scriptname = sys.argv[0].replace('/','_')[0:-3]
    FORMAT = '%(asctime)s %(processName)s %(message)s'
    logging.basicConfig(
            format=FORMAT, 
            filename='log/'+scriptname+'.log',
            level=logging.INFO, 
            datefmt='%Y-%m-%d %H:%M:%S'
            )
    logging.info("Started: %s" % sys.argv)

    manrs = Crawler(ORG, URL, NAME)
    if len(sys.argv) > 1 and sys.argv[1] == 'unit_test':
        manrs.unit_test(logging)
    else :   
        manrs.run()
        manrs.close()
