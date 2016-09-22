'''ConfigChecker.py checks if local/tracked config files are equivallent'''

import configparser
from configparser import ExtendedInterpolation

from plumbum import cli, local


class ConfigCheck(cli.Application):
    verbose = cli.Flag(
        ['v', 'verbose'],
        help='Verbose mode = lots of printing'
    )

    base_file = ''
    base_config = configparser.ConfigParser(
        interpolation=ExtendedInterpolation(),
        allow_no_value=True,
        delimiters=('='),
        inline_comment_prefixes=('#')
    )
    comp_file = ''
    comp_config = configparser.ConfigParser(
        interpolation=ExtendedInterpolation(),
        allow_no_value=True,
        delimiters=('='),
        inline_comment_prefixes=('#')
    )

    @cli.switch(
        ['-b', '--base'],
        str,
        help='base file to compare against'
    )
    def load_basefile(self, filename):
        '''test and load base file for comparisons'''
        tmp_path = local.path(filename)
        if tmp_path.exists() and tmp_path.is_file():
            try:
                with open(tmp_path,'r') as config_handle:
                    self.base_config.read_file(config_handle)
            except Exception as error_msg:
                raise error_msg
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
            try:
                with open(tmp_path,'r') as config_handle:
                    self.comp_config.read_file(config_handle)
            except Exception as error_msg:
                raise error_msg
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

        section_list = []
        for section in self.base_config:
            section_list.append(section)
            try:
                self.comp_config[section]
            except KeyError:
                print('SECTION MISSING IN COMP: ' + section)
                continue

            for value in self.base_config[section]:
                base_entry = self.base_config.get(section, value)
                try:
                    comp_entry=self.comp_config.get(section, value)
                except KeyError:
                    print('--KEY MISSING IN COMP: ' + value)
                    continue

                if base_entry:  #if key isn't blank, compare values
                    if base_entry != comp_entry:
                        print('--WARNING: base/comp entries different for {section}.{value}'.\
                            format(
                                section=section,
                                value=value
                            ))
                        print('\tbase=' + base_entry)
                        print('\tcomp=' + comp_entry)
                    elif self.verbose:
                        print('{section}.{value}==={entry}'.\
                            format(
                                section=section,
                                value=value,
                                entry=base_entry
                            ))
            for value in self.comp_config[section]:
                comp_entry = self.comp_config.get(section, value)
                try:
                    base_entry = self.base_config.get(section, value)
                except KeyError:
                    print('--KEY MISSING IN BASE: ' + value)
                    continue

                #TODO: compare comp value differences?

        for section in self.comp_config:
            if section in section_list:
                continue

            try:
                self.base_config[section]
            except KeyError:
                print('SECTION MISSING IN BASE: ' + section)
                continue

if __name__ == '__main__':
    ConfigCheck.run()
