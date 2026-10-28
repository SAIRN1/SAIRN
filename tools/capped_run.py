#!/usr/bin/env python3
# OWNER: cc
"""Run a command under a HARD memory cap and a wall-clock cap, set up front.

    python tools/capped_run.py --mem-mb 1500 --timeout 900 -- bash replay.sh
    python tools/capped_run.py --fixtures

THE RULE (cc b60, methodology): any worktree replay of a past incident runs
through this, with the cap chosen BEFORE the run. The b59 replay of the 11:03
push ran uncapped, the machine ran low on memory, and the OS killed it in the
middle of the gate: the attempt was lost and nothing said how far it got. A
cap set up front turns that into a refusal inside the replay -- the replay's
own processes fail an allocation -- while the rest of the machine, and this
process, keep running and report what happened.

HOW. On Windows this process puts ITSELF in a Job Object with a job-wide
memory limit and KILL_ON_JOB_CLOSE, then starts the command, so the command
and every process it spawns are inside the job from their first instruction.
There is no window between start and assignment, and if this process dies the
job closes and takes every replay process with it rather than leaving orphans
writing into a worktree. Elsewhere it uses RLIMIT_AS on the child.

FAILS CLOSED. If the cap cannot be applied the command is NOT run, exit 2. A
replay that silently ran uncapped is exactly the run this exists to prevent.

Exit codes: the command's own exit code; 2 COULD NOT RUN (cap not applied,
bad usage); 4 the memory cap was reached (peak within 5% of it), whatever the
command returned; 5 the wall-clock cap was reached and the job was killed.
"""
import ctypes
import os
import subprocess
import sys
import time

EXIT_COULD_NOT_RUN, EXIT_MEM, EXIT_TIMEOUT = 2, 4, 5


class _Job(object):
    """A Windows Job Object holding this process and everything it spawns."""

    def __init__(self, limit_bytes):
        from ctypes import wintypes
        k = ctypes.WinDLL('kernel32', use_last_error=True)
        k.CreateJobObjectW.restype = wintypes.HANDLE
        k.GetCurrentProcess.restype = wintypes.HANDLE
        k.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                              ctypes.c_void_p, wintypes.DWORD]
        k.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                                ctypes.c_void_p, wintypes.DWORD,
                                                ctypes.c_void_p]
        k.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        k.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]

        class IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_ulonglong) for n in
                        ('r', 'w', 'o', 'rb', 'wb', 'ob')]

        class Basic(ctypes.Structure):
            _fields_ = [('PerProcessUserTimeLimit', ctypes.c_int64),
                        ('PerJobUserTimeLimit', ctypes.c_int64),
                        ('LimitFlags', wintypes.DWORD),
                        ('MinimumWorkingSetSize', ctypes.c_size_t),
                        ('MaximumWorkingSetSize', ctypes.c_size_t),
                        ('ActiveProcessLimit', wintypes.DWORD),
                        ('Affinity', ctypes.c_size_t),
                        ('PriorityClass', wintypes.DWORD),
                        ('SchedulingClass', wintypes.DWORD)]

        class Ext(ctypes.Structure):
            _fields_ = [('Basic', Basic), ('IoInfo', IO),
                        ('ProcessMemoryLimit', ctypes.c_size_t),
                        ('JobMemoryLimit', ctypes.c_size_t),
                        ('PeakProcessMemoryUsed', ctypes.c_size_t),
                        ('PeakJobMemoryUsed', ctypes.c_size_t)]

        self.k, self.Ext = k, Ext
        self.h = k.CreateJobObjectW(None, None)
        if not self.h:
            raise OSError('CreateJobObject failed, error %d' % ctypes.get_last_error())
        info = Ext()
        info.Basic.LimitFlags = 0x200 | 0x2000     # JOB_MEMORY | KILL_ON_JOB_CLOSE
        info.JobMemoryLimit = limit_bytes
        if not k.SetInformationJobObject(self.h, 9, ctypes.byref(info), ctypes.sizeof(info)):
            raise OSError('SetInformationJobObject failed, error %d' % ctypes.get_last_error())
        if not k.AssignProcessToJobObject(self.h, k.GetCurrentProcess()):
            raise OSError('AssignProcessToJobObject failed, error %d' % ctypes.get_last_error())

    def peak(self):
        info = self.Ext()
        ok = self.k.QueryInformationJobObject(self.h, 9, ctypes.byref(info),
                                              ctypes.sizeof(info), None)
        return info.PeakJobMemoryUsed if ok else None

    def kill(self, code):
        # This process is in the job too, so this is its exit as well: the
        # exit code handed over here IS the exit code the caller sees.
        sys.stdout.flush()
        self.k.TerminateJobObject(self.h, code)


def run(cmd, mem_mb, timeout):
    limit = mem_mb * 1024 * 1024
    job, preexec = None, None
    try:
        if os.name == 'nt':
            job = _Job(limit)
        else:
            import resource

            def preexec():
                resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    except Exception as e:
        print('COULD NOT RUN: the memory cap could not be applied (%s). The command '
              'was NOT run -- an uncapped replay is the thing this refuses.' % e)
        return EXIT_COULD_NOT_RUN
    print('CAPPED: %d MB job-wide, %ss wall clock -- %s' % (mem_mb, timeout, cmd))
    t0 = time.time()
    p = subprocess.Popen(cmd, preexec_fn=preexec)
    try:
        rc = p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        print('WALL-CLOCK CAP REACHED after %ss: the job was killed. The replay did '
              'NOT complete; what it did before the cap is all there is.' % timeout)
        if job:
            job.kill(EXIT_TIMEOUT)
        p.kill()
        return EXIT_TIMEOUT
    peak = job.peak() if job else None
    print('EXITED rc=%s after %.1fs, peak job memory %s' % (
        rc, time.time() - t0, '%.0f MB' % (peak / 1048576.0) if peak else 'not measured'))
    if peak and peak >= limit * 0.95:
        print('MEMORY CAP REACHED (peak %.0f of %d MB): allocations inside the replay '
              'were refused, so its result is not a clean result.' % (peak / 1048576.0, mem_mb))
        return EXIT_MEM
    return rc


def fixtures():
    """Both directions, each arm in its own capped_run process -- a run puts
    ITSELF in the job, so the driver must not."""
    me = [sys.executable, os.path.abspath(__file__)]
    # Grown in 10 MB steps, the way a replay actually grows. ONE allocation
    # bigger than the headroom fails without moving the peak, so the peak test
    # cannot see it; the command's own non-zero exit is the signal then.
    alloc = 'b = [bytearray(10 * 1024 * 1024) for _ in range(%d // 10)]; print(len(b))'
    arms = [
        ('a 20 MB child under a 512 MB cap runs and exits 0',
         me + ['--mem-mb', '512', '--timeout', '60', '--', sys.executable, '-c', alloc % 20], 0),
        ('a 700 MB child under a 256 MB cap is REFUSED, exit %d' % EXIT_MEM,
         me + ['--mem-mb', '256', '--timeout', '60', '--', sys.executable, '-c', alloc % 700],
         EXIT_MEM),
        ('a child that outlives a 3 s wall-clock cap is killed, exit %d' % EXIT_TIMEOUT,
         me + ['--mem-mb', '512', '--timeout', '3', '--', sys.executable, '-c',
               'import time; time.sleep(60)'], EXIT_TIMEOUT),
        ('a child exit code passes through unchanged',
         me + ['--mem-mb', '512', '--timeout', '60', '--', sys.executable, '-c',
               'import sys; sys.exit(7)'], 7),
        ('no command is a usage refusal, exit %d' % EXIT_COULD_NOT_RUN,
         me + ['--mem-mb', '512'], EXIT_COULD_NOT_RUN),
    ]
    bad = 0
    for label, argv, want in arms:
        t0 = time.time()
        rc = subprocess.run(argv, capture_output=True, text=True, timeout=120).returncode
        ok = rc == want
        bad += not ok
        print('  %-4s %s%s' % ('ok' if ok else 'FAIL', label,
                               '' if ok else ' -- got %s' % rc))
    print('CAPPED RUN -- %d/%d fixtures' % (len(arms) - bad, len(arms)))
    return EXIT_COULD_NOT_RUN if bad else 0


def main(argv):
    if '--fixtures' in argv:
        return fixtures()
    if '--' not in argv or not argv[argv.index('--') + 1:]:
        print('usage: python tools/capped_run.py --mem-mb N --timeout S -- <command...>')
        return EXIT_COULD_NOT_RUN
    head, cmd = argv[:argv.index('--')], argv[argv.index('--') + 1:]
    try:
        mem = int(head[head.index('--mem-mb') + 1])
        to = int(head[head.index('--timeout') + 1]) if '--timeout' in head else 1800
    except (ValueError, IndexError):
        print('COULD NOT RUN: --mem-mb N is required, set up front -- there is no '
              'default, because a default cap is one nobody chose.')
        return EXIT_COULD_NOT_RUN
    return run(cmd, mem, to)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
