#!/usr/bin/env python3
#
# gpgsign.py - part of the FDroid server tools
# Copyright (C) 2015, Ciaran Gultnieks, ciaran@ciarang.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
import os
import time
import zipfile
from argparse import ArgumentParser
import logging

from . import _
from . import common
from . import metadata
from .exception import FDroidException

config = None
options = None
start_timestamp = time.gmtime()


def sign_jar(jar):
    """Sign a JAR file with Java's jarsigner.

    This method requires a properly initialized config object.

    This does use old hashing algorithms, i.e. SHA1, but that's not
    broken yet for file verification.  This could be set to SHA256,
    but then Android < 4.3 would not be able to verify it.
    https://code.google.com/p/android/issues/detail?id=38321
    """
    args = [
        config['jarsigner'],
        '-keystore',
        config['keystore'],
        '-storepass:env',
        'FDROID_KEY_STORE_PASS',
        '-digestalg',
        'SHA1',
        '-sigalg',
        'SHA1withRSA',
        jar,
        config['repo_keyalias'],
    ]
    if config['keystore'] == 'NONE':
        args += config['smartcardoptions']
    else:  # smardcards never use -keypass
        args += ['-keypass:env', 'FDROID_KEY_PASS']
    env_vars = {
        'FDROID_KEY_STORE_PASS': config['keystorepass'],
        'FDROID_KEY_PASS': config.get('keypass', ""),
    }
    p = common.FDroidPopen(args, envs=env_vars)
    if p.returncode != 0:
        raise FDroidException("Failed to sign %s!" % jar)


def sign_index_v1(repodir, json_name):
    """Sign index-v1.json to make index-v1.jar.

    This is a bit different than index.jar: instead of their being index.xml
    and index_unsigned.jar, the presence of index-v1.json means that there is
    unsigned data.  That file is then stuck into a jar and signed by the
    signing process.  index-v1.json is never published to the repo.  It is
    included in the binary transparency log, if that is enabled.
    """
    name, ext = common.get_extension(json_name)
    index_file = os.path.join(repodir, json_name)

    # Test if index is valid
    with open(index_file, encoding="utf-8") as fp:
        index = json.load(fp)
        [metadata.App(app) for app in index["apps"]]

    jar_file = os.path.join(repodir, name + '.jar')
    with zipfile.ZipFile(jar_file, 'w', zipfile.ZIP_DEFLATED) as jar:
        jar.write(index_file, json_name)
    sign_jar(jar_file)


def status_update_json(signed):
    """Output a JSON file with metadata about this run."""
    logging.debug(_('Outputting JSON'))
    output = common.setup_status_output(start_timestamp)
    if signed:
        output['signed'] = signed
    common.write_status_json(output)


def main():

    global config, options

    parser = ArgumentParser()
    common.setup_global_opts(parser)
    options = parser.parse_args()

    config = common.read_config(options)

    if 'jarsigner' not in config:
        raise FDroidException(
            _(
                'Java jarsigner not found! Install in standard location or set java_paths!'
            )
        )

    repodirs = ['repo']
    if config['archive_older'] != 0:
        repodirs.append('archive')

    signed = []
    for output_dir in repodirs:
        if not os.path.isdir(output_dir):
            raise FDroidException("Missing output directory '" + output_dir + "'")

        unsigned = os.path.join(output_dir, 'index_unsigned.jar')
        if os.path.exists(unsigned):
            sign_jar(unsigned)
            index_jar = os.path.join(output_dir, 'index.jar')
            os.rename(unsigned, index_jar)
            logging.info('Signed index in ' + output_dir)
            signed.append(index_jar)

        json_name = 'index-v1.json'
        index_file = os.path.join(output_dir, json_name)
        if os.path.exists(index_file):
            sign_index_v1(output_dir, json_name)
            logging.info('Signed ' + index_file)
            signed.append(index_file)

    if not signed:
        logging.info(_("Nothing to do"))
    status_update_json(signed)


if __name__ == "__main__":
    main()
