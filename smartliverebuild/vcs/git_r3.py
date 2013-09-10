#	vim:fileencoding=utf-8
# (c) 2011 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from . import RemoteVCSSupport, NonLiveEbuild

class GitR3Support(RemoteVCSSupport):
	reqenv = ['EGIT_REPO_URI', 'EGIT_VERSION']
	optenv = ['EGIT_BRANCH', 'EGIT_COMMIT']

	def __init__(self, *args, **kwargs):
		RemoteVCSSupport.__init__(self, *args, **kwargs)
		if (self.env['EGIT_COMMIT']
				and self.env['EGIT_COMMIT'] != (self.env.get('EGIT_BRANCH') or HEAD)):
			raise NonLiveEbuild('EGIT_COMMIT set, package is not really a live one')
		self.repo_uris = self.env['EGIT_REPO_URI'].split()

	def __str__(self):
		return '%s [%s]' % (self.repo_uris[0],
				self.env.get('EGIT_BRANCH') or 'HEAD')

	def parseoutput(self, out):
		return out.split()[0]

	@property
	def savedrev(self):
		return self.env['EGIT_VERSION']

	@property
	def updatecmd(self):
		cmds = []
		for r in self.repo_uris:
			cmds.append('git ls-remote %s %s' % (
				r, self.env.get('EGIT_BRANCH') or 'HEAD'))
		return ' || '.join(cmds)