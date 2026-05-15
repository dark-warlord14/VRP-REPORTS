#  V8 perf profiling follows symlinks and overwrites arbitrary files (perf-<pid>.map/jit-<pid>.dump) using 0666 open without O_NOFOLLOW

| Field | Value |
|-------|-------|
| **Issue ID** | [474951825](https://issues.chromium.org/issues/474951825) |
| **Status** | Verified |
| **Severity** | S3-Low |
| **Priority** | P3 |
| **Component** | Blink>JavaScript |
| **Platforms** | Android, Fuchsia, Linux, Mac, Windows, ChromeOS |
| **Reporter** | na...@gmail.com |
| **Assignee** | cl...@chromium.org |
| **Created** | 2026-01-11 |
| **Bounty** | Confirmed (amount unknown) |

## Description

---

### Report description

V8 perf profiling follows symlinks and overwrites arbitrary files (perf-<pid>.map/jit-<pid>.dump) using 0666 open without O\_NOFOLLOW

---

### Bug location

#### Where do you want to report your vulnerability?

Chrome VRP – Report security issues affecting the Chrome browser. [See program rules](https://bughunters.google.com/about/rules/5745167867576320/chrome-vulnerability-reward-program-rules)

#### Which URL (or repository) have you found the vulnerability in?

<https://chromium.googlesource.com/chromium/src>

---

### The problem

#### Please describe the technical details of the vulnerability

- Vulnerability: Perf profiling opens its outputs with open(..., O\_CREAT | O\_TRUNC | O\_RDWR, 0666) and follows symlinks,
  enabling arbitrary file overwrite on normal code paths.
  - v8/src/logging/log.cc:410-424 (--perf-basic-prof): writes perf-<pid>.map to perf\_basic\_prof\_path (default /tmp).
    No O\_NOFOLLOW/O\_EXCL; mode 0666.
  - v8/src/diagnostics/perf-jit.cc:136-154 (--perf-prof): writes jit-<pid>.dump to perf\_prof\_path (default .). Same
    flags and permissions.
- Impact: If perf profiling is enabled, a pre-planted symlink at the expected path lets an attacker overwrite arbitrary
  files with the V8/Chrome process’s privileges (O\_CREAT|O\_TRUNC 0666). In multi-user environments, another local user
  can precreate /tmp/perf-<victim-pid>.map pointing to a sensitive file and wait for the victim to run d8/Chrome with
  perf profiling; the target gets clobbered with profiling data.
- Normal-path trigger (no exploit-specific flags beyond documented profiling):
  1. Attacker predicts/observes the next PID and creates a symlink, e.g., ln -s /tmp/target.txt /tmp/perf-<pid>.map
     (or ln -s /tmp/target.dump <perf\_prof\_path>/jit-<pid>.dump).
  2. Victim runs d8 --perf-basic-prof (or Chrome with --perf-basic-prof/--perf-prof).
  3. Profiling startup follows the symlink and truncates/overwrites the target with profiling output.
- Verified locally: Created /tmp/perf-<pid>.map symlink to /tmp/v8\_overwrite.txt, ran out/v8\_x64.release/d8 --perf-
  basic-prof -e "0", and /tmp/v8\_overwrite.txt was created/filled with perf map data.
- Minimal PoC (non-destructive example):

LAST=$(cat /proc/sys/kernel/ns\_last\_pid); D8\_PID=$((LAST+2))
ln -sf /tmp/overwrite.txt /tmp/perf-${D8\_PID}.map
/home/finder/chromium/src/out/v8\_x64.release/d8 --perf-basic-prof -e "0"

#### Impact analysis

Impact: Turning on perf profiling is enough to overwrite arbitrary files with V8/Chrome process privileges. The profiler
writes to /tmp or the current dir without O\_NOFOLLOW, so a pre-planted symlink lets an attacker clobber sensitive/
config/script files with O\_CREAT|O\_TRUNC 0666 data. If profiling runs under privileged accounts (e.g., buildbots/admin),
system files can be overwritten, causing denial of service or setting up further privilege escalation

---

### The cause

#### What version of Chrome have you found the security issue in?

Chromium src checkout at commit e1db071eae4d295bf27e8d37d38390c4554e6e6

#### Is the security issue related to a crash?

No, it is not related to a crash.

#### Choose the type of vulnerability

Other

#### How would you like to be publicly acknowledged for your report?

jaeyeong

## Timeline

### ct...@chromium.org (2026-01-12)

Thanks for your report.

As this requires a local attacker under specific circumstances, I think this is borderline Sev-Low at best. It seems like this is maybe more of a concern for downstream NodeJS users which is a very different threat model environment?

Passing to clemensb@ as my best guess at an initial owner for this (based on <https://chromium-review.googlesource.com/c/v8/v8/+/1993969>, sorry for basing this on a 5 year old CL...)

### cl...@chromium.org (2026-01-13)

Yeah, this is not a valid attack vector. Not sure if we should keep it as vulnerability, but P4 S3 already looks good. I'll also set impact None.

Sure, we can pass `O_NOFOLLOW` and `O_NOEXCL` on the `open` call. I'll do that when I have time.

### ch...@google.com (2026-01-13)

This V8 bug has been marked as either a release blocker or a vulnerability bug. V8 bugs affect all OSs supported by Chrome, so the OS field has been updated to reflect this. Please update the bug with the correct OS field if it only affects a subset of OSes.

### dx...@google.com (2026-01-19)

Project: v8/v8  

Branch:  main  

Author:  Clemens Backes [clemensb@chromium.org](mailto:clemensb@chromium.org)  

Link:    <https://chromium-review.googlesource.com/7461065>

[perf-jit] Do not follow symlinks when opening perf-jit file

---


Expand for full commit details
```
     
    This is absolutely not critical, but was externally reported, so let's 
    just add the O_NOFOLLOW flag, which makes sense in any case. 
     
    This requires splitting the `fopen` call into `open` and `fdopen`. 
     
    Also check for failure to open the file and report that instead of 
    silently returning. 
     
    Drive-by: Inline `PerfJitLogger::OpenMarkerFile` and 
    `PerfJitLogger::CloseMarkerFile`; the latter was never called. 
     
    R=cbruni@chromium.org 
     
    Fixed: 474951825 
    Change-Id: Ifab9a5bfe4b721a84dcfd8770a1a5c0b11177488 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7461065 
    Reviewed-by: Camillo Bruni <cbruni@chromium.org> 
    Commit-Queue: Clemens Backes <clemensb@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#104772}

```

---

Files:

- M `src/base/platform/platform-posix.cc`
- M `src/diagnostics/perf-jit.cc`
- M `src/diagnostics/perf-jit.h`

---

Hash: [29bc47b9003d8c6f67bff65028fe783983de815b](https://chromiumdash.appspot.com/commit/29bc47b9003d8c6f67bff65028fe783983de815b)  

Date: Tue Jan 13 17:17:33 2026


---

### dx...@google.com (2026-01-20)

Project: v8/v8  

Branch:  main  

Author:  Clemens Backes [clemensb@chromium.org](mailto:clemensb@chromium.org)  

Link:    <https://chromium-review.googlesource.com/7493916>

Revert "[perf-jit] Do not follow symlinks when opening perf-jit file"

---


Expand for full commit details
```
     
    This reverts commit 29bc47b9003d8c6f67bff65028fe783983de815b. 
     
    Reason for revert: Too restrictive. 
     
    Original change's description: 
    > [perf-jit] Do not follow symlinks when opening perf-jit file 
    > 
    > This is absolutely not critical, but was externally reported, so let's 
    > just add the O_NOFOLLOW flag, which makes sense in any case. 
    > 
    > This requires splitting the `fopen` call into `open` and `fdopen`. 
    > 
    > Also check for failure to open the file and report that instead of 
    > silently returning. 
    > 
    > Drive-by: Inline `PerfJitLogger::OpenMarkerFile` and 
    > `PerfJitLogger::CloseMarkerFile`; the latter was never called. 
    > 
    > R=cbruni@chromium.org 
    > 
    > Fixed: 474951825 
    > Change-Id: Ifab9a5bfe4b721a84dcfd8770a1a5c0b11177488 
    > Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7461065 
    > Reviewed-by: Camillo Bruni <cbruni@chromium.org> 
    > Commit-Queue: Clemens Backes <clemensb@chromium.org> 
    > Cr-Commit-Position: refs/heads/main@{#104772} 
     
    Bug: 474951825 
    No-Presubmit: true 
    No-Tree-Checks: true 
    No-Try: true 
    Change-Id: I669e986f6ff7131604fabe4c058ab51355c85b70 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7493916 
    Auto-Submit: Clemens Backes <clemensb@chromium.org> 
    Bot-Commit: Rubber Stamper <rubber-stamper@appspot.gserviceaccount.com> 
    Commit-Queue: Rubber Stamper <rubber-stamper@appspot.gserviceaccount.com> 
    Cr-Commit-Position: refs/heads/main@{#104777}

```

---

Files:

- M `src/base/platform/platform-posix.cc`
- M `src/diagnostics/perf-jit.cc`
- M `src/diagnostics/perf-jit.h`

---

Hash: [e7c657afbe4d0144683375cefef799362826f43d](https://chromiumdash.appspot.com/commit/e7c657afbe4d0144683375cefef799362826f43d)  

Date: Tue Jan 20 05:52:23 2026


---

### dx...@google.com (2026-01-26)

Project: v8/v8  

Branch:  main  

Author:  Clemens Backes [clemensb@chromium.org](mailto:clemensb@chromium.org)  

Link:    <https://chromium-review.googlesource.com/7502559>

[perf-jit] Do not follow symlinks

---


Expand for full commit details
```
     
    To not follow symlinks when opening perf-jit files, to avoid following 
    symlinks placed in the /tmp directory. 
     
    R=cbruni@chromium.org 
     
    Bug: 474951825 
    Change-Id: Ica49ac5be2885cfe94fd05695fabe620a18277a6 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7502559 
    Reviewed-by: Camillo Bruni <cbruni@chromium.org> 
    Commit-Queue: Clemens Backes <clemensb@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#104898}

```

---

Files:

- M `src/diagnostics/perf-jit.cc`

---

Hash: [f1be130639ce4360764281bcc9d46b0e1fc9c0d2](https://chromiumdash.appspot.com/commit/f1be130639ce4360764281bcc9d46b0e1fc9c0d2)  

Date: Wed Jan 21 13:34:48 2026


---

### dx...@google.com (2026-01-27)

Project: v8/v8  

Branch:  main  

Author:  Clemens Backes [clemensb@chromium.org](mailto:clemensb@chromium.org)  

Link:    <https://chromium-review.googlesource.com/7502557>

[perf-jit] Cleanup file opening

---


Expand for full commit details
```
     
    This is the cleanup part of the reverted https://crrev.com/c/7461065. 
     
    R=cbruni@chromium.org 
     
    Bug: 474951825 
    Change-Id: Ia9ee1153b81f98bc9d03ec59e518ac4d870eebba 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7502557 
    Commit-Queue: Clemens Backes <clemensb@chromium.org> 
    Reviewed-by: Camillo Bruni <cbruni@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#104922}

```

---

Files:

- M `src/diagnostics/perf-jit.cc`
- M `src/diagnostics/perf-jit.h`

---

Hash: [1961425700c7b93e980fba35e6728a08241b4b96](https://chromiumdash.appspot.com/commit/1961425700c7b93e980fba35e6728a08241b4b96)  

Date: Wed Jan 21 15:29:57 2026


---

### sp...@google.com (2026-02-20)

*NOTE: This is an automatically generated email*

Hello,

Chrome Vulnerability Rewards Program (VRP) Panel has decided that the security impact of this
issue does not meet the criteria to qualify for a reward.

Rationale for this decision:

Does not impact a shipping version of google chrome

Note that the fact that this issue is not being rewarded does not mean
that the product team won't fix the issue. We have filed a bug with the product
team and they will review your report and decide if a fix is required. We'll
let you know if the issue was fixed.

Regards,   

Google Security Bot

*How did we do? Please fill out a [short anonymous survey](https://goo.gl/IR3KRH).*

### ch...@google.com (2026-05-06)

This bug has been closed for more than 14 weeks. Removing issue access restrictions.

## Bounty Award

> Does not impact a shipping version of google chrome
> 
> 
> Note that the fact that this issue is not being rewarded does not mean
> that the product team won't fix the issue. We have filed a bug with the product
> team and they will review your report and decide if a fix is required. We'll
> let you know if the issue was fixed.
> 
> Regards, \
> Google Security Bot
> 
> *How did we do? Please fill out a [short anonymous survey](https://goo.gl/IR3KRH).*

---
*Data from [Chromium Issue Tracker](https://issues.chromium.org/issues/474951825)*
