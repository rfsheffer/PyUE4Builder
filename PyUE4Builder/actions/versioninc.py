

# def do_game_version_increment(uproject_dir_path):
#     """
#     Increments the game version number
#     Note: This function assumes you are current pushed into the directory jenkins.py resides
#     """
#     abs_ini_path = os.path.join(uproject_dir_path, game_version_ini)
#     if not os.path.isfile(abs_ini_path):
#         error_exit('COULD NOT INCREMENT BUILD VERSION ERROR! FILE NOT FOUND!')
#
#     # Get the current perforce ticket so we can call p4 commands on the workspace
#     if 'P4TICKET' in os.environ:
#         # If the ticket is set in the environment already, use that
#         p4_ticket = os.environ['P4TICKET']
#     else:
#         # Try to do a general login on a client machine
#         p4_ticket = get_p4_ticket()
#
#     # Edit the ini file, we will increment the version number
#     click.secho('INI found at {}'.format(abs_ini_path))
#     launch('p4 -P {0} edit {1}'.format(p4_ticket, abs_ini_path), False)
#
#     fp = open(abs_ini_path, 'r')
#     ini_lines = fp.readlines()
#     fp.close()
#     proj_ver_str = 'ProjectVersion='
#     for ini_line_index in range(0, len(ini_lines)):
#         if ini_lines[ini_line_index].startswith(proj_ver_str):
#             edit_line = ini_lines[ini_line_index].split(proj_ver_str)[1]
#             ver_nums = edit_line.split('.')
#             ver_nums[len(ver_nums) - 1] = str(int(ver_nums[len(ver_nums) - 1]) + 1)
#             ini_lines[ini_line_index] = '{0}{1}\n'.format(proj_ver_str, str.join('.', ver_nums))
#
#     fp = open(abs_ini_path, 'w')
#     fp.writelines(ini_lines)
#     fp.close()
#
#     # Submit the version increment edit back to version control
#     # UNDONE: This is great for build automation on a dedicated build server, but on local client
#     # I am letting the client user submit this themselves.
#     # launch('p4 -P {0} submit -d "[proj_name][auto] Automatic version increment"'.format(p4_ticket), False)
