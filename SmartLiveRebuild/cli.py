#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 3-clause BSD license or the GPL-2 license.

import os
from optparse import OptionParser

import portage

from SmartLiveRebuild import PV
from SmartLiveRebuild.core import Config, SmartLiveRebuild, SLRFailure
from SmartLiveRebuild.output import out

def parse_options(argv):
	opt = OptionParser(
			usage='%prog [options] -- [emerge options]',
			version='%%prog %s' % PV,
			description='Enumerate all live packages in system, check their repositories for updates and remerge the updated ones.'
	)
	opt.add_option('-c', '--config-file', action='store', dest='config_file',
		help='Configuration file (default: /etc/portage/smart-live-rebuild.conf)')
	opt.add_option('-C', '--no-color', action='store_false', dest='color',
		help='Disable colorful output.')
	opt.add_option('-E', '--no-erraneous-merge', action='store_false', dest='erraneous_merge',
		help='Disable emerging packages for which the update has failed.')
	opt.add_option('-j', '--jobs', action='store', type='int', dest='jobs',
		help='Spawn JOBS parallel processes to perform repository updates.')
	opt.add_option('-l', '--local-rev', action='store_true', dest='local_rev',
		help='Force determining the current package revision from the repository instead of using the one saved by portage.')
	opt.add_option('-N', '--no-network', action='store_false', dest='network',
		help='Disable network interaction and just aggregate already updated repositories (requires --local-rev not set).')
	opt.add_option('-O', '--no-offline', action='store_false', dest='offline',
		help='Disable setting ESCM_OFFLINE for emerge.')
	opt.add_option('-p', '--pretend', action='store_true', dest='pretend',
		help='Only print a list of the packages which were updated; do not call emerge to rebuild them.')
	opt.add_option('-P', '--profile', action='store', dest='profile',
		help='Configuration profile (config file section) to use (default: smart-live-rebuild)')
	opt.add_option('-Q', '--quickpkg', action='store_true', dest='quickpkg',
		help='Call quickpkg to create binary backups of packages which are going to be updated.')
	opt.add_option('-S', '--no-setuid', action='store_false', dest='setuid',
		help='Do not switch UID to portage when FEATURES=userpriv is set.')
	opt.add_option('-t', '--type', action='append', dest='type',
		help='Limit rebuild to packages using specific VCS (eclass name). If used multiple times, all specified VCS-es will be used.')
	opt.add_option('-U', '--unprivileged-user', action='store_true', dest='unprivileged_user',
		help='Allow running as an unprivileged user.')

	return opt.parse_args(argv[1:])

def main(argv):
	# initialize config with defaults
	c = Config()

	# parse opts to get the config file
	(opts, args) = parse_options(argv)
	c.apply_optparse(opts)

	# do the config file parsing
	c.parse_configfiles()

	# and now reapply the options to override config file defaults
	c.apply_optparse(opts)
	opts = c.get_options()

	if not opts.pretend:
		try:
			import psutil

			def getproc(pid):
				for ps in psutil.get_process_list():
					if pid == ps.pid:
						return ps
				raise Exception()

			def getscriptname(ps):
				if os.path.basename(ps.cmdline[0]) != ps.name:
					return ps.cmdline[0]
				cmdline = ps.cmdline[1:]
				while cmdline[0].startswith('-'): # omit options
					cmdline.pop(0)
				return os.path.basename(cmdline[0])

			ps = getproc(os.getppid())
			# traverse upstream to find the emerge process
			while ps.pid > 1:
				if getscriptname(ps) == 'emerge':
					out.s1('Running under the emerge process, assuming --pretend.')
					opts.pretend = True
					break
				ps = ps.parent
		except Exception:
			pass

	if opts.setuid:
		puid = portage.data.portage_uid
		pgid = portage.data.portage_gid
		if puid and pgid and os.geteuid() != 0 and os.getuid() == puid:
			if not opts.pretend:
				out.s1('Running as the portage user, assuming --pretend.')
				opts.pretend = True
			if opts.quickpkg:
				out.err("Running as the portage user, --quickpkg probably won't work")

	try:
		packages = SmartLiveRebuild(opts, saveuid = not opts.pretend)
	except SLRFailure:
		return 1

	if opts.pretend:
		for p in packages:
			print('>=%s' % p)
		return 0
	else:
		cmd = ['emerge', '--oneshot']
		cmd.extend(args)
		cmd.extend(['>=%s' % x for x in packages])
		out.s2(' '.join(cmd))
		os.execv('/usr/bin/emerge', cmd)
		return 126