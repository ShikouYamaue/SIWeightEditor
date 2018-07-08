# -*- coding: utf-8 -*-
#関数計測
import functools
try:
	import cProfile as profile
	import pstats
except: pass

def profileFunction(sortKey="time", rows=30):
	def _(f):
		@functools.wraps(_)
		def __(*fargs, **fkwargs):
			prof = profile.Profile()
			ret = prof.runcall(f, *fargs, **fkwargs)
			pstats.Stats(prof).strip_dirs().sort_stats(sortKey).print_stats(rows)

			return ret

		return __
	return _