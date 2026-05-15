# Improper handling of side-effects of CopyFastSmiOrObjectElements in LateLoadElimination leads to a fake object / arbitrary write primitive

| Field | Value |
|-------|-------|
| **Issue ID** | [480438199](https://issues.chromium.org/issues/480438199) |
| **Status** | Assigned |
| **Severity** | S4-Minimal |
| **Priority** | P1 |
| **Component** | Blink>JavaScript>Compiler>Maglev |
| **Platforms** | Android, Fuchsia, Linux, Mac, Windows, ChromeOS |
| **Reporter** | bj...@neodyme.io |
| **Assignee** | ni...@chromium.org |
| **Created** | 2026-02-01 |
| **Bounty** | $11,000.00 |

## Description

VULNERABILITY DETAILS

# Late Load Elimination

Inside the TurboShaft Late Load Elimination Phase, the `LateLoadEliminationAnalyzer` does not handle `Call` nodes carefully enough.
The `CopyFastSmiOrObjectElements` Builtin is handled as a special case, leading to no invalidation of memory loads apart from the first argument:

`src/compiler/turboshaft/late-load-elimination-reducer.cc`:`516-533`

```
if (builtin_id) {
  switch (*builtin_id) {
    // TODO(dmercadier): extend this list.
    case Builtin::kCopyFastSmiOrObjectElements:
      // This function just replaces the Elements array of an object.
      // It doesn't invalidate any alias or any other memory than this
      // Elements array.
      TRACE(
          ">> Call is CopyFastSmiOrObjectElements, invalidating only "
          "Elements for "
          << op.arguments()[0]);
      memory_.Invalidate(op.arguments()[0], OpIndex::Invalid(),
                         JSObject::kElementsOffset);
      return;
    default:
      break;
  }
}

```

This misses the fact that a gc scavenge operation can be triggered by this builtin, which can change the type of a `ThinString` to a `SeqString` via `Scavenger::EvacuateThinString`.

If some part of a string is loaded before and after a call to `CopyFastSmiOrObjectElements`,
without any other instructions that could potentially overwrite it, the second load gets replaced with the value loaded before the call.
In case `CopyFastSmiOrObjectElements` triggers a scavenge operation, this leads to a type confusion,
because the underlying string is being treated as a `ThinString`, even though it is a `SeqString`.

When using the `turbolev` compiler, this type confusion can be exploited by doing a `CompareOp` between the target string and some other constant string, with a type hint of `CompareOp:InternalizedString`.

# Maglev

When building the maglev graph, the graph builder uses this type hint and implements the comparison the following way:

`src/maglev/maglev-graph-builder.cc`:`2949-2967`

```
case CompareOperationHint::kInternalizedString: {
  DCHECK(kOperation == Operation::kEqual ||
         kOperation == Operation::kStrictEqual);
  ValueNode *left, *right;
  if (IsRegisterEqualToAccumulator(0)) {
    GET_VALUE_OR_ABORT(
        left, GetInternalizedString(iterator_.GetRegisterOperand(0)));
    right = left;
    SetAccumulator(GetRootConstant(RootIndex::kTrueValue));
    return ReduceResult::Done();
  }
  GET_VALUE_OR_ABORT(
      left, GetInternalizedString(iterator_.GetRegisterOperand(0)));
  GET_VALUE_OR_ABORT(
      right,
      GetInternalizedString(interpreter::Register::virtual_accumulator()));
  if (TryConstantFoldEqual(left, right)) return ReduceResult::Done();
  return SetAccumulator(BuildTaggedEqual(left, right));
}

```

`GetInternalizedString` in turn emits a `CheckedInternalizedString` node to unpack potential `ThinString`s and points further uses of the same variable to the resulting internalized string:

`src/maglev/maglev-graph-builder.cc`:`1825-1833`

```
// This node may unwrap ThinStrings.
ValueNode* maybe_unwrapping_node;
GET_VALUE_OR_ABORT(
    maybe_unwrapping_node,
    AddNewNode<CheckedInternalizedString>({node}, GetCheckType(old_type)));
known_info->alternative().set_checked_value(maybe_unwrapping_node);

current_interpreter_frame_.set(reg, maybe_unwrapping_node);
return maybe_unwrapping_node;

```
# Turbolev

On encountering the `CheckedInternalizedString` node while building the initial TurboShaft graph from the maglev graph, the `GraphBuildingNodeProcessor` lowers it the following way:

`src/compiler/turboshaft/turbolev-early-lowering-reducer-inl.h`:`67-102`

```
V<InternalizedString> CheckedInternalizedString(
    V<Object> object, V<FrameState> frame_state, bool check_smi,
    const FeedbackSource& feedback) {
  if (check_smi) {
    __ DeoptimizeIf(__ IsSmi(object), frame_state, DeoptimizeReason::kSmi,
                    feedback);
  }

  Label<InternalizedString> done(this);
  V<Map> map = __ LoadMapField(object);
  V<Word32> instance_type = __ LoadInstanceTypeField(map);

  // Go to the slow path if this is a non-string, or a non-internalised
  // string.
  static_assert((kStringTag | kInternalizedTag) == 0);
  IF (UNLIKELY(__ Word32BitwiseAnd(
          instance_type, kIsNotStringMask | kIsNotInternalizedMask))) {
    // Deopt if this isn't a string.
    __ DeoptimizeIf(__ Word32BitwiseAnd(instance_type, kIsNotStringMask),
                    frame_state, DeoptimizeReason::kWrongMap, feedback);
    // Deopt if this isn't a thin string.
    static_assert(base::bits::CountPopulation(kThinStringTagBit) == 1);
    __ DeoptimizeIfNot(__ Word32BitwiseAnd(instance_type, kThinStringTagBit),
                       frame_state, DeoptimizeReason::kWrongMap, feedback);
    // Load internalized string from thin string.
    V<InternalizedString> intern_string =
        __ template LoadField<InternalizedString>(
            object, AccessBuilder::ForThinStringActual());
    GOTO(done, intern_string);
  } ELSE {
    GOTO(done, V<InternalizedString>::Cast(object));
  }

  BIND(done, result);
  return result;
}

```

Because of the improper handling of the scavenge operation inside the Late Load Elimination Phase,
the map load can get replaced with a cached, outdated one from before the scavenge operation.
This leads to a load of the "actual" field from the underlying, now updated, string.
Because the underlying string was updated to be a `SeqString`, this load instead loads the first 4 bytes of the original string, using those as a tagged pointer to another object.
Through the replacement of the original node with the `CheckedInternalizedString` node all further uses of the original string node will now also use this arbitrary pointer,
leading to a fake object being returned in place of the original, unchanged string.

This fake object can be used by returning a pointer to some attacker controlled memory like a `JSArray` and forging a new `JSArray` with an invalid `elements` field, giving arbitrary read/write access inside the sandbox.

BISECT

The special case inside the Late Load Elimination Phase was added together with the Phase itself, in commit `32e2c6014d0daded58a1164ffc586e2e2890eb3a`, but it probably wasn't exploitable for most of the time, as there aren't many code paths making a distinction between `ThinString` and `SeqString`.

A simple fix would be to remove this special case, as it violates the assumptions made about the heap state.

VERSION

Tested on d8, V8 commit: `bdc8f396b7d81e6521ee395970935edede39349a`
Using these compilation parameters:

```
is_component_build = true
is_debug = true
symbol_level = 2
target_cpu = "x64"
v8_enable_sandbox = true
v8_enable_backtrace = true
v8_enable_fast_mksnapshot = true
v8_enable_slow_dchecks = true
v8_optimized_debug = false

```

REPRODUCTION CASE

The attached poc.js triggers a segfault via an OOB write to `0x13371330` inside the sandbox when run as:

```
./d8 --turbolev poc.js

```

CREDIT INFORMATION

Reporter credit: Bjarne Boll (@Rairosu) at Neodyme Ag

## Attachments

- [poc.js](attachments/poc.js) (text/javascript, 3.0 KB)
- [poc.js](attachments/poc.js) (text/javascript, 3.2 KB)

## Timeline

### ch...@google.com (2026-02-02)

This V8 bug has been marked as either a release blocker or a vulnerability bug. V8 bugs affect all OSs supported by Chrome, so the OS field has been updated to reflect this. Please update the bug with the correct OS field if it only affects a subset of OSes.

### cl...@appspot.gserviceaccount.com (2026-02-02)

ClusterFuzz is analyzing your testcase. Developers can follow the progress at https://clusterfuzz.com/testcase?key=6361942016851968.

### an...@chromium.org (2026-02-02)

Clusterfuzz seems to be reproducing the crash but I'll go ahead and forward to V8 shepherd with provisional severity to clear the item from our triage queue.

### ta...@google.com (2026-02-02)

Hi Darius, based on the description, I believe you are the correct person to handle this issue.

### 24...@project.gserviceaccount.com (2026-02-02)

Automatically applying components based on crash stacktrace and information from OWNERS files.

If this is incorrect, please apply the hotlistid:4801165.

### 24...@project.gserviceaccount.com (2026-02-02)

Detailed Report: https://clusterfuzz.com/testcase?key=6361942016851968

Fuzzer: None
Job Type: linux_asan_d8_dbg
Platform Id: linux

Crash Type: DCHECK failure
Crash Address: 
Crash State:
  Holder<To> v8::internal::TrustedCast(Holder<From>, SourceLocation) [To = v8::int
  T1<T> v8::internal::TrustedCast<v8::internal::Union<v8::internal::Smi, v8::inter
  v8::internal::__RT_impl_Runtime_KeyedLoadIC_Miss
  
Sanitizer: address (ASAN)

Regressed: https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=104966:104967

Reproducer Testcase: https://clusterfuzz.com/download?testcase_id=6361942016851968

To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.

If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.

If you have any feedback on reproducing test cases, let us know at https://forms.gle/Yh3qCYFveHj6E5jz5 so we can improve.


### le...@chromium.org (2026-02-03)

Nico, can you take a look since Darius is out?

### dx...@google.com (2026-02-03)

Project: v8/v8  

Branch:  main  

Author:  Nico Hartmann [nicohartmann@chromium.org](mailto:nicohartmann@chromium.org)  

Link:    <https://chromium-review.googlesource.com/7531748>

[turboshaft] Remove special builtin handling in LateLoadElimination

---


Expand for full commit details
```
     
    This looks unsound in some cases. Disabling this optimization for now. 
    Further investigation is required. 
     
    Bug: 480438199 
    Change-Id: I4b9c7daf1315f6875765c65499cc2f7c372d04a4 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7531748 
    Commit-Queue: Leszek Swirski <leszeks@chromium.org> 
    Reviewed-by: Leszek Swirski <leszeks@chromium.org> 
    Commit-Queue: Nico Hartmann <nicohartmann@chromium.org> 
    Auto-Submit: Nico Hartmann <nicohartmann@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#105052}

```

---

Files:

- M `src/compiler/turboshaft/late-load-elimination-reducer.cc`

---

Hash: [18a3288490a0c5ce58cf1b67a814d5d04f2be3e4](https://chromiumdash.appspot.com/commit/18a3288490a0c5ce58cf1b67a814d5d04f2be3e4)  

Date: Tue Feb 3 10:09:53 2026


---

### ch...@google.com (2026-02-03)

Setting milestone because of s0/s1 severity.

### ch...@google.com (2026-02-03)

This is a serious security regression. If you are not able to fix this quickly, please revert the change that introduced it.

If this doesn't affect a release branch, or has not been properly classified for severity, please update the Security Impact hotlist or the Severity field, and remove the ReleaseBlock hotlist.

### ch...@google.com (2026-02-03)

Setting Priority to P1 to match Severity s1. If this is incorrect, please reset the priority. The automation bot account won't make this change again.

### 24...@project.gserviceaccount.com (2026-02-04)

ClusterFuzz testcase 6361942016851968 is verified as fixed in https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=105051:105052

If this is incorrect, please add the hotlistid:5433040 and re-open the issue.

### wf...@chromium.org (2026-02-04)

Hi thanks for your report, VRP panel here - we note you claim a controlled write in your PoC - would it be possible to demonstrate this via a stack trace with registers?

### bj...@neodyme.io (2026-02-05)

Yeah sure, the original d8 stack trace looks like this:

```
Received signal 11 SEGV_ACCERR 386213371330

==== C stack trace ===============================

/out/x64.debug/libv8_libbase.so(_ZN2v84base5debug10StackTraceC2Ev+0x29) [0x7fb5468870d9]
/out/x64.debug/libv8_libbase.so(+0x80023) [0x7fb546887023]
/nix/store/j193mfi0f921y0kfs8vjc1znnr45ispv-glibc-2.40-66/lib/libc.so.6(+0x41da0) [0x7fb545ff0da0]
/out/x64.debug/libv8.so(+0x8635c05) [0x7fb54eecec05]
[end of stack trace]

```

and opening the coredump in gdb leaves me with these:

```
(gdb) bt
#0  0x00007fb54eecec05 in Builtins_KeyedStoreIC_Megamorphic () from /out/x64.debug/libv8.so
#1  0x00007fb54fcd9549 in Builtins_SetKeyedPropertyHandler () from /out/x64.debug/libv8.so
#2  0x000038620102dbed in ?? ()
#3  0x0000386200000011 in ?? ()
#4  0x00003862010506d1 in ?? ()
#5  0x00000000048d108a in ?? ()
#6  0x0000000000000016 in ?? ()
#7  0x0000000000000104 in ?? ()
#8  0x000038620102d0f1 in ?? ()
#9  0x0000000000000082 in ?? ()
#10 0x000035ec001a8010 in ?? ()
#11 0x00007ffd12f71750 in ?? ()
#12 0x0000000000000010 in ?? ()
#13 0x00007ffd12f71750 in ?? ()
#14 0x00007fb54ee8f245 in Builtins_InterpreterEntryTrampoline () from /out/x64.debug/libv8.so
#15 0x000038620102d0f1 in ?? ()
#16 0x00003862010505fd in ?? ()
#17 0x0000000000000000 in ?? ()
(gdb) i r
rax            0x0                 0
rbx            0x386200000011      61993557950481
rcx            0x0                 0
rdx            0x55595cf0e780      93842299742080
rsi            0x0                 0
rdi            0x38620102d101      61993574912257
rbp            0x7ffd12f71680      0x7ffd12f71680
rsp            0x7ffd12f715a8      0x7ffd12f715a8
r8             0xfff7fffffff7ffff  -2251799814209537
r9             0x2468845           38176837
r10            0x7fb54eecebc9      140416689957833
r11            0x4                 4
r12            0x2b301000791       2967839180689
r13            0x35ec00140080      59287729864832
r14            0x386200000000      61993557950464
r15            0x35ec001a8010      59287730290704
rip            0x7fb54eecec05      0x7fb54eecec05 <Builtins_KeyedStoreIC_Megamorphic+151557>
eflags         0x10246             [ PF ZF IF RF ]
cs             0x33                51
ss             0x2b                43
ds             0x0                 0
es             0x0                 0
fs             0x0                 0
gs             0x0                 0
k0             0x0                 0
k1             0xff                255
k2             0x10                16
k3             0x0                 0
k4             0xf7f7ffff          4160225279
k5             0x0                 0
k6             0x0                 0
k7             0x0                 0
fs_base        0x7fb5458a1480      140416532485248
gs_base        0x0                 0

```

I'm not quite sure where exactly it crashes, because I simply used a JSArray with a corrupted elements field and wrote somewhere far OOB, but I would assume this to be some permission checks on the address before the actual write happens?

### dm...@chromium.org (2026-02-05)

Quick comment: this looks definitely exploitable (as in: can lead to in-sandbox arbitrary controlled reads/writes). And there might be more cases of this happening without going through the CopyFastSmiOrObjectElements builtin, since LateLoadElimination assumes that string shapes "don't matter" (cf <https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/turboshaft/late-load-elimination-reducer.h;l=953-969;drc=e137c54cdb8f80c9dc70534ff016aa2e0246b6f0>), and so it assumes that GCs don't invalidate anything. This was true for Turbofan (cf previous link), but isn't true for Turbolev anymore. I'll work on a more generic fix.

Triaging note: since Turbolev is disabled by default, impact is None.

### bj...@neodyme.io (2026-02-05)

I've tinkered a bit with the original poc to let the write happen inside an optimised function instead of the interpreter, and now the stack trace and register dump clearly show the OOB write happen:

d8 stack trace:

```
Received signal 11 SEGV_ACCERR 093713371330

==== C stack trace ===============================

/out/x64.debug/libv8_libbase.so(_ZN2v84base5debug10StackTraceC2Ev+0x29) [0x7fdc092870d9]
/out/x64.debug/libv8_libbase.so(+0x80023) [0x7fdc09287023]
/nix/store/j193mfi0f921y0kfs8vjc1znnr45ispv-glibc-2.40-66/lib/libc.so.6(+0x41da0) [0x7fdc089f0da0]
/out/x64.debug/libv8.so(+0x97900b5) [0x7fdc12a290b5]
/out/x64.debug/libv8.so(+0x979008f) [0x7fdc12a2908f]
/out/x64.debug/libv8.so(_ZN2v88internal20UnalignedValueMemberIdE9set_valueEd+0x1f) [0x7fdc12aa626f]
/out/x64.debug/libv8.so(_ZN2v88internal16FixedDoubleArray3setEjd+0x56) [0x7fdc12b01f36]
/out/x64.debug/libv8.so(+0xa6ee879) [0x7fdc13987879]
/out/x64.debug/libv8.so(+0xa6ee781) [0x7fdc13987781]
/out/x64.debug/libv8.so(+0xa6e8e76) [0x7fdc13981e76]
/out/x64.debug/libv8.so(_ZN2v88internal14LookupIterator14WriteDataValueENS0_12DirectHandleINS0_6ObjectEEEb+0x2ef) [0x7fdc13c53b2f]
/out/x64.debug/libv8.so(_ZN2v88internal6Object15SetDataPropertyEPNS0_14LookupIteratorENS0_12DirectHandleIS1_EE+0x9e6) [0x7fdc13cbfe16]
/out/x64.debug/libv8.so(_ZN2v88internal6Object19SetPropertyInternalEPNS0_14LookupIteratorENS0_12DirectHandleIS1_EENS_5MaybeINS0_11ShouldThrowEEENS0_11StoreOriginEPb+0xc3c) [0x7fdc13cbdf6c]
/out/x64.debug/libv8.so(_ZN2v88internal6Object11SetPropertyEPNS0_14LookupIteratorENS0_12DirectHandleIS1_EENS0_11StoreOriginENS_5MaybeINS0_11ShouldThrowEEE+0x6a) [0x7fdc13cb4ffa]
/out/x64.debug/libv8.so(_ZN2v88internal7Runtime17SetObjectPropertyEPNS0_7IsolateENS0_12DirectHandleINS0_5UnionIJNS0_3SmiENS0_10HeapNumberENS0_6BigIntENS0_6StringENS0_6SymbolENS0_7BooleanENS0_4NullENS0_9UndefinedENS0_10JSReceiverEEEEEENS4_INS0_6ObjectEEESI_NS0_17MaybeDirectHandleISF_EENS0_11StoreOriginENS_5MaybeINS0_11ShouldThrowEEE+0x4b0) [0x7fdc14102760]
/out/x64.debug/libv8.so(_ZN2v88internal7Runtime17SetObjectPropertyEPNS0_7IsolateENS0_12DirectHandleINS0_5UnionIJNS0_3SmiENS0_10HeapNumberENS0_6BigIntENS0_6StringENS0_6SymbolENS0_7BooleanENS0_4NullENS0_9UndefinedENS0_10JSReceiverEEEEEENS4_INS0_6ObjectEEESI_NS0_11StoreOriginENS_5MaybeINS0_11ShouldThrowEEE+0x99) [0x7fdc14102859]
/out/x64.debug/libv8.so(_ZN2v88internal12KeyedStoreIC5StoreENS0_6HandleINS0_5UnionIJNS0_3SmiENS0_10HeapNumberENS0_6BigIntENS0_6StringENS0_6SymbolENS0_7BooleanENS0_4NullENS0_9UndefinedENS0_10JSReceiverEEEEEENS2_INS0_6ObjectEEENS0_12DirectHandleISF_EE+0xb5c) [0x7fdc136ffd4c]
/out/x64.debug/libv8.so(+0xa47153c) [0x7fdc1370a53c]
/out/x64.debug/libv8.so(_ZN2v88internal25Runtime_KeyedStoreIC_MissEiPmPNS0_7IsolateE+0x151) [0x7fdc13709e51]
/out/x64.debug/libv8.so(+0x8b9207d) [0x7fdc11e2b07d]
[end of stack trace]

```

gdb stack trace + register dump:

```
(gdb) bt
#0  0x00007fdc12a290b5 in v8::base::WriteUnalignedValue<double> (p=10132150227760, value=1.8457939563190925e-314) at ../../src/base/memory.h:43
#1  0x00007fdc12a2908f in v8::base::WriteUnalignedValue<double> (p=0x93713371330 "", value=1.8457939563190925e-314) at ../../src/base/memory.h:48
#2  0x00007fdc12aa626f in v8::internal::UnalignedValueMember<double>::set_value (this=0x93713371330, value=1.8457939563190925e-314)
    at ../../src/objects/tagged-field.h:79
#3  0x00007fdc12b01f36 in v8::internal::FixedDoubleArray::set (this=0x9370102d100, index=38176837, value=1.8457939563190925e-314)
    at ../../src/objects/fixed-array-inl.h:642
#4  0x00007fdc13987879 in v8::internal::(anonymous namespace)::FastDoubleElementsAccessor<v8::internal::(anonymous namespace)::FastPackedDoubleElementsAccessor, v8::internal::(anonymous namespace)::ElementsKindTraits<(v8::internal::ElementsKind)4> >::SetImpl (backing_store=..., entry=..., value=...)
    at ../../src/objects/elements.cc:3306
#5  0x00007fdc13987781 in v8::internal::(anonymous namespace)::FastDoubleElementsAccessor<v8::internal::(anonymous namespace)::FastPackedDoubleElementsAccessor, v8::internal::(anonymous namespace)::ElementsKindTraits<(v8::internal::ElementsKind)4> >::SetImpl (holder=..., entry=..., value=...)
    at ../../src/objects/elements.cc:3294
#6  0x00007fdc13981e76 in v8::internal::(anonymous namespace)::ElementsAccessorBase<v8::internal::(anonymous namespace)::FastPackedDoubleElementsAccessor, v8::internal::(anonymous namespace)::ElementsKindTraits<(v8::internal::ElementsKind)4> >::Set (this=0x355c00030800, holder=..., entry=..., value=...)
    at ../../src/objects/elements.cc:815
#7  0x00007fdc13c53b2f in v8::internal::LookupIterator::WriteDataValue (this=0x7ffd73f18880, value=..., initializing_store=false)
    at ../../src/objects/lookup.cc:1150
#8  0x00007fdc13cbfe16 in v8::internal::Object::SetDataProperty (it=0x7ffd73f18880, value=...) at ../../src/objects/objects.cc:2764
#9  0x00007fdc13cbdf6c in v8::internal::Object::SetPropertyInternal (it=0x7ffd73f18880, value=..., should_throw=...,
    store_origin=v8::internal::StoreOrigin::kMaybeKeyed, found=0x7ffd73f1879b) at ../../src/objects/objects.cc:2505
#10 0x00007fdc13cb4ffa in v8::internal::Object::SetProperty (it=0x7ffd73f18880, value=..., store_origin=v8::internal::StoreOrigin::kMaybeKeyed,
    should_throw=...) at ../../src/objects/objects.cc:2546
#11 0x00007fdc14102760 in v8::internal::Runtime::SetObjectProperty (isolate=0x355c00140000, lookup_start_obj=..., key=..., value=..., maybe_receiver=...,
    store_origin=v8::internal::StoreOrigin::kMaybeKeyed, should_throw=...) at ../../src/runtime/runtime-object.cc:422
#12 0x00007fdc14102859 in v8::internal::Runtime::SetObjectProperty (isolate=0x355c00140000, object=..., key=..., value=...,
    store_origin=v8::internal::StoreOrigin::kMaybeKeyed, should_throw=...) at ../../src/runtime/runtime-object.cc:431
#13 0x00007fdc136ffd4c in v8::internal::KeyedStoreIC::Store (this=0x7ffd73f19288, object=..., key=..., value=...) at ../../src/ic/ic.cc:2811
#14 0x00007fdc1370a53c in v8::internal::__RT_impl_Runtime_KeyedStoreIC_Miss (args=..., isolate=0x355c00140000) at ../../src/ic/ic.cc:3369
#15 0x00007fdc13709e51 in v8::internal::Runtime_KeyedStoreIC_Miss (args_length=5, args_object=0x7ffd73f19448, isolate=0x355c00140000)
    at ../../src/ic/ic.cc:3336
#16 0x00007fdc11e2b07d in Builtins_CEntry_Return1_ArgvOnStack_NoBuiltinExit () from /out/x64.debug/libv8.so
#17 0x00007fdc126d9549 in Builtins_SetKeyedPropertyHandler () from /out/x64.debug/libv8.so
#18 0x00000937048d108a in ?? ()
#19 0x000009370102d0f1 in ?? ()
#20 0x0000093701031bdd in ?? ()
#21 0x0000000000000000 in ?? ()
(gdb) i r
rax            0x93713371330       10132150227760
rbx            0x7fdc13709d00      140583195680000
rcx            0xdeadbeef          3735928559
rdx            0x7fdc0f8439fa      140583129856506
rsi            0x2468845           38176837
rdi            0x93713371330       10132150227760
rbp            0x7ffd73f17c00      0x7ffd73f17c00
rsp            0x7ffd73f17c00      0x7ffd73f17c00
r8             0x7ffd73f1879b      140726548662171
r9             0x7ffd73f19430      140726548665392
r10            0x937048d108a       10131904204938
r11            0x52                82
r12            0x3cba0100082d      66769578362925
r13            0x355c00140080      58669254574208
r14            0x93700000000       10131827851264
r15            0x7ffd73f19448      140726548665416
rip            0x7fdc12a290b5      0x7fdc12a290b5 <v8::base::WriteUnalignedValue<double>(unsigned long, double)+21>
eflags         0x10202             [ IF RF ]
cs             0x33                51
ss             0x2b                43
ds             0x0                 0
es             0x0                 0
fs             0x0                 0
gs             0x0                 0
k0             0x2                 2
k1             0xff                255
k2             0x200000            2097152
k3             0x0                 0
k4             0xf7f7ffff          4160225279
k5             0x0                 0
k6             0x0                 0
k7             0x0                 0
fs_base        0x7fdc082a1480      140583006508160
gs_base        0x0                 0

```

I've added the modified poc.js as an attachement

### ch...@google.com (2026-02-11)

Security Merge Request Consideration: This is sufficiently serious that it should be merged to dev. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M146. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately.
**Merge approved:** your change passed merge requirements and is auto-approved for M146. Please go ahead and merge the CL to branch 7680 (refs/branch-heads/7680) manually. Please contact milestone owner if you have questions.
Merge instructions: <https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/process/merge_request.md>
Owners: lmenezes (ChromeOS), srinivassista (Desktop US), None (Desktop EMEA), govind (Mobile US), eakpobaro (Mobile EMEA)
Security Merge Request: Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [146].

Please answer the following questions so that we can safely process this merge request:

1. Which CLs should be backmerged? (Please include Gerrit links.)
2. Has this fix been verified on Canary to not pose any stability regressions?
3. Does this fix pose any potential non-verifiable stability risks?
4. Does this fix pose any known compatibility risks?
5. Does it require manual verification by the test team? If so, please describe required testing.
6. (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!

### ch...@google.com (2026-02-16)

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.

### ni...@chromium.org (2026-02-17)

This fix is already in 146 (see https://chromiumdash.appspot.com/commit/18a3288490a0c5ce58cf1b67a814d5d04f2be3e4)

### ni...@chromium.org (2026-02-17)

Please clarify if further backmerging is necessary.

### sp...@google.com (2026-02-19)

** NOTE: This is an automatically generated email **

Hello,

Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $11000.00 for this report.

Rationale for this decision:
High-quality report of demonstrated memory corruption in a sandboxed process plus a bisect bonus


Important: If you aren't already registered with Google as a supplier, p2p-vrp@google.com will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.

If you have any payment related requests, please direct them to p2p-vrp@google.com. Please remember to include the subject of this email and the email address that the report was sent from.


Thank you for your efforts and helping us make Chrome more secure for all users!

Cheers,
Chrome VRP Panel Bot


P.S. One other thing we'd like to mention:

* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.

Please contact security-vrp@chromium.org with any questions.

### bj...@neodyme.io (2026-02-19)

Thanks!
I'm wondering why this wasn't classified as an OOB read/write though. Is there anything missing in the PoC, because from my perspective it clearly shows an arbitrary write inside the sandbox (even though it is very flaky because it depends on a specific heap layout)?

### aj...@chromium.org (2026-02-20)

Thanks - we need to see evidence that an attacker controlled value can be written to a place that when read has consequences e.g. some hex value in a JS poc ends up in a program instruction counter.

### bj...@neodyme.io (2026-02-20)

I see, but shouldn't that exact example be mitigated by the JS sandbox (if there would be a way to make user-controlled values appear inside the IP that would grant arbitrary code execution through e.g. JIT spraying and therefore also count as a sandbox escape).

Nonetheless seeing that my exploit sets up the `caged_write` function, which is able to write almost anywhere inside the sandbox through the corrupted array, I would assume for this criteria to be met. It's just that I chose to write to 0x13371330 (+base address of the sandbox) to trigger a crash to make the impact more visible instead of looping around and corrupting another object.

Edit:

If that's not the case, I can't really grasp what is meant with "a place that when read has consequences".
As I've understood it, the whole point of the sandbox is to make any read/write inside the sandbox not have any broader consequences apart from corrupting other heap objects and maybe triggering a segfault.

### bj...@neodyme.io (2026-04-14)

Hi,

I saw that you changed the abstract about reassessments to now requiring a hotlist addition instead of a mail to [security-vrp@chromium.org](mailto:security-vrp@chromium.org),
so I thought I write a small comment here to bump this.

Also even though it's far out of the timeframe (6 weeks) by now, since I asked this in the original mail already I'm just gonna include this here as well:

```
Since the VRP rules state that controlled read/write qualifies as RCE and reports of RCE get accepted even after the issue is resolved and the reward decision is made,
would it clear up things if I would provide a exploit achieving full controlled read/write inside the sandbox cage?

```

### aj...@google.com (2026-04-21)

If you can demonstrate a v8 sbox escape you can do so in their harness.

### bj...@neodyme.io (2026-04-28)

I think there was a misunderstanding. I didn't find a v8 sbx escape.

I was under the assumption that an arbitrary write inside the sandbox cage would get classified as an arbitrary write from looking at other issues like <https://crbug.com/454485895> or <https://crbug.com/450618029> which both only achieved a caged arbitrary read and write, if I am not mistaken.

If there was a change to the classification of such bugs I'm sorry for causing trouble around this.

### ch...@google.com (2026-05-13)

This bug has been closed for more than 14 weeks. Removing issue access restrictions.

## Bounty Award

> High-quality report of demonstrated memory corruption in a sandboxed process plus a bisect bonus

---
*Data from [Chromium Issue Tracker](https://issues.chromium.org/issues/480438199)*
