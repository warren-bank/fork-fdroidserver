#!/usr/bin/env python3
#
# an fdroid plugin print the repo_pubkey from a repo's keystore
#

from argparse import ArgumentParser
from fdroidserver import common, index

fdroid_summary = 'export the keystore in standard PEM format'


def main():
    parser = ArgumentParser()
    common.setup_global_opts(parser)
    options = parser.parse_args()
    common.config = common.read_config(options)
    pubkey, repo_pubkey_fingerprint = index.extract_pubkey()
    print('repo_pubkey = "%s"' % pubkey.decode())


if __name__ == "__main__":
    main()
