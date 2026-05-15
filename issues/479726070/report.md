# Hole leak in MaglevGraphBuilder

| Field | Value |
|-------|-------|
| **Issue ID** | [479726070](https://issues.chromium.org/issues/479726070) |
| **Status** | Assigned |
| **Severity** | S4-Minimal |
| **Priority** | P1 |
| **Component** | Blink>JavaScript>Compiler>Maglev |
| **Platforms** | Android, Fuchsia, Linux, Mac, Windows, ChromeOS |
| **Reporter** | ha...@gmail.com |
| **Assignee** | vi...@chromium.org |
| **Created** | 2026-01-29 |
| **Bounty** | $10,000.00 |

## Description

### VULNERABILITY DETAILS

#### Summary

[MaglevGraphBuilder::VisitThrowReferenceErrorIfHole](https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-graph-builder.cc;l=16443) incorrectly eliminates TDZ checks for module variables because [CanBeTheHoleValue](https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-ir.h;l=734) does not include `LoadTaggedField` in its whitelist. This causes `the_hole_value` (HOLE\_TYPE) to leak into JS when accessing uninitialized module bindings, leading to type confusion. This issue is similar to [crbug.com/450618029](https://crbug.com/450618029)

#### Suggested Fix

Add `Opcode::kLoadTaggedField` to the [CanBeTheHoleValue()](https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-ir.h;l=734) whitelist, or special-case `Cell::kValueOffset` reads to return `Tribool::kMaybe` to prevent hole check elimination for module variable accesses.

Attached `fix.diff` which adds `kLoadTaggedField` to the `CanBeTheHoleValue()` whitelist:

```
diff --git a/src/maglev/maglev-ir.h b/src/maglev/maglev-ir.h
--- a/src/maglev/maglev-ir.h
+++ b/src/maglev/maglev-ir.h
@@ -734,6 +734,9 @@ constexpr bool CanBeTheHoleValue(Opcode opcode) {
   switch (opcode) {
     case Opcode::kInitialValue:
     case Opcode::kCallRuntime:
+    case Opcode::kLoadTaggedField:
     // TODO(victorgomes): Should we have a list of builtins that could
     // return the hole?
     case Opcode::kCallBuiltin:

```
#### Details

When accessing module variables, Ignition generates the following bytecode sequence:

- `LdaModuleVariable`
- `ThrowReferenceErrorIfHole "<name>"`
- `Return`

The `ThrowReferenceErrorIfHole` bytecode is critical for TDZ enforcement and must be preserved to prevent `the_hole_value` from leaking.

In [MaglevGraphBuilder::VisitLdaModuleVariable](https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-graph-builder.cc;l=7564), module variable accesses are compiled to read from a `Cell` via `LoadTaggedField(Cell::kValueOffset)`. The issue is that [ValueNode::IsTheHole](https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-ir.cc;l=667) returns `kFalse` for `LoadTaggedField` nodes because [CanBeTheHoleValue](https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-ir.h;l=734) does not include `Opcode::kLoadTaggedField` in its whitelist:

```
constexpr bool CanBeTheHoleValue(Opcode opcode) {
  switch (opcode) {
    case Opcode::kInitialValue:
    case Opcode::kCallRuntime:
    // TODO(victorgomes): Should we have a list of builtins that could
    // return the hole?
    case Opcode::kCallBuiltin:
    case Opcode::kGeneratorRestoreRegister:
    case Opcode::kRootConstant:
    case Opcode::kLoadContextSlot:
    case Opcode::kLoadContextSlotNoCells:
    case Opcode::kLoadFixedArrayElement:
    case Opcode::kPhi:
      return true;
    default:
      return false;
  }
}

```

As a result, when [MaglevGraphBuilder::VisitThrowReferenceErrorIfHole](https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-graph-builder.cc;l=16443) checks `IsTheHole()` and gets `kFalse`, it skips inserting the hole check entirely. Additionally, [MaglevGraphOptimizer::VisitThrowReferenceErrorIfHole](https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-graph-optimizer.cc;l=939) removes any existing `ThrowReferenceErrorIfHole` nodes when `IsTheHole() == kFalse`.

```
ReduceResult MaglevGraphBuilder::VisitThrowReferenceErrorIfHole() {
  // ThrowReferenceErrorIfHole <variable_name>
  compiler::NameRef name = GetRefOperand<Name>(0);
  ValueNode* value = GetAccumulator();
  switch (value->IsTheHole()) {
    case Tribool::kTrue:
      return BuildThrow(Throw::kThrowAccessedUninitializedVariable,
                        GetConstant(name));
    case Tribool::kFalse:
      return ReduceResult::Done();
    case Tribool::kMaybe:
      DCHECK(value->is_tagged());
      return AddNewNode<ThrowReferenceErrorIfHole>({value}, name);
  }
}

```

This causes `the_hole_value` to leak into JavaScript, which then triggers crashes when the value is used (e.g., in `Map.delete()` or `JSON.stringify()`).

### VERSION

V8 commit: 5853269075baaf304cd5be09d941a6c3e9671847

V8 Version: 14.6.101

#### REPRODUCTION CASE

Build args on commit 5853269075baaf304cd5be09d941a6c3e9671847:

```
is_component_build = false
is_debug = false
v8_enable_backtrace = true
dcheck_always_on = true
is_asan=true
v8_static_library=true

```

Run `./d8 --module --allow-natives-syntax poc.js`, you would observe the DCHECK failure as the `stack.txt` shows.

## Attachments

- [stack.txt](attachments/stack.txt) (text/plain, 3.9 KB)
- [poc.js](attachments/poc.js) (text/javascript, 158 B)
- [fix.diff](attachments/fix.diff) (text/x-diff, 379 B)
- [confusion_poc_a.js](attachments/confusion_poc_a.js) (text/javascript, 72 B)
- [confusion_poc_b.js](attachments/confusion_poc_b.js) (text/javascript, 361 B)
- [confusion_stack.txt](attachments/confusion_stack.txt) (text/plain, 4.1 KB)

## Timeline

### ha...@gmail.com (2026-01-29)

We can further trigger the type confusion via passing the hole to a string operation so the runtime dereferences it as a String. Run the d8 with:

```
./d8 --module --allow-natives-syntax ./confusion_poc_a.js

```
> The poc would import child module for getting the hole in confusion\_poc\_b.js

You would get the type confusion crash shown in `confusion_stack.txt`

### ha...@gmail.com (2026-01-29)

Running the above POC on Linux d8 in commit d39a989e59a4e8c81f2720e242d08163a763181d without DCHECK enabled

```
is_component_build = false
is_debug = false
v8_enable_backtrace = true
dcheck_always_on = false
is_asan=true
v8_static_library=true

```

This will trigger the following crash:

```
Received signal 11 SEGV_ACCERR 79cd00030004

==== C stack trace ===============================

/source/v8/src/out/asan_d8_nocheck/d8(__interceptor_backtrace+0x46)[0x55d71a3c0b36]
/source/v8/src/out/asan_d8_nocheck/d8(_ZN2v84base5debug10StackTraceC1Ev+0x3a)[0x55d71ac4679a]
/source/v8/src/out/asan_d8_nocheck/d8(+0x2df0569)[0x55d71ac46569]
/lib/x86_64-linux-gnu/libpthread.so.0(+0x14420)[0x7f0eae2e0420]
/source/v8/src/out/asan_d8_nocheck/d8(_ZN2v88internal24Runtime_StringCharCodeAtEiPmPNS0_7IsolateE+0x32f)[0x55d71c6ba96f]
/source/v8/src/out/asan_d8_nocheck/d8(+0x88fd331)[0x55d720753331]
[end of stack trace]

```

### el...@chromium.org (2026-01-29)

Thanks for the report! I can confirm this is legit; sending to clusterfuzz and v8 for triage.

Reproed at d8 a672d08d37424a230afa8dcd1e3e0b3cd7dfec4d with your build args:

```
$ d8 --module --allow-natives-syntax poc.js


#
# Fatal error in ../../src/objects/objects-inl.h, line 2031
# Debug check failed: instance_type != HOLE_TYPE (HOLE_TYPE (274) vs. HOLE_TYPE (274)).
#
#
#
#FailureMessage Object: 0x7b00ef118860
==== C stack trace ===============================

    /usr/local/google/home/ellyjones/p/v8/v8/out/rel/d8(___interceptor_backtrace+0x46) [0x55d2d32aeb36]
    /usr/local/google/home/ellyjones/p/v8/v8/out/rel/d8(v8::base::debug::StackTrace::StackTrace()+0x34) [0x55d2d371bab4]
    /usr/local/google/home/ellyjones/p/v8/v8/out/rel/d8(+0x434b7db) [0x55d2d37197db]
    /usr/local/google/home/ellyjones/p/v8/v8/out/rel/d8(V8_Fatal(char const*, int, char const*, ...)+0x2a0) [0x55d2d3708520]
    /usr/local/google/home/ellyjones/p/v8/v8/out/rel/d8(+0x433941f) [0x55d2d370741f]
    /usr/local/google/home/ellyjones/p/v8/v8/out/rel/d8(v8::internal::Object::GetSimpleHash(v8::internal::Tagged<v8::internal::Object>)+0xa42) [0x55d2d385f192]
    /usr/local/google/home/ellyjones/p/v8/v8/out/rel/d8(v8::internal::Object::GetHash(v8::internal::Tagged<v8::internal::Object>)+0xbf) [0x55d2d37a984f]
    /usr/local/google/home/ellyjones/p/v8/v8/out/rel/d8(v8::internal::OrderedHashMap::GetHash(v8::internal::Isolate*, unsigned long)+0xae) [0x55d2d521c57e]
    /usr/local/google/home/ellyjones/p/v8/v8/out/rel/d8(+0xb51844d) [0x55d2da8e644d]
Trace/BPT trap

```

### cl...@appspot.gserviceaccount.com (2026-01-29)

ClusterFuzz is analyzing your testcase. Developers can follow the progress at https://clusterfuzz.com/testcase?key=6542937173196800.

### 24...@project.gserviceaccount.com (2026-01-29)

Detailed Report: https://clusterfuzz.com/testcase?key=6542937173196800

Fuzzer: None
Job Type: linux_asan_d8
Platform Id: linux

Crash Type: CHECK failure
Crash Address: 
Crash State:
  IsJSReceiver(obj)
  v8::internal::Object::GetHash
  v8::internal::OrderedHashMap::GetHash
  
Sanitizer: address (ASAN)

Regressed: https://clusterfuzz.com/revisions?job=linux_asan_d8&range=104001:104002

Reproducer Testcase: https://clusterfuzz.com/download?testcase_id=6542937173196800

To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.

If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.

If you have any feedback on reproducing test cases, let us know at https://forms.gle/Yh3qCYFveHj6E5jz5 so we can improve.


### 24...@project.gserviceaccount.com (2026-01-29)

Automatically applying components based on crash stacktrace and information from OWNERS files.

If this is incorrect, please apply the hotlistid:4801165.

### ch...@google.com (2026-01-30)

Setting milestone because of s0/s1 severity.

### ch...@google.com (2026-01-30)

This V8 bug has been marked as either a release blocker or a vulnerability bug. V8 bugs affect all OSs supported by Chrome, so the OS field has been updated to reflect this. Please update the bug with the correct OS field if it only affects a subset of OSes.

### le...@chromium.org (2026-01-30)

Victor, this issue and proposed fix looks reasonable to me, can you verify?

### vi...@chromium.org (2026-01-30)

Yes, the fix looks reasonable to me.

This issue suggests a gap in our fuzzing infrastructure, specifically regarding module coverage.

### dx...@google.com (2026-01-30)

Project: v8/v8  

Branch:  main  

Author:  Victor Gomes [victorgomes@chromium.org](mailto:victorgomes@chromium.org)  

Link:    <https://chromium-review.googlesource.com/7534881>

[maglev] Module variables can be the hole

---


Expand for full commit details
```
     
    Module variables are lowered in Maglev to 
    LoadTaggedField(cell, Cell:kValueOffset). 
     
    Drive-by: order opcodes alphabetically in CanBeTheHoleValue. 
     
    Fixed: 479726070 
    Change-Id: I2be5752906cf2ec8fdb4df497724a4d9ad55648d 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7534881 
    Auto-Submit: Victor Gomes <victorgomes@chromium.org> 
    Reviewed-by: Leszek Swirski <leszeks@chromium.org> 
    Commit-Queue: Leszek Swirski <leszeks@chromium.org> 
    Commit-Queue: Victor Gomes <victorgomes@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#105008}

```

---

Files:

- M `src/maglev/maglev-ir.cc`
- M `src/maglev/maglev-ir.h`

---

Hash: [4508b5dfb26e86f975fc57cf04350d67071fe98e](https://chromiumdash.appspot.com/commit/4508b5dfb26e86f975fc57cf04350d67071fe98e)  

Date: Fri Jan 30 14:18:32 2026


---

### 24...@project.gserviceaccount.com (2026-01-31)

ClusterFuzz testcase 6542937173196800 is verified as fixed in https://clusterfuzz.com/revisions?job=linux_asan_d8&range=105007:105008

If this is incorrect, please add the hotlistid:5433040 and re-open the issue.

### ch...@google.com (2026-01-31)

Security Merge Request Consideration: This is sufficiently serious that it should be merged to stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M144. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately.
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

### ch...@google.com (2026-01-31)

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

### ch...@google.com (2026-01-31)

Merge review required: M144 is already shipping to stable.

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
Owners: alonbajayo (ChromeOS), srinivassista (Desktop US), None (Desktop EMEA), govind (Mobile US), eakpobaro (Mobile EMEA)

### dr...@chromium.org (2026-02-02)

No crashes in Canary yet, approving merge to M144 and M145.

### vi...@chromium.org (2026-02-02)

1. High impact vulnerability
2. <https://chromium-review.googlesource.com/c/v8/v8/+/7534881>
3. Yes
4. No
5. N/A
6. No

### go...@google.com (2026-02-02)

Please merge to M144 by 11:00 AM PT today as we're cutting M144 Stable refresh today for release tomorrow. 

### dx...@google.com (2026-02-02)

Project: v8/v8  

Branch:  refs/branch-heads/14.4  

Author:  Victor Gomes [victorgomes@chromium.org](mailto:victorgomes@chromium.org)  

Link:    <https://chromium-review.googlesource.com/7535119>

Merge: [maglev] Module variables can be the hole

---


Expand for full commit details
```
     
    Module variables are lowered in Maglev to 
    LoadTaggedField(cell, Cell:kValueOffset). 
     
    Drive-by: order opcodes alphabetically in CanBeTheHoleValue. 
     
    Fixed: 479726070 
     
    (cherry picked from commit 4508b5dfb26e86f975fc57cf04350d67071fe98e) 
     
    Change-Id: I7487d9a83de83b1af7eb2917820d179b576676cf 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7535119 
    Commit-Queue: Marja Hölttä <marja@chromium.org> 
    Reviewed-by: Marja Hölttä <marja@chromium.org> 
    Auto-Submit: Victor Gomes <victorgomes@chromium.org> 
    Cr-Commit-Position: refs/branch-heads/14.4@{#46} 
    Cr-Branched-From: 80acc26727d5a34e77dabeebe7c9213ec1bd4768-refs/heads/14.4.258@{#1} 
    Cr-Branched-From: ce7e597e90f6df3fa4b6df224bc613b80c635450-refs/heads/main@{#104020}

```

---

Files:

- M `src/maglev/maglev-ir.cc`
- M `src/maglev/maglev-ir.h`

---

Hash: [87d8ea13e6e3b22d1c161f500184d4abc02aa049](https://chromiumdash.appspot.com/commit/87d8ea13e6e3b22d1c161f500184d4abc02aa049)  

Date: Fri Jan 30 14:18:32 2026


---

### dx...@google.com (2026-02-02)

Project: v8/v8  

Branch:  refs/branch-heads/14.5  

Author:  Victor Gomes [victorgomes@chromium.org](mailto:victorgomes@chromium.org)  

Link:    <https://chromium-review.googlesource.com/7535118>

Merged: [maglev] Module variables can be the hole

---


Expand for full commit details
```
     
    Module variables are lowered in Maglev to 
    LoadTaggedField(cell, Cell:kValueOffset). 
     
    Drive-by: order opcodes alphabetically in CanBeTheHoleValue. 
     
    Fixed: 479726070 
     
    (cherry picked from commit 4508b5dfb26e86f975fc57cf04350d67071fe98e) 
     
    Change-Id: Id95ce81d1f86a6dadea3f7c0883cb14b4cc5087f 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7535118 
    Reviewed-by: Marja Hölttä <marja@chromium.org> 
    Commit-Queue: Marja Hölttä <marja@chromium.org> 
    Auto-Submit: Victor Gomes <victorgomes@chromium.org> 
    Cr-Commit-Position: refs/branch-heads/14.5@{#8} 
    Cr-Branched-From: f09d67c66114951c0ea3dc9d4b025461670a9557-refs/heads/14.5.201@{#2} 
    Cr-Branched-From: 3f006438f768659ed9776359a421dc432edce53f-refs/heads/main@{#104623}

```

---

Files:

- M `src/maglev/maglev-ir.cc`
- M `src/maglev/maglev-ir.h`

---

Hash: [64f39da03f085c62991c32e0d500642814b4c862](https://chromiumdash.appspot.com/commit/64f39da03f085c62991c32e0d500642814b4c862)  

Date: Fri Jan 30 14:18:32 2026


---

### wf...@chromium.org (2026-02-02)

I don't think this issue was in 142 as the culprit CL looks like <https://chromium-review.googlesource.com/c/v8/v8/+/7207566> which landed in 144 - but please correct me if I am wrong. Removing the `142` foundin.

### dx...@google.com (2026-02-03)

Project: v8/v8  

Branch:  main  

Author:  Victor Gomes [victorgomes@chromium.org](mailto:victorgomes@chromium.org)  

Link:    <https://chromium-review.googlesource.com/7535117>

[test] Variable module hole check

---


Expand for full commit details
```
     
    Bug: 479726070 
    Change-Id: I2a98eece35dc2efb174301208df63662de20427a 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7535117 
    Reviewed-by: Leszek Swirski <leszeks@chromium.org> 
    Commit-Queue: Leszek Swirski <leszeks@chromium.org> 
    Auto-Submit: Victor Gomes <victorgomes@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#105062}

```

---

Files:

- A `test/mjsunit/maglev/regress-480100972.mjs`

---

Hash: [11a55a4424043c3fd154f72fe580c0a748d7b93c](https://chromiumdash.appspot.com/commit/11a55a4424043c3fd154f72fe580c0a748d7b93c)  

Date: Mon Feb 2 10:00:29 2026


---

### dm...@chromium.org (2026-02-06)

Is this really a Vulnerability? With the unmapped hole (currently enabled by default), accessing the\_hole will reliably crash. Maybe I just lack imagination, but I don't see how this can be exploited.

### le...@chromium.org (2026-02-06)

At the time of filing, holes were not unmapped on 32-bit (they are now, so that future issues like this aren't vulns)

### sp...@google.com (2026-02-19)

** NOTE: This is an automatically generated email **

Hello,

Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $10000.00 for this report.

Rationale for this decision:
High quality memory corruption in a sandboxed process


Important: If you aren't already registered with Google as a supplier, p2p-vrp@google.com will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.

If you have any payment related requests, please direct them to p2p-vrp@google.com. Please remember to include the subject of this email and the email address that the report was sent from.


Thank you for your efforts and helping us make Chrome more secure for all users!

Cheers,
Chrome VRP Panel Bot


P.S. One other thing we'd like to mention:

* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.

Please contact security-vrp@chromium.org with any questions.

### ch...@google.com (2026-05-09)

This bug has been closed for more than 14 weeks. Removing issue access restrictions.

## Bounty Award

> High quality memory corruption in a sandboxed process

---
*Data from [Chromium Issue Tracker](https://issues.chromium.org/issues/479726070)*
