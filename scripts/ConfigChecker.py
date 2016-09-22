'''ConfigChecker.py checks if local/tracked config files are equivallent'''

import configparser

from plumbum import cli, local


class ConfigCheck(cli.Application):
    verbose = cli.Flag(
        ['v', 'verbose'],
        help='Verbose mode = lots of printing'
    )

    base_file = ''
    comp_file = ''

    @cli.switch(
        ['-b', '--base'],
        str,
        help='base file to compare against'
    )
    def load_basefile(self, filename):
        '''test and load base file for comparisons'''
        tmp_path = local.path(filename)
        if tmp_path.exists() and tmp_path.is_file():
            self.base_file = tmp_path
        else:
            raise IOError('--base=' + filename + ' not found')

    @cli.switch(
        ['-c', '--comp'],
        str,
        help='base file to compare against'
    )
    def load_compfile(self, filename):
        '''test and load comp file for comparisons'''
        tmp_path = local.path(filename)
        if tmp_path.exists() and tmp_path.is_file():
            self.comp_file = tmp_path
        else:
            raise IOError('--comp=' + filename + ' not found')

    def main(self):
        '''working part of the cli app'''
        if self.verbose: print('main')

        if not self.comp_file:
            if self.verbose: print('-- no compfile given, using <basefile>_local.cfg')
            compfile = str(self.base_file).replace('.cfg', '_local.cfg')
            self.load_compfile(compfile)

        if self.verbose:
            print('--base_file=' + self.base_file)
            print('--comp_file=' + self.comp_file)


if __name__ == '__main__':
    ConfigCheck.run()
