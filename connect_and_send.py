#!/usr/bin/env python

'''
Purpose:    Connect to a list of cisco devices, run the commands contained
            in one file (commands), and display the output of other commands
            in another file (show_commands).

Author:
            ___  ____ _ ____ _  _    _  _ _    ____ ___ ___
            |__] |__/ | |__| |\ |    |_/  |    |  |  |    /
            |__] |  \ | |  | | \|    | \_ |___ |__|  |   /__
            Brian.Klotz@nike.com

Version:    0.3
Date:       April 2017
'''
import argparse
import netmiko
import getpass
import logging
import os

# Set up argument parser and help info
parser = argparse.ArgumentParser(description='Connect to list of devices and \
                                 run a set of commands on each')
always_required = parser.add_argument_group('always required')
always_required.add_argument("devices", nargs=1, help="Name of file containing devices",
                    metavar='<devices_file>')
one_or_both = parser.add_argument_group('one (or both) of these')
one_or_both.add_argument("-c", "--configs", nargs=1, help="Name of file containing commands to \
                    run", metavar='<configure_commands_file>')
one_or_both.add_argument("-s", "--show-commands",nargs=1, help="Name of file containing show commands \
                    (for verification)", metavar='<show_commands_file>')
args = parser.parse_args()

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('output.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(message)s\n')
handler.setFormatter(formatter)
logger.addHandler(handler)

def open_file(file):
    with open(file) as f:
        content = f.read().strip().splitlines()
        return content

def get_creds(): # Prompt for credentials
    username = getpass.getuser()
    password = getpass.getpass()
    return username, password

def main():
    device_file = args.devices[0]
    devices = open_file(device_file)

    if args.configs:
        command_list = args.configs[0]

    if args.show_commands:
        show_cmds_file = args.show_commands[0]
        show_cmds = open_file(show_cmds_file)

    if not (args.configs or args.show_commands):
        parser.print_help()
        parser.exit(status=1)

    username, password = get_creds()

    netmiko_exceptions = (netmiko.ssh_exception.NetMikoTimeoutException,
                          netmiko.ssh_exception.NetMikoAuthenticationException)

    for a_device in devices:
        a_device = {'host' : a_device ,
                    'device_type' : 'cisco_ios' ,
                    'username' : username ,
                    'password' : password ,
                    'secret' : password
                    }

        print('-'*79)
        print('Connecting to ' + a_device['host'] + '...')
        try:
            connection = netmiko.ConnectHandler(**a_device)
            if args.configs:
                connection.enable()
                print('Sending commands...')
                connection.send_config_from_file(command_list)
                path_to_command_list = os.path.abspath(command_list)
                logger.info('Sending commands from %s', path_to_command_list)
            if args.show_commands:
                connection.enable()
                for a_command in show_cmds:
                    banner = ('\n>>>>>>>>>>> ' + a_command.upper() + ' <<<<<<<<<<<<\n')
                    show_result = (connection.send_command(a_command))
                    print(banner + show_result)
                    logger.info('%s %s %s', a_device['host'], banner, show_result )
                if args.configs:
                    good_to_go = raw_input('\nCheck the output, ' +
                                            'OK to save? (y/n): ').lower()
                    if good_to_go == 'y':
                        connection.send_command('write mem')
                        print('Configuration saved')
                    else:
                        print('Configuration was NOT saved, ' + \
                              'back out changes manually (or reload)')
            else:
                connection.send_command('write mem')
                print('Commands sent and saved to startup-config on ' + a_device['host'])

            connection.disconnect()

        except netmiko_exceptions as e:
            print('Failed to connect: %s' % e)
            logger.error('Failed to connect %s', e)

main()
