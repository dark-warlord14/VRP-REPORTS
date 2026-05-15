# V8 Sandbox Bypass: UAF in Temporal.PlainDate.prototype.with

| Field | Value |
|-------|-------|
| **Issue ID** | [480122167](https://issues.chromium.org/issues/480122167) |
| **Status** | Assigned |
| **Severity** | S4-Minimal |
| **Priority** | P2 |
| **Component** | Blink>JavaScript>Sandbox |
| **Platforms** | Android, Fuchsia, Linux, Mac, Windows, ChromeOS |
| **Reporter** | er...@gmail.com |
| **Assignee** | ma...@google.com |
| **Created** | 2026-01-31 |
| **Bounty** | $5,000.00 |

## Description

VULNERABILITY DETAILS

A Use-After-Free vulnerability exists in the implementation of Temporal.PlainDate.prototype.with (and potentially other methods sharing the GenericWith or GenericDifferenceTemporal helpers) in V8.

The issue arises from unsafe ordering of operations in src/objects/js-temporal-objects.cc. The code captures a raw reference to the underlying Rust object (temporal\_rs::PlainDate) managed by a Managed<T> wrapper before performing operations that execute user-controlled JavaScript (specifically, options parsing and property retrieval).

If the user-controlled JavaScript (e.g., a getter) modifies the Temporal object to replace its internal backing store (the Managed<T> object) and triggers Garbage Collection, the original backing store can be freed while the C++ code still holds a reference to it. When the C++ code subsequently uses this stale reference, it accesses freed memory.

Root Cause:
  

In v8::internal::temporal::GenericWith (and similar helpers):

1. A raw reference to the Rust object is obtained: auto& rust\_object = this\_obj->wrapped\_rust();
2. PrepareCalendarFields is called, which iterates over the user-provided fields object, triggering getters.
3. Inside a getter, the attacker can:
   - Overwrite the Managed<PlainDate> field in this\_obj with a new value.
   - Trigger gc() to reclaim the old Managed<PlainDate> object (since this\_obj no longer points to it).
4. After PrepareCalendarFields returns, GenericWithHelper uses the stale rust\_object reference, causing UAF.

##### VERSION

V8 Git Commit: bdc8f396b7d81e6521ee395970935edede39349a

##### REPRODUCTION CASE

`d8 --sandbox-testing --expose-gc x.js`

Asan Report

```
=================================================================
==38803==ERROR: AddressSanitizer: heap-use-after-free on address 0x7279985ec2d0 at pc 0x5a6cd257138f bp 0x7fffdbf0a870 sp 0x7fffdbf0a868
READ of size 8 at 0x7279985ec2d0 thread T0
    #0 0x5a6cd257138e in <temporal_rs::builtins::core::calendar::Calendar>::kind third_party/rust/chromium_crates_io/vendor/temporal_rs-v0_1/src/builtins/core/calendar.rs:302:9
    #1 0x5a6cd257138e in <temporal_rs::builtins::core::plain_date::PlainDate>::with third_party/rust/chromium_crates_io/vendor/temporal_rs-v0_1/src/builtins/core/plain_date.rs:449:59
    #2 0x5a6cd2426f0d in <temporal_capi::plain_date::ffi::PlainDate>::with third_party/rust/chromium_crates_io/vendor/temporal_capi-v0_1/src/plain_date.rs:189:18
    #3 0x5a6cd242b82b in temporal_rs_PlainDate_with third_party/rust/chromium_crates_io/vendor/temporal_capi-v0_1/src/plain_date.rs:5:1
    #4 0x5a6cce27bbd8 in with third_party/rust/chromium_crates_io/vendor/temporal_capi-v0_1/bindings/cpp/temporal_rs/PlainDate.hpp:217:19
    #5 0x5a6cce27bbd8 in v8::internal::MaybeDirectHandle<v8::internal::JSTemporalPlainDate> v8::internal::temporal::GenericWithHelper<v8::internal::JSTemporalPlainDate, temporal_rs::PartialDate>(v8::internal::Isolate*, v8::internal::JSTemporalPlainDate::RustType const&, v8::internal::temporal::CombinedRecord&, v8::internal::DirectHandle<v8::internal::Object>, char const*) src/objects/js-temporal-objects.cc:3578:56
    #6 0x5a6cce238a4a in v8::internal::MaybeDirectHandle<v8::internal::JSTemporalPlainDate> v8::internal::temporal::GenericWith<v8::internal::JSTemporalPlainDate, temporal_rs::PartialDate>(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSTemporalPlainDate>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>, v8::base::Flags<v8::internal::temporal::CalendarFieldsFlag, int, int>, char const*) src/objects/js-temporal-objects.cc:3685:10
    #7 0x5a6cce152c13 in v8::internal::Builtin_Impl_TemporalPlainDatePrototypeWith(v8::internal::BuiltinArguments, v8::internal::Isolate*) src/builtins/builtins-temporal.cc:239:1
    #8 0x5a6cd21dcb35 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit setup-isolate-deserialize.cc
    #9 0x5a6cd212b829 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #10 0x5a6cd21285db in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #11 0x5a6cd212832a in Builtins_JSEntry setup-isolate-deserialize.cc
    #12 0x5a6ccc9dbde3 in Call src/execution/simulator.h:216:12
    #13 0x5a6ccc9dbde3 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:442:22
    #14 0x5a6ccc9de6a8 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #15 0x5a6ccc58b31b in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:2029:7
    #16 0x5a6ccc1793ba in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1037:44
    #17 0x5a6ccc1bde07 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5614:10
    #18 0x5a6ccc1ccba0 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6633:37
    #19 0x5a6ccc1cbdbe in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6541:18
    #20 0x5a6ccc1d0da8 in v8::Shell::Main(int, char**) src/d8/d8.cc:7456:18
    #21 0x76599942a1c9 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #22 0x76599942a28a in __libc_start_main csu/../csu/libc-start.c:360:3
    #23 0x5a6ccc065029 in _start (/home/erge/v8/v8/out/fuzzbuild/d8+0x1346029) (BuildId: bfddc83b50c0ce96)

0x7279985ec2d0 is located 0 bytes inside of 16-byte region [0x7279985ec2d0,0x7279985ec2e0)
freed by thread T0 here:
    #0 0x5a6ccc1070a6 in free (/home/erge/v8/v8/out/fuzzbuild/d8+0x13e80a6) (BuildId: bfddc83b50c0ce96)
    #1 0x5a6cce275268 in __release_shared gen/third_party/libc++/src/include/__memory/shared_count.h:65:7
    #2 0x5a6cce275268 in __release_shared gen/third_party/libc++/src/include/__memory/shared_count.h:100:25
    #3 0x5a6cce275268 in ~shared_ptr gen/third_party/libc++/src/include/__memory/shared_ptr.h:501:17
    #4 0x5a6cce275268 in void v8::internal::detail::Destructor<temporal_rs::PlainDate>(void*) src/objects/managed-inl.h:21:3
    #5 0x5a6ccd87aebd in v8::internal::(anonymous namespace)::ManagedObjectFinalizerSecondPass(v8::WeakCallbackInfo<void> const&) src/objects/managed.cc:21:3
    #6 0x5a6cccb15958 in Invoke src/handles/global-handles.cc:867:3
    #7 0x5a6cccb15958 in v8::internal::GlobalHandles::InvokeSecondPassPhantomCallbacks() src/handles/global-handles.cc:768:18
    #8 0x5a6cccb17931 in v8::internal::GlobalHandles::PostGarbageCollectionProcessing(v8::GCCallbackFlags) src/handles/global-handles.cc:886:5
    #9 0x5a6cccc3d281 in operator() src/heap/heap.cc:1727:34
    #10 0x5a6cccc3d281 in InvokeExternalCallbacks<(lambda at ../../src/heap/heap.cc:1722:38)> src/heap/heap.cc:1540:3
    #11 0x5a6cccc3d281 in v8::internal::Heap::CollectGarbage(v8::internal::AllocationSpace, v8::internal::GarbageCollectionReason, v8::GCCallbackFlags, v8::internal::PerformHeapLimitCheck, v8::internal::PerformIneffectiveMarkCompactCheck) src/heap/heap.cc:1722:3
    #12 0x5a6ccd075a1b in v8::internal::(anonymous namespace)::InvokeGC(v8::Isolate*, v8::internal::(anonymous namespace)::GCOptions) src/extensions/gc-extension.cc:209:17
    #13 0x5a6ccd073dcc in v8::internal::GCExtension::GC(v8::FunctionCallbackInfo<v8::Value> const&) src/extensions/gc-extension.cc:296:5
    #14 0x5a6cd212d5e3 in Builtins_CallApiCallbackGeneric setup-isolate-deserialize.cc
    #15 0x5a6cd212b829 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #16 0x5a6cd21285db in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #17 0x5a6cd212832a in Builtins_JSEntry setup-isolate-deserialize.cc
    #18 0x5a6ccc9dbde3 in Call src/execution/simulator.h:216:12
    #19 0x5a6ccc9dbde3 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:442:22
    #20 0x5a6ccc9da4ad in v8::internal::Execution::Call(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>, v8::base::Vector<v8::internal::DirectHandle<v8::internal::Object> const>) src/execution/execution.cc:532:10
    #21 0x5a6ccd8fd9c8 in GetPropertyWithDefinedGetter src/objects/objects.cc:1726:22
    #22 0x5a6ccd8fd9c8 in v8::internal::Object::GetPropertyWithAccessor(v8::internal::LookupIterator*) src/objects/objects.cc:1631:12
    #23 0x5a6ccd8fb110 in v8::internal::Object::GetProperty(v8::internal::LookupIterator*, bool) src/objects/objects.cc:1344:16
    #24 0x5a6cce20ca76 in GetProperty src/objects/js-objects-inl.h:90:10
    #25 0x5a6cce20ca76 in v8::Maybe<bool> v8::internal::temporal::GetSingleCalendarField<double>(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSReceiver>, v8::internal::DirectHandle<v8::internal::String>, bool&, double&, v8::Maybe<double> (*)(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::Object>)) src/objects/js-temporal-objects.cc:1910:23
    #26 0x5a6cce2088b7 in v8::internal::temporal::PrepareCalendarFields(v8::internal::Isolate*, temporal_rs::AnyCalendarKind, v8::internal::DirectHandle<v8::internal::JSReceiver>, v8::base::Flags<v8::internal::temporal::CalendarFieldsFlag, int, int>, v8::internal::temporal::RequiredFields) src/objects/js-temporal-objects.cc:2106:19
    #27 0x5a6cce23892c in v8::internal::MaybeDirectHandle<v8::internal::JSTemporalPlainDate> v8::internal::temporal::GenericWith<v8::internal::JSTemporalPlainDate, temporal_rs::PartialDate>(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSTemporalPlainDate>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>, v8::base::Flags<v8::internal::temporal::CalendarFieldsFlag, int, int>, char const*) src/objects/js-temporal-objects.cc:3675:7
    #28 0x5a6cce152c13 in v8::internal::Builtin_Impl_TemporalPlainDatePrototypeWith(v8::internal::BuiltinArguments, v8::internal::Isolate*) src/builtins/builtins-temporal.cc:239:1
    #29 0x5a6cd21dcb35 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit setup-isolate-deserialize.cc
    #30 0x5a6cd212b829 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #31 0x5a6cd21285db in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #32 0x5a6cd212832a in Builtins_JSEntry setup-isolate-deserialize.cc
    #33 0x5a6ccc9dbde3 in Call src/execution/simulator.h:216:12
    #34 0x5a6ccc9dbde3 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:442:22
    #35 0x5a6ccc9de6a8 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #36 0x5a6ccc58b31b in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:2029:7
    #37 0x5a6ccc1793ba in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1037:44
    #38 0x5a6ccc1bde07 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5614:10
    #39 0x5a6ccc1ccba0 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6633:37

previously allocated by thread T0 here:
    #0 0x5a6ccc107344 in malloc (/home/erge/v8/v8/out/fuzzbuild/d8+0x13e8344) (BuildId: bfddc83b50c0ce96)
    #1 0x5a6cd251522d in <std::alloc::System as core::alloc::global::GlobalAlloc>::alloc third_party/rust-toolchain/lib/rustlib/src/rust/library/std/src/sys/alloc/unix.rs:14:22
    #2 0x5a6cd251522d in __rustc::__rust_alloc build/rust/allocator/lib.rs:67:20
    #3 0x5a6cd2427956 in alloc::alloc::alloc third_party/rust-toolchain/lib/rustlib/src/rust/library/alloc/src/alloc.rs:95:9
    #4 0x5a6cd2427956 in <alloc::alloc::Global>::alloc_impl_runtime third_party/rust-toolchain/lib/rustlib/src/rust/library/alloc/src/alloc.rs:190:73
    #5 0x5a6cd2427956 in <alloc::alloc::Global>::alloc_impl third_party/rust-toolchain/lib/rustlib/src/rust/library/alloc/src/alloc.rs:312:9
    #6 0x5a6cd2427956 in <alloc::alloc::Global as core::alloc::Allocator>::allocate third_party/rust-toolchain/lib/rustlib/src/rust/library/alloc/src/alloc.rs:429:14
    #7 0x5a6cd2427956 in alloc::alloc::exchange_malloc third_party/rust-toolchain/lib/rustlib/src/rust/library/alloc/src/alloc.rs:489:18
    #8 0x5a6cd2427956 in <alloc::boxed::Box<temporal_capi::plain_date::ffi::PlainDate>>::new third_party/rust-toolchain/lib/rustlib/src/rust/library/alloc/src/boxed.rs:265:16
    #9 0x5a6cd2427956 in <temporal_capi::plain_date::ffi::PlainDate>::try_new::{closure#0} third_party/rust/chromium_crates_io/vendor/temporal_capi-v0_1/src/plain_date.rs:119:22
    #10 0x5a6cd2427956 in <core::result::Result<temporal_rs::builtins::core::plain_date::PlainDate, temporal_rs::error::TemporalError>>::map::<alloc::boxed::Box<temporal_capi::plain_date::ffi::PlainDate>, <temporal_capi::plain_date::ffi::PlainDate>::try_new::{closure#0}> third_party/rust-toolchain/lib/rustlib/src/rust/library/core/src/result.rs:836:25
    #11 0x5a6cd2427956 in <temporal_capi::plain_date::ffi::PlainDate>::try_new third_party/rust/chromium_crates_io/vendor/temporal_capi-v0_1/src/plain_date.rs:119:14
    #12 0x5a6cd242b09d in temporal_rs_PlainDate_try_new third_party/rust/chromium_crates_io/vendor/temporal_capi-v0_1/src/plain_date.rs:5:1
    #13 0x5a6cce235511 in temporal_rs::PlainDate::try_new(int, unsigned char, unsigned char, temporal_rs::AnyCalendarKind) third_party/rust/chromium_crates_io/vendor/temporal_capi-v0_1/bindings/cpp/temporal_rs/PlainDate.hpp:163:19
    #14 0x5a6cce2351dd in v8::internal::JSTemporalPlainDate::Constructor(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::HeapObject>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/objects/js-temporal-objects.cc:4315:22
    #15 0x5a6cce13f5fb in v8::internal::Builtin_Impl_TemporalPlainDateConstructor(v8::internal::BuiltinArguments, v8::internal::Isolate*) src/builtins/builtins-temporal.cc:196:16
    #16 0x5a6cd21dcb35 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit setup-isolate-deserialize.cc
    #17 0x5a6cd212c0e9 in Builtins_InterpreterPushArgsThenFastConstructFunction setup-isolate-deserialize.cc
    #18 0x5a6cd22e6317 in Builtins_ConstructHandler setup-isolate-deserialize.cc
    #19 0x5a6cd212b829 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #20 0x5a6cd21285db in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #21 0x5a6cd212832a in Builtins_JSEntry setup-isolate-deserialize.cc
    #22 0x5a6ccc9dbde3 in Call src/execution/simulator.h:216:12
    #23 0x5a6ccc9dbde3 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:442:22
    #24 0x5a6ccc9de6a8 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #25 0x5a6ccc58b31b in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:2029:7
    #26 0x5a6ccc1793ba in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1037:44
    #27 0x5a6ccc1bde07 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5614:10
    #28 0x5a6ccc1ccba0 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6633:37
    #29 0x5a6ccc1cbdbe in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6541:18
    #30 0x5a6ccc1d0da8 in v8::Shell::Main(int, char**) src/d8/d8.cc:7456:18
    #31 0x76599942a1c9 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #32 0x76599942a28a in __libc_start_main csu/../csu/libc-start.c:360:3
    #33 0x5a6ccc065029 in _start (/home/erge/v8/v8/out/fuzzbuild/d8+0x1346029) (BuildId: bfddc83b50c0ce96)

SUMMARY: AddressSanitizer: heap-use-after-free third_party/rust/chromium_crates_io/vendor/temporal_rs-v0_1/src/builtins/core/calendar.rs:302:9 in <temporal_rs::builtins::core::calendar::Calendar>::kind
Shadow bytes around the buggy address:
  0x7279985ec000: fa fa fd fd fa fa fd fa fa fa fd fa fa fa fd fa
  0x7279985ec080: fa fa 00 00 fa fa fd fa fa fa fd fa fa fa 00 00
  0x7279985ec100: fa fa fd fa fa fa ac 00 fa fa fd fa fa fa fd fd
  0x7279985ec180: fa fa fd fd fa fa fd fd fa fa fd fd fa fa fd fd
  0x7279985ec200: fa fa fd fd fa fa fd fd fa fa fd fd fa fa fd fd
=>0x7279985ec280: fa fa fd fa fa fa fd fd fa fa[fd]fd fa fa fd fd
  0x7279985ec300: fa fa fd fd fa fa fd fa fa fa fd fa fa fa 00 00
  0x7279985ec380: fa fa 00 00 fa fa fd fa fa fa fd fa fa fa fd fd
  0x7279985ec400: fa fa fd fd fa fa fd fd fa fa 06 fa fa fa fd fa
  0x7279985ec480: fa fa 00 fa fa fa fd fa fa fa fd fa fa fa fd fd
  0x7279985ec500: fa fa fd fd fa fa fc fa fa fa fc fa fa fa fc fa
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
==38803==ABORTING

## V8 sandbox violation detected!

```

CREDIT INFORMATION

Reporter credit: Erge

## Attachments

- [x.js](attachments/x.js) (text/javascript, 1.5 KB)
- [since.js](attachments/since.js) (text/javascript, 955 B)

## Timeline

### er...@gmail.com (2026-01-31)

Here's another POC using the `Temporal.PlainDate.prototype.since` path, the core bug pattern remains the same

### an...@chromium.org (2026-02-01)

Setting provisional severity and priority of S2, P1 and assigning to current V8 shepherd.

### ch...@google.com (2026-02-02)

This V8 bug has been marked as either a release blocker or a vulnerability bug. V8 bugs affect all OSs supported by Chrome, so the OS field has been updated to reflect this. Please update the bug with the correct OS field if it only affects a subset of OSes.

### cl...@appspot.gserviceaccount.com (2026-02-02)

ClusterFuzz is analyzing your testcase. Developers can follow the progress at https://clusterfuzz.com/testcase?key=6287175226163200.

### cl...@appspot.gserviceaccount.com (2026-02-02)

ClusterFuzz is analyzing your testcase. Developers can follow the progress at https://clusterfuzz.com/testcase?key=5861367135272960.

### 24...@project.gserviceaccount.com (2026-02-02)

Detailed Report: https://clusterfuzz.com/testcase?key=6287175226163200

Fuzzer: None
Job Type: linux_d8_sandbox_testing
Platform Id: linux

Crash Type: V8 sandbox violation
Crash Address: 
Crash State:
  NULL
Sanitizer: address (ASAN)

Crash Revision: https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&revision=105016

Reproducer Testcase: https://clusterfuzz.com/download?testcase_id=6287175226163200

To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.

If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.

If you have any feedback on reproducing test cases, let us know at https://forms.gle/Yh3qCYFveHj6E5jz5 so we can improve.


### ta...@google.com (2026-02-02)

Hi Clemens, CYPTAL?

### 24...@project.gserviceaccount.com (2026-02-02)

Detailed Report: https://clusterfuzz.com/testcase?key=6287175226163200

Fuzzer: None
Job Type: linux_d8_sandbox_testing
Platform Id: linux

Crash Type: V8 sandbox violation
Crash Address: 
Crash State:
  NULL
Sanitizer: address (ASAN)

Crash Revision: https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&revision=105016

Reproducer Testcase: https://clusterfuzz.com/download?testcase_id=6287175226163200

To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.

If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.

If you have any feedback on reproducing test cases, let us know at https://forms.gle/Yh3qCYFveHj6E5jz5 so we can improve.


### cl...@chromium.org (2026-02-03)

This macro in [`js-temporal-objects-inl.h](https://source.chromium.org/chromium/chromium/src/+/main:v8/src/objects/js-temporal-objects-inl.h;l=81;drc=af6ca53b19edb04cfb044c0bb70fcd3f0e8b0a14) looks very dangerous:

```
#define DEFINE_ACCESSORS_FOR_RUST_WRAPPER(field, JSType)        \
  inline void JSType::initialize_with_wrapped_rust_value(       \
      Tagged<Managed<JSType::RustType>> handle) {               \
    this->set_##field(handle);                                  \
  }                                                             \
  inline const JSType::RustType& JSType::wrapped_rust() const { \
    return *this->field()->raw();                               \
  }

```

Should the getter generally return a `std::shared_ptr` to ensure that the pointer stays alive even if we call out to JS while holding it?

This looks very similar to [issue 472139305](https://issues.chromium.org/issues/472139305) and [issue 454734141](https://issues.chromium.org/issues/454734141).

### ma...@google.com (2026-02-03)

> If the user-controlled JavaScript (e.g., a getter) modifies the Temporal object to replace its internal backing store (the Managed<T> object) and triggers Garbage Collection, the original backing store can be freed while the C++ code still holds a reference to it.

I don't understand: I don't think this is possible with the current API. The Rust objects are only written to during construction (mandatorily so, you cannot have a Temporal object without an associated Rust object, we *only* set it in `initialize_with_wrapped_rust_value`), once a Temporal object is created that object will stick around.

Is the issue that the JSTemporalPlainDate is "inside the sandbox" and can expect arbitrary writes, but the Rust memory is not, and should not experience UAFs?

What protects us from this pointer being overwritten with a dangling pointer? Would that be caught by the `Managed<T>` somehow?

I am unfamiliar with the details of V8 sandboxing: I'm not sure I can be convinced of the safety of a fix without help.

> Should the getter generally return a std::shared\_ptr to ensure that the pointer stays alive even if we call out to JS while holding it?

I think so, yes. Would there be performance concerns? We call it a lot to just do `->wrapped_rust().getter()`.

### er...@gmail.com (2026-02-03)

From my understanding of the issue:

> I don't understand: I don't think this is possible with the current API. The Rust objects are only written to during construction (mandatorily so, you cannot have a Temporal object without an associated Rust object, we only set it in initialize\_with\_wrapped\_rust\_value), once a Temporal object is created that object will stick around.

We can swap the Foreign object of a Temporal object to another Foreign object given arbitrary write inside the heap.
This allows us to make a certain Foreign object go out of scope and get freed from the GC, which removes its EPT[1] entry and the corresponding Rust object.
This is safe and allowed under the EPT[1] design.

> Is the issue that the JSTemporalPlainDate is "inside the sandbox" and can expect arbitrary writes, but the Rust memory is not, and should not experience UAFs?

I believe the issue is that the Temporal methods acquire a raw pointer of the Rust object, this coupled with the ability to run JS callbacks in the middle of the method allows us to free the Rust object (by the method explained above) inside the JS callback while the Temporal method still holds a reference to it.

> What protects us from this pointer being overwritten with a dangling pointer? Would that be caught by the Managed<T> somehow?

The EPT[1] ensures memory safety

[1]<https://docs.google.com/document/d/1V3sxltuFjjhp_6grGHgfqZNK57qfzGzme0QTk0IXDHk/edit?tab=t.0#heading=h.x3v2w83oezls>

### ma...@google.com (2026-02-03)

Initial attempt at a fix: <https://chromium-review.googlesource.com/c/v8/v8/+/7542404>

I'm still not fully clear on the sandboxing model (I have not yet read the docs, but plan to), so I would appreciate a more thorough review of this approach.

I'll also need help figuring out backporting procedures, I am not primarily a Chromium dev.

### ma...@google.com (2026-02-04)

I think I understand now how this works. Using the `shared_ptr` should indeed be a sufficient fix.

### cl...@chromium.org (2026-02-04)

Ack, the `shared_ptr` should fix this.

After this bug is marked fixed, bots will automatically apply labels for merges. Since this is "only" a sandbox escape, it's marked as `Security_Impact-None`, which AFAIK do not get merged by default, but in most cases we do merge them anyway. So if bots do not request backmerges I can help with doing that manually, once the fix has landed.

### dx...@google.com (2026-02-04)

Project: v8/v8  

Branch:  main  

Author:  Manish Goregaokar [manishearth@google.com](mailto:manishearth@google.com)  

Link:    <https://chromium-review.googlesource.com/7542404>

[temporal] Return shared pointer from wrapped\_rust()

---


Expand for full commit details
```
     
    This avoids potential dangling pointers in the case of sandbox memory 
    overwrites (prevents sandbox escapes). 
     
    Bug: 480122167 
    Change-Id: I86d6b50b1e71d3d4bbb7479cf8a251e06a6a6964 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7542404 
    Reviewed-by: Clemens Backes <clemensb@chromium.org> 
    Commit-Queue: Manish Goregaokar <manishearth@google.com> 
    Cr-Commit-Position: refs/heads/main@{#105072}

```

---

Files:

- M `src/objects/js-date-time-format.cc`
- M `src/objects/js-temporal-objects-inl.h`
- M `src/objects/js-temporal-objects.cc`
- M `src/objects/js-temporal-objects.h`

---

Hash: [6d1967c08bf4c3755c15f992057d64b5e13a47f4](https://chromiumdash.appspot.com/commit/6d1967c08bf4c3755c15f992057d64b5e13a47f4)  

Date: Tue Feb 3 19:35:09 2026


---

### cl...@chromium.org (2026-02-05)

Let's merge this simple fix to M145.

### ch...@google.com (2026-02-05)

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

### ma...@google.com (2026-02-06)

We should also uplift <https://chromium-review.googlesource.com/c/v8/v8/+/7549980> and <https://chromium-review.googlesource.com/c/v8/v8/+/7549983>. The first one fixes the remaining issues with this, the second one adds some defense in depth by removing calls to raw() completely.

### cl...@chromium.org (2026-02-09)

Should we merge <https://crbug.com/481749435> and <https://crbug.com/481749440> into this issue? It's all the same root cause, and you were looking into fixing it all anyway, right?

### ma...@google.com (2026-02-09)

Yes, we should.

I was at a team summit so I could only fix the immediate issue, but I was planning on working on shoring up the code around that afterwards, which I have now done.

### dx...@google.com (2026-02-09)

Project: v8/v8  

Branch:  main  

Author:  Manish Goregaokar [manishearth@google.com](mailto:manishearth@google.com)  

Link:    <https://chromium-review.googlesource.com/7549980>

[temporal] Replace persisted uses of ->raw() with ->get()

---


Expand for full commit details
```
     
    Building on the work in https://crrev.com/c/7542404, this ensures all 
    other persisted uses of `->raw()` on the stored temporal_rs Object are 
    instead persisted as `std::shared_ptr`. 
     
    I did not fix this in GetPartialDate/etc since they do not invoke JS 
    code. 
     
    Bug: 481749440,481749435,480122167 
    Change-Id: Ife6a03904b32f6ed88bf39505632e6916a6a6964 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7549980 
    Reviewed-by: Clemens Backes <clemensb@chromium.org> 
    Commit-Queue: Manish Goregaokar <manishearth@google.com> 
    Reviewed-by: Igor Sheludko <ishell@chromium.org> 
    Auto-Submit: Manish Goregaokar <manishearth@google.com> 
    Cr-Commit-Position: refs/heads/main@{#105156}

```

---

Files:

- M `src/objects/js-temporal-objects.cc`

---

Hash: [32eb92aa5cf1b98a4852de04ec9f09aa5556015b](https://chromiumdash.appspot.com/commit/32eb92aa5cf1b98a4852de04ec9f09aa5556015b)  

Date: Fri Feb 6 14:59:12 2026


---

### dr...@chromium.org (2026-02-09)

No crashes yet in M146. Approving <https://chromium-review.googlesource.com/7542404> for merge to M145.

<https://crrev.com/c/7549980> has not released yet. Let me know if you want to merge that one too.

### dx...@google.com (2026-02-10)

Project: v8/v8  

Branch:  main  

Author:  Manish Goregaokar [manishearth@google.com](mailto:manishearth@google.com)  

Link:    <https://chromium-review.googlesource.com/7549983>

[temporal] Replace all uses of raw() with wrapped\_rust()

---


Expand for full commit details
```
     
    In most cases wrapped_rust() returns a std::shared_ptr&, so it won't 
    addref unless you explicitly try and persist it, which is exactly the 
    behavior we want. 
     
    I don't think any of these usages are such that problems can happen, but 
    we should probably backport this anyway. 
     
    Bug: 480122167,481749440,481749435 
    Change-Id: I191bb7eb9d4cf984c1c96c2904c684d46a6a6964 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7549983 
    Auto-Submit: Manish Goregaokar <manishearth@google.com> 
    Reviewed-by: Igor Sheludko <ishell@chromium.org> 
    Commit-Queue: Manish Goregaokar <manishearth@google.com> 
    Reviewed-by: Clemens Backes <clemensb@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#105158}

```

---

Files:

- M `src/objects/js-temporal-objects.cc`

---

Hash: [07c84700bb5925c6d8f0ce3617f23fdfb0006f03](https://chromiumdash.appspot.com/commit/07c84700bb5925c6d8f0ce3617f23fdfb0006f03)  

Date: Fri Feb 6 16:30:53 2026


---

### ma...@google.com (2026-02-10)

@drubery I do want a merge on that, as well as <https://crrev.com/c/7549983>. <https://crrev.com/c/7549983> is more of a defense in depth measure since as far as I can tell those remaining uses of ->raw() were not persisted, but it would be good to uplift anyway.

### 24...@project.gserviceaccount.com (2026-02-10)

ClusterFuzz testcase 5782513079222272 is verified as fixed in https://clusterfuzz.com/revisions?job=linux_asan_d8_sandbox_testing&range=105155:105156

If this is incorrect, please add the hotlistid:5433040 and re-open the issue.

### dr...@chromium.org (2026-02-12)

Thanks. Still no crashes in Canary, so approving merges for all three of:

- <https://crrev.com/c/7542404>
- <https://crrev.com/c/7549980>
- <https://crrev.com/c/7549983>

We would generally merge this to Extended Stable as well, so approving for both M144 and M145.

### ch...@google.com (2026-02-16)

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.

### ma...@google.com (2026-02-17)

Uplifts:

First:

- <https://chromium-review.googlesource.com/c/v8/v8/+/7584793?usp=dashboard>
- <https://chromium-review.googlesource.com/c/v8/v8/+/7584813?usp=dashboard>

Second:

- <https://chromium-review.googlesource.com/c/v8/v8/+/7584796>
- <https://chromium-review.googlesource.com/c/v8/v8/+/7584814>

Third:

- <https://chromium-review.googlesource.com/c/v8/v8/+/7584815>
- <https://chromium-review.googlesource.com/c/v8/v8/+/7584816>

### dx...@google.com (2026-02-17)

Project: v8/v8  

Branch:  refs/branch-heads/14.5  

Author:  Manish Goregaokar [manishearth@google.com](mailto:manishearth@google.com)  

Link:    <https://chromium-review.googlesource.com/7584813>

Merged: [temporal] Return shared pointer from wrapped\_rust()

---


Expand for full commit details
```
     
    This avoids potential dangling pointers in the case of sandbox memory 
    overwrites (prevents sandbox escapes). 
     
    (cherry picked from commit 6d1967c08bf4c3755c15f992057d64b5e13a47f4) 
     
    Bug: 480122167 
    Change-Id: I504a1c5288d2f4a73dd666296681b74478c20e41 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7584813 
    Reviewed-by: Igor Sheludko <ishell@chromium.org> 
    Auto-Submit: Manish Goregaokar <manishearth@google.com> 
    Commit-Queue: Manish Goregaokar <manishearth@google.com> 
    Cr-Commit-Position: refs/branch-heads/14.5@{#14} 
    Cr-Branched-From: f09d67c66114951c0ea3dc9d4b025461670a9557-refs/heads/14.5.201@{#2} 
    Cr-Branched-From: 3f006438f768659ed9776359a421dc432edce53f-refs/heads/main@{#104623}

```

---

Files:

- M `src/objects/js-date-time-format.cc`
- M `src/objects/js-temporal-objects-inl.h`
- M `src/objects/js-temporal-objects.cc`
- M `src/objects/js-temporal-objects.h`

---

Hash: [a72bd27861f04a3baf8b7b8484bd370bedcf89a0](https://chromiumdash.appspot.com/commit/a72bd27861f04a3baf8b7b8484bd370bedcf89a0)  

Date: Tue Feb 3 19:35:09 2026


---

### dx...@google.com (2026-02-18)

Project: v8/v8  

Branch:  refs/branch-heads/14.4  

Author:  Manish Goregaokar [manishearth@google.com](mailto:manishearth@google.com)  

Link:    <https://chromium-review.googlesource.com/7584793>

Merged: [temporal] Return shared pointer from wrapped\_rust()

---


Expand for full commit details
```
     
    This avoids potential dangling pointers in the case of sandbox memory 
    overwrites (prevents sandbox escapes). 
     
    (cherry picked from commit 6d1967c08bf4c3755c15f992057d64b5e13a47f4) 
     
    Bug: 480122167 
    Change-Id: I7600250c64a1cb6b84b6711f23af511881a3a53b 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7584793 
    Commit-Queue: Manish Goregaokar <manishearth@google.com> 
    Reviewed-by: Igor Sheludko <ishell@chromium.org> 
    Auto-Submit: Manish Goregaokar <manishearth@google.com> 
    Cr-Commit-Position: refs/branch-heads/14.4@{#50} 
    Cr-Branched-From: 80acc26727d5a34e77dabeebe7c9213ec1bd4768-refs/heads/14.4.258@{#1} 
    Cr-Branched-From: ce7e597e90f6df3fa4b6df224bc613b80c635450-refs/heads/main@{#104020}

```

---

Files:

- M `src/objects/js-date-time-format.cc`
- M `src/objects/js-temporal-objects-inl.h`
- M `src/objects/js-temporal-objects.cc`
- M `src/objects/js-temporal-objects.h`

---

Hash: [1ef170b029471b7223b6e56b90c27deab68a0bc4](https://chromiumdash.appspot.com/commit/1ef170b029471b7223b6e56b90c27deab68a0bc4)  

Date: Tue Feb 3 19:35:09 2026


---

### dx...@google.com (2026-02-18)

Project: v8/v8  

Branch:  refs/branch-heads/14.5  

Author:  Manish Goregaokar [manishearth@google.com](mailto:manishearth@google.com)  

Link:    <https://chromium-review.googlesource.com/7584814>

Merged: [temporal] Replace persisted uses of ->raw() with ->get()

---


Expand for full commit details
```
     
    Building on the work in https://crrev.com/c/7542404, this ensures all 
    other persisted uses of `->raw()` on the stored temporal_rs Object are 
    instead persisted as `std::shared_ptr`. 
     
    I did not fix this in GetPartialDate/etc since they do not invoke JS 
    code. 
     
    (cherry-picked from commit 32eb92aa5cf1b98a4852de04ec9f09aa5556015b) 
     
    Bug: 481749440,481749435,480122167 
    Change-Id: Ie6dc13ae361f8964b1bac51e73a517b1c3a05cb4 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7584814 
    Reviewed-by: Igor Sheludko <ishell@chromium.org> 
    Auto-Submit: Manish Goregaokar <manishearth@google.com> 
    Commit-Queue: Manish Goregaokar <manishearth@google.com> 
    Cr-Commit-Position: refs/branch-heads/14.5@{#16} 
    Cr-Branched-From: f09d67c66114951c0ea3dc9d4b025461670a9557-refs/heads/14.5.201@{#2} 
    Cr-Branched-From: 3f006438f768659ed9776359a421dc432edce53f-refs/heads/main@{#104623}

```

---

Files:

- M `src/objects/js-temporal-objects.cc`

---

Hash: [be88f7af2d53d08a3b574216701f813848d269a9](https://chromiumdash.appspot.com/commit/be88f7af2d53d08a3b574216701f813848d269a9)  

Date: Fri Feb 6 14:59:12 2026


---

### dx...@google.com (2026-02-18)

Project: v8/v8  

Branch:  refs/branch-heads/14.5  

Author:  Manish Goregaokar [manishearth@google.com](mailto:manishearth@google.com)  

Link:    <https://chromium-review.googlesource.com/7584816>

Merged: [temporal] Replace all uses of raw() with wrapped\_rust()

---


Expand for full commit details
```
     
    In most cases wrapped_rust() returns a std::shared_ptr&, so it won't 
    addref unless you explicitly try and persist it, which is exactly the 
    behavior we want. 
     
    I don't think any of these usages are such that problems can happen, but 
    we should probably backport this anyway. 
     
    (cherry-picked from commit 07c84700bb5925c6d8f0ce3617f23fdfb0006f03) 
     
    Bug: 480122167,481749440,481749435 
    Change-Id: Ic47511269fc3bd981ff9ed15cd9234f44520588f 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7584816 
    Commit-Queue: Manish Goregaokar <manishearth@google.com> 
    Auto-Submit: Manish Goregaokar <manishearth@google.com> 
    Reviewed-by: Igor Sheludko <ishell@chromium.org> 
    Cr-Commit-Position: refs/branch-heads/14.5@{#18} 
    Cr-Branched-From: f09d67c66114951c0ea3dc9d4b025461670a9557-refs/heads/14.5.201@{#2} 
    Cr-Branched-From: 3f006438f768659ed9776359a421dc432edce53f-refs/heads/main@{#104623}

```

---

Files:

- M `src/objects/js-temporal-objects.cc`

---

Hash: [0258f2b341cfed6c6da58ad23fbf1c6f6b6a76e6](https://chromiumdash.appspot.com/commit/0258f2b341cfed6c6da58ad23fbf1c6f6b6a76e6)  

Date: Fri Feb 6 16:30:53 2026


---

### dx...@google.com (2026-02-18)

Project: v8/v8  

Branch:  refs/branch-heads/14.4  

Author:  Manish Goregaokar [manishearth@google.com](mailto:manishearth@google.com)  

Link:    <https://chromium-review.googlesource.com/7584796>

Merged: [temporal] Replace persisted uses of ->raw() with ->get()

---


Expand for full commit details
```
     
    Building on the work in https://crrev.com/c/7542404, this ensures all 
    other persisted uses of `->raw()` on the stored temporal_rs Object are 
    instead persisted as `std::shared_ptr`. 
     
    I did not fix this in GetPartialDate/etc since they do not invoke JS 
    code. 
     
    (cherry-picked from commit 32eb92aa5cf1b98a4852de04ec9f09aa5556015b) 
     
    Bug: 481749440,481749435,480122167 
    Change-Id: I59e98aed9f03100499973062e87fc92f26942042 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7584796 
    Commit-Queue: Manish Goregaokar <manishearth@google.com> 
    Auto-Submit: Manish Goregaokar <manishearth@google.com> 
    Reviewed-by: Igor Sheludko <ishell@chromium.org> 
    Cr-Commit-Position: refs/branch-heads/14.4@{#52} 
    Cr-Branched-From: 80acc26727d5a34e77dabeebe7c9213ec1bd4768-refs/heads/14.4.258@{#1} 
    Cr-Branched-From: ce7e597e90f6df3fa4b6df224bc613b80c635450-refs/heads/main@{#104020}

```

---

Files:

- M `src/objects/js-temporal-objects.cc`

---

Hash: [f05d785967b5f50cd9f26e374f3848e3df1b19e6](https://chromiumdash.appspot.com/commit/f05d785967b5f50cd9f26e374f3848e3df1b19e6)  

Date: Fri Feb 6 14:59:12 2026


---

### dx...@google.com (2026-02-18)

Project: v8/v8  

Branch:  refs/branch-heads/14.4  

Author:  Manish Goregaokar [manishearth@google.com](mailto:manishearth@google.com)  

Link:    <https://chromium-review.googlesource.com/7584815>

Merged: [temporal] Replace all uses of raw() with wrapped\_rust()

---


Expand for full commit details
```
     
    In most cases wrapped_rust() returns a std::shared_ptr&, so it won't 
    addref unless you explicitly try and persist it, which is exactly the 
    behavior we want. 
     
    I don't think any of these usages are such that problems can happen, but 
    we should probably backport this anyway. 
     
    (cherry-picked from commit 07c84700bb5925c6d8f0ce3617f23fdfb0006f03) 
     
    Bug: 480122167,481749440,481749435 
    Change-Id: I40fba3b8c1eedd4498fc6e1cd0dc209e087a2c2c 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7584815 
    Reviewed-by: Igor Sheludko <ishell@chromium.org> 
    Auto-Submit: Manish Goregaokar <manishearth@google.com> 
    Commit-Queue: Manish Goregaokar <manishearth@google.com> 
    Cr-Commit-Position: refs/branch-heads/14.4@{#54} 
    Cr-Branched-From: 80acc26727d5a34e77dabeebe7c9213ec1bd4768-refs/heads/14.4.258@{#1} 
    Cr-Branched-From: ce7e597e90f6df3fa4b6df224bc613b80c635450-refs/heads/main@{#104020}

```

---

Files:

- M `src/objects/js-temporal-objects.cc`

---

Hash: [6cd9c323f4fce7f109ff062f311cbdb38885ac64](https://chromiumdash.appspot.com/commit/6cd9c323f4fce7f109ff062f311cbdb38885ac64)  

Date: Fri Feb 6 16:30:53 2026


---

### ma...@google.com (2026-02-18)

I believe this has been completely uplifted.

### sp...@google.com (2026-02-20)

** NOTE: This is an automatically generated email **

Hello,

Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $5000.00 for this report.

Rationale for this decision:
Memory corruption outside the V8 sandbox without demonstration of controlled write


Important: If you aren't already registered with Google as a supplier, p2p-vrp@google.com will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.

If you have any payment related requests, please direct them to p2p-vrp@google.com. Please remember to include the subject of this email and the email address that the report was sent from.


Thank you for your efforts and helping us make Chrome more secure for all users!

Cheers,
Chrome VRP Panel Bot


P.S. One other thing we'd like to mention:

* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.

Please contact security-vrp@chromium.org with any questions.

### ch...@google.com (2026-05-14)

This bug has been closed for more than 14 weeks. Removing issue access restrictions.

## Bounty Award

> Memory corruption outside the V8 sandbox without demonstration of controlled write

---
*Data from [Chromium Issue Tracker](https://issues.chromium.org/issues/480122167)*
