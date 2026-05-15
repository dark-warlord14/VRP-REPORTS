# use-after-poison on address  thread T0

| Field | Value |
|-------|-------|
| **Issue ID** | [475613896](https://issues.chromium.org/issues/475613896) |
| **Status** | Assigned |
| **Severity** | S4-Minimal |
| **Priority** | P1 |
| **Component** | Speed>Tracing |
| **Platforms** | Android, Linux, Mac, Windows, ChromeOS |
| **Reporter** | mu...@gmail.com |
| **Assignee** | et...@chromium.org |
| **Created** | 2026-01-13 |
| **Bounty** | $2,000.00 |

## Description

---

### Report description

use-after-poison on address thread T0

---

### Bug location

#### Where do you want to report your vulnerability?

Chrome VRP – Report security issues affecting the Chrome browser. [See program rules](https://bughunters.google.com/about/rules/5745167867576320/chrome-vulnerability-reward-program-rules)

---

### The problem

#### Please describe the technical details of the vulnerability

`.\tools\get_asan_chrome\chromium-145.0.7632.0-win64-asan\chrome.exe --no-sandbox --enable-tracing --view-stack-traces --sandbox-ipc --enable-logging=stderr --v=1 http://localhost:9090/testing.html`

```
=================================================================
==8388==ERROR: AddressSanitizer: use-after-poison on address 0x7ee400433b00 at pc 0x7ffdf910997d bp 0x00a87f3fe970 sp 0x00a87f3fe9b8
READ of size 8 at 0x7ee400433b00 thread T0
    #0 0x7ffdf910997c in [thunk]: xml_ffi::XmlCallbacks::`vcall'{32, {flat}} (D:\chromium\src\tools\get_asan_chrome\chromium-145.0.7632.0-win64-asan\chrome.dll+0x1838e997c)
    #1 0x7ffe0973b2c1 in base::internal::DecayedFunctorTraits<void (*)(void (perfetto::TrackEventSessionObserver::*)(const perfetto::DataSourceBase::SetupArgs &), const perfetto::DataSourceBase::SetupArgs &, perfetto::TrackEventSessionObserver *),void (perfetto::TrackEventSessionObserver::*const &)(const perfetto::DataSourceBase::SetupArgs &),const perfetto::DataSourceBase::SetupArgs &>::Invoke C:\b\s\w\ir\cache\builder\src\base\functional\bind_internal.h:663
    #2 0x7ffe0973b2c1 in base::internal::InvokeHelper<0,base::internal::FunctorTraits<void (*const &)(void (perfetto::TrackEventSessionObserver::*)(const perfetto::DataSourceBase::SetupArgs &), const perfetto::DataSourceBase::SetupArgs &, perfetto::TrackEventSessionObserver *),void (perfetto::TrackEventSessionObserver::*const &)(const perfetto::DataSourceBase::SetupArgs &),const perfetto::DataSourceBase::SetupArgs &>,void,0,1>::MakeItSo C:\b\s\w\ir\cache\builder\src\base\functional\bind_internal.h:922
    #3 0x7ffe0973b2c1 in base::internal::Invoker<base::internal::FunctorTraits<void (*const &)(void (perfetto::TrackEventSessionObserver::*)(const perfetto::DataSourceBase::SetupArgs &), const perfetto::DataSourceBase::SetupArgs &, perfetto::TrackEventSessionObserver *),void (perfetto::TrackEventSessionObserver::*const &)(const perfetto::DataSourceBase::SetupArgs &),const perfetto::DataSourceBase::SetupArgs &>,base::internal::BindState<0,1,0,void (*)(void (perfetto::TrackEventSessionObserver::*)(const perfetto::DataSourceBase::SetupArgs &), const perfetto::DataSourceBase::SetupArgs &, perfetto::TrackEventSessionObserver *),void (perfetto::TrackEventSessionObserver::*)(const perfetto::DataSourceBase::SetupArgs &),perfetto::DataSourceBase::SetupArgs>,void (perfetto::TrackEventSessionObserver *)>::RunImpl C:\b\s\w\ir\cache\builder\src\base\functional\bind_internal.h:1059
    #4 0x7ffe0973b2c1 in base::internal::Invoker<struct base::internal::FunctorTraits<void (__cdecl *const &)(void (__cdecl perfetto::TrackEventSessionObserver::*)(class perfetto::DataSourceBase::StartArgs const &), class perfetto::DataSourceBase::StartArgs const &, class perfetto::TrackEventSessionObserver *), void (__cdecl perfetto::TrackEventSessionObserver::*const &)(class perfetto::DataSourceBase::StartArgs const &), class perfetto::DataSourceBase::StartArgs const &>, struct base::internal::BindState<0, 1, 0, void (__cdecl *)(void (__cdecl perfetto::TrackEventSessionObserver::*)(class perfetto::DataSourceBase::StartArgs const &), class perfetto::DataSourceBase::StartArgs const &, class perfetto::TrackEventSessionObserver *), void (__cdecl perfetto::TrackEventSessionObserver::*)(class perfetto::DataSourceBase::StartArgs const &), class perfetto::DataSourceBase::StartArgs>, (class perfetto::TrackEventSessionObserver *)>::Run(class base::internal::BindStateBase *, class perfetto::TrackEventSessionObserver *) C:\b\s\w\ir\cache\builder\src\base\functional\bind_internal.h:979:12
    #5 0x7ffe09739442 in base::RepeatingCallback<void (perfetto::TrackEventSessionObserver *)>::Run C:\b\s\w\ir\cache\builder\src\base\functional\callback.h:343
    #6 0x7ffe09739442 in base::ObserverListThreadSafe<class perfetto::TrackEventSessionObserver, 1>::NotifyWrapper(class base::raw_ptr<class perfetto::TrackEventSessionObserver, 1>, struct base::ObserverListThreadSafe<class perfetto::TrackEventSessionObserver, 1>::NotificationData const &) C:\b\s\w\ir\cache\builder\src\base\observer_list_threadsafe.h:295:25
    #7 0x7ffe0973a3ee in base::internal::DecayedFunctorTraits<void (base::ObserverListThreadSafe<perfetto::TrackEventSessionObserver,1>::*)(base::raw_ptr<perfetto::TrackEventSessionObserver,1>, const base::ObserverListThreadSafe<perfetto::TrackEventSessionObserver,1>::NotificationData &),base::ObserverListThreadSafe<perfetto::TrackEventSessionObserver,1> *&&,base::raw_ptr<perfetto::TrackEventSessionObserver,1>,base::ObserverListThreadSafe<perfetto::TrackEventSessionObserver,1>::NotificationData &&>::Invoke C:\b\s\w\ir\cache\builder\src\base\functional\bind_internal.h:730
    #8 0x7ffe0973a3ee in base::internal::InvokeHelper<0,base::internal::FunctorTraits<void (base::ObserverListThreadSafe<perfetto::TrackEventSessionObserver,1>::*&&)(base::raw_ptr<perfetto::TrackEventSessionObserver,1>, const base::ObserverListThreadSafe<perfetto::TrackEventSessionObserver,1>::NotificationData &),base::ObserverListThreadSafe<perfetto::TrackEventSessionObserver,1> *&&,base::raw_ptr<perfetto::TrackEventSessionObserver,1>,base::ObserverListThreadSafe<perfetto::TrackEventSessionObserver,1>::NotificationData &&>,void,0,1,2>::MakeItSo C:\b\s\w\ir\cache\builder\src\base\functional\bind_internal.h:922
    #9 0x7ffe0973a3ee in base::internal::Invoker<struct base::internal::FunctorTraits<void (__cdecl base::ObserverListThreadSafe<class perfetto::TrackEventSessionObserver, 1>::*&&)(class base::raw_ptr<class perfetto::TrackEventSessionObserver, 1>, struct base::ObserverListThreadSafe<class perfetto::TrackEventSessionObserver, 1>::NotificationData const &), class base::ObserverListThreadSafe<class perfetto::TrackEventSessionObserver, 1> *&&, class base::raw_ptr<class perfetto::TrackEventSessionObserver, 1>, struct base::ObserverListThreadSafe<class perfetto::TrackEventSessionObserver, 1>::NotificationData &&>, struct base::internal::BindState<1, 1, 0, void (__cdecl base::ObserverListThreadSafe<class perfetto::TrackEventSessionObserver, 1>::*)(class base::raw_ptr<class perfetto::TrackEventSessionObserver, 1>, struct base::ObserverListThreadSafe<class perfetto::TrackEventSessionObserver, 1>::NotificationData const &), class scoped_refptr<class base::ObserverListThreadSafe<class perfetto::TrackEventSessionObserver, 1>>, class base::internal::UnretainedWrapper<class perfetto::TrackEventSessionObserver, struct base::unretained_traits::MayDangle, 0>, struct base::ObserverListThreadSafe<class perfetto::TrackEventSessionObserver, 1>::NotificationData>, (void)>::RunImpl<void (__cdecl base::ObserverListThreadSafe<class perfetto::TrackEventSessionObserver, 1>::*)(class base::raw_ptr<class perfetto::TrackEventSessionObserver, 1>, struct base::ObserverListThreadSafe<class perfetto::TrackEventSessionObserver, 1>::NotificationData const &), class std::__Cr::tuple<class scoped_refptr<class base::ObserverListThreadSafe<class perfetto::TrackEventSessionObserver, 1>>, class base::internal::UnretainedWrapper<class perfetto::TrackEventSessionObserver, struct base::unretained_traits::MayDangle, 0>, struct base::ObserverListThreadSafe<class perfetto::TrackEventSessionObserver, 1>::NotificationData>, 0, 1, 2>(void (__cdecl base::ObserverListThreadSafe<class perfetto::TrackEventSessionObserver, 1>::*&&)(class base::raw_ptr<class perfetto::TrackEventSessionObserver, 1>, struct base::ObserverListThreadSafe<class perfetto::TrackEventSessionObserver, 1>::NotificationData const &), class std::__Cr::tuple<class scoped_refptr<class base::ObserverListThreadSafe<class perfetto::TrackEventSessionObserver, 1>>, class base::internal::UnretainedWrapper<class perfetto::TrackEventSessionObserver, struct base::unretained_traits::MayDangle, 0>, struct base::ObserverListThreadSafe<class perfetto::TrackEventSessionObserver, 1>::NotificationData> &&, struct std::__Cr::integer_sequence<unsigned __int64, 0, 1, 2>) C:\b\s\w\ir\cache\builder\src\base\functional\bind_internal.h:1059:14
    #10 0x7ffe098512a8 in base::OnceCallback<void ()>::Run C:\b\s\w\ir\cache\builder\src\base\functional\callback.h:155
    #11 0x7ffe098512a8 in base::TaskAnnotator::RunTaskImpl(struct base::PendingTask &) C:\b\s\w\ir\cache\builder\src\base\task\common\task_annotator.cc:229:34
    #12 0x7ffe098216f6 in base::TaskAnnotator::RunTask C:\b\s\w\ir\cache\builder\src\base\task\common\task_annotator.h:112
    #13 0x7ffe098216f6 in base::sequence_manager::internal::ThreadControllerWithMessagePumpImpl::DoWorkImpl(class base::LazyNow *) C:\b\s\w\ir\cache\builder\src\base\task\sequence_manager\thread_controller_with_message_pump_impl.cc:472:23
    #14 0x7ffe09820583 in base::sequence_manager::internal::ThreadControllerWithMessagePumpImpl::DoWork(void) C:\b\s\w\ir\cache\builder\src\base\task\sequence_manager\thread_controller_with_message_pump_impl.cc:346:40
    #15 0x7ffe0998972e in base::MessagePumpDefault::Run(class base::MessagePump::Delegate *) C:\b\s\w\ir\cache\builder\src\base\message_loop\message_pump_default.cc:42:55
    #16 0x7ffe098233ff in base::sequence_manager::internal::ThreadControllerWithMessagePumpImpl::Run(bool, class base::TimeDelta) C:\b\s\w\ir\cache\builder\src\base\task\sequence_manager\thread_controller_with_message_pump_impl.cc:647:12
    #17 0x7ffe098c73ec in base::RunLoop::Run(class base::Location const &) C:\b\s\w\ir\cache\builder\src\base\run_loop.cc:135:14
    #18 0x7ffe13c33c3d in content::RendererMain(struct content::MainFunctionParams) C:\b\s\w\ir\cache\builder\src\content\renderer\renderer_main.cc:360:16
    #19 0x7ffe0553986d in content::RunOtherNamedProcessTypeMain(class std::__Cr::basic_string<char, struct std::__Cr::char_traits<char>, class std::__Cr::allocator<char>> const &, struct content::MainFunctionParams, class content::ContentMainDelegate *) C:\b\s\w\ir\cache\builder\src\content\app\content_main_runner_impl.cc:771:14
    #20 0x7ffe0553bd28 in content::ContentMainRunnerImpl::Run(void) C:\b\s\w\ir\cache\builder\src\content\app\content_main_runner_impl.cc:1137:10
    #21 0x7ffe0552fddf in content::RunContentProcess(struct content::ContentMainParams, class content::ContentMainRunner *) C:\b\s\w\ir\cache\builder\src\content\app\content_main.cc:358:36
    #22 0x7ffe05530582 in content::ContentMain(struct content::ContentMainParams) C:\b\s\w\ir\cache\builder\src\content\app\content_main.cc:371:10
    #23 0x7ffdf5822b06 in ChromeMain C:\b\s\w\ir\cache\builder\src\chrome\app\chrome_main.cc:191:12
    #24 0x7ff7341b4807 in MainDllLoader::Launch(struct HINSTANCE__*, class base::TimeTicks) C:\b\s\w\ir\cache\builder\src\chrome\app\main_dll_loader_win.cc:201:12
    #25 0x7ff7341b2074 in main C:\b\s\w\ir\cache\builder\src\chrome\app\chrome_exe_main_win.cc:351:20
    #26 0x7ff734697e5f in invoke_main D:\a\_work\1\s\src\vctools\crt\vcstartup\src\startup\exe_common.inl:78
    #27 0x7ff734697e5f in __scrt_common_main_seh D:\a\_work\1\s\src\vctools\crt\vcstartup\src\startup\exe_common.inl:288
    #28 0x7fff339be8d6  (C:\WINDOWS\System32\KERNEL32.DLL+0x18002e8d6)
    #29 0x7fff355ec53b  (C:\WINDOWS\SYSTEM32\ntdll.dll+0x18008c53b)

Address 0x7ee400433b00 is a wild pointer inside of access range of size 0x000000000008.
SUMMARY: AddressSanitizer: use-after-poison (D:\chromium\src\tools\get_asan_chrome\chromium-145.0.7632.0-win64-asan\chrome.dll+0x1838e997c) in [thunk]: xml_ffi::XmlCallbacks::`vcall'{32, {flat}}
Shadow bytes around the buggy address:
  0x7ee400433880: f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
  0x7ee400433900: f7 f7 f7 f7 f7 f7 f7 f7 00 f7 f7 f7 f7 f7 f7 f7
  0x7ee400433980: f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
  0x7ee400433a00: f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
  0x7ee400433a80: f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 00 f7 f7 f7 f7
=>0x7ee400433b00:[f7]f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 00 f7 f7
  0x7ee400433b80: f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
  0x7ee400433c00: 00 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
  0x7ee400433c80: f7 f7 00 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
  0x7ee400433d00: f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
  0x7ee400433d80: f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
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

==8388==ADDITIONAL INFO

==8388==Note: Please include this section with the ASan report.
Task trace:
    #0 0x7ffe09738cde in base::trace_event::TraceSessionObserverList::WillClearIncrementalState(class perfetto::DataSourceBase::ClearIncrementalStateArgs const &) C:\b\s\w\ir\cache\builder\src\base\trace_event\trace_session_observer.cc:102:7
    #1 0x7ffe09db08fb in mojo::SimpleWatcher::Context::Notify(unsigned int, struct MojoHandleSignalsState, unsigned int) C:\b\s\w\ir\cache\builder\src\mojo\public\cpp\system\simple_watcher.cc:103:13


Command line: `"D:\chromium\src\tools\get_asan_chrome\chromium-145.0.7632.0-win64-asan\chrome.exe" --type=renderer --no-pre-read-main-dll --no-sandbox --file-url-path-alias="/gen=D:\chromium\src\tools\get_asan_chrome\chromium-145.0.7632.0-win64-asan\gen" --video-capture-use-gpu-memory-buffer --lang=en-GB --device-scale-factor=1 --num-raster-threads=4 --enable-main-frame-before-activation --renderer-client-id=7 --time-ticks-at-unix-epoch=-1768139261136931 --launch-time-ticks=205221525474 --metrics-shmem-handle=4056,i,7306954522051042214,17707470118951886632,2097152 --field-trial-handle=1992,i,16776162894360259390,10038150665230881207,262144 --variations-seed-version --trace-config-handle=4052,i,10016150941017158417,8594763259026028519,128 --trace-buffer-handle=4064,i,7728697922996083413,3790315423214685690,4194304 --trace-process-track-uuid=3190708992871164437 --enable-logging=stderr --v=1 --mojo-platform-channel-handle=4068 /prefetch:1`


==8388==END OF ADDITIONAL INFO

==8388==ABORTING

```
#### Impact analysis

use-after-poison

---

### The cause

#### What version of Chrome have you found the security issue in?

145.0.7632.0

#### Is the security issue related to a crash?

Yes, it is related to a crash.

#### Choose the type of vulnerability

Memory Corruption (in a non-sandboxed process)

## Attachments

- 2026-01-14 05-47-59.mp4 (video/mp4, 12.9 MB)
- [testing.html](attachments/testing.html) (text/html, 11.0 KB)

## Timeline

### wf...@chromium.org (2026-01-13)

Thank you for this report. It appears I can reproduce but only with the `--enable-tracing` feature. This appears to be related to perfetto somehow.

### wf...@chromium.org (2026-01-13)

task posted from here <https://source.chromium.org/chromium/chromium/src/+/main:base/trace_event/trace_session_observer.cc;l=99> assigning to [etiennep@chromium.org](mailto:etiennep@chromium.org)

### wf...@chromium.org (2026-01-13)

appears to be something inside an observerlist I'm not sure how real-world exploitable this would be, but etiennep PTAL at this high sev security bug.

### ch...@google.com (2026-01-14)

Setting milestone because of s0/s1 severity.

### dx...@google.com (2026-01-15)

Project: chromium/src  

Branch:  main  

Author:  Etienne Pierre-doray [etiennep@chromium.org](mailto:etiennep@chromium.org)  

Link:    <https://chromium-review.googlesource.com/7473763>

[trace] Hold PaintTimingVisualizer as unique\_ptr to fix use-after-poison

---


Expand for full commit details
```
     
    See crbug.com/475613896 for use-after-poison 
    The blamed CL didn't introduce the bug but probably made it show 
    up because more notifications are sent to observers: 
    https://chromium-review.googlesource.com/c/chromium/src/+/7234082 
     
    In local testing, a pointer to PaintTimingVisualizer is poisoned before 
    its destructor is invoke. This is because oilpan forbids holding 
    references to GCed memory from non GC (in this case the observer list points to PaintTimingVisualizer which is within a GCed object) and poisons such memory. 
    The solution is to hold PaintTimingVisualizer outside of GCed memory 
    with a unique_ptr. 
     
    Bug: 475613896 
    Change-Id: I4fe4e3c91e03074f3a8b7fa21f152bdfaede761b 
    Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/7473763 
    Reviewed-by: Scott Haseley <shaseley@chromium.org> 
    Commit-Queue: Etienne Pierre-Doray <etiennep@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#1569820}

```

---

Files:

- M `third_party/blink/renderer/core/paint/timing/image_paint_timing_detector.cc`
- M `third_party/blink/renderer/core/paint/timing/paint_timing_detector.cc`
- M `third_party/blink/renderer/core/paint/timing/paint_timing_detector.h`
- M `third_party/blink/renderer/core/paint/timing/paint_timing_visualizer.h`
- M `third_party/blink/renderer/core/paint/timing/text_paint_timing_detector.cc`

---

Hash: [209f799f3e3e5f32cb6d4756481c9eaaaffd7478](https://chromiumdash.appspot.com/commit/209f799f3e3e5f32cb6d4756481c9eaaaffd7478)  

Date: Thu Jan 15 17:33:53 2026


---

### sa...@gmail.com (2026-01-17)

Thank you for the quick fix.

I observed that this vulnerability might be a "tip of the iceberg" situation. I’ve noticed several patterns that suggest deeper instability within the memory management subsystem, potentially leading to:

1. Garbage Collection (GC). [linux](https://issues.chromium.org/issues/475893566)
2. Invalid Free / Free on non-malloc address. [linux](https://issues.chromium.org/issues/475893566)
3. Bus Errors. (Linux)
4. FD confusion and dcheck fails because fd has truncated by os.

### sa...@gmail.com (2026-01-22)

Hi, team.

Could I get any update?

Thanks,

Best regards.

### ch...@google.com (2026-01-22)

This is a serious security regression. If you are not able to fix this quickly, please revert the change that introduced it.

If this doesn't affect a release branch, or has not been properly classified for severity, please update the Security Impact hotlist or the Severity field, and remove the ReleaseBlock hotlist.

### et...@chromium.org (2026-01-22)

The issue originally described should be fixed by Comment 6.
I defer to security team for follow-up steps.

### ch...@google.com (2026-01-23)

Security Merge Request Consideration: Requesting merge to beta (M145) because latest trunk commit (1569820) appears to be after beta branch point (1568190).
Security Merge Request - Manual Review: Merge review required: M145 is already shipping to beta.

Security Merge Request: Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [145].

Please answer the following questions so that we can safely process this merge request:

1. Which CLs should be backmerged? (Please include Gerrit links.)
2. Has this fix been verified on Canary to not pose any stability regressions?
3. Does this fix pose any potential non-verifiable stability risks?
4. Does this fix pose any known compatibility risks?
5. Does it require manual verification by the test team? If so, please describe required testing.
6. (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!

### et...@chromium.org (2026-01-23)

- Which CLs should be backmerged? (Please include Gerrit links.): <https://chromium-review.googlesource.com/7473763>
- Has this fix been verified on Canary to not pose any stability regressions?: yes
- Does this fix pose any potential non-verifiable stability risks?: No
- Does this fix pose any known compatibility risks?: No
- Does it require manual verification by the test team? If so, please describe required testing. No
- (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!

### dr...@chromium.org (2026-01-27)

Stability in Canary/Dev looks good (no crashes in this directory in versions after the fix). Merge approved.

### sr...@chromium.org (2026-01-28)

If the merges are complete, please make sure you update the bug to status:fixed, 

If not done , please make sure you get all merges complete before next week monday Feb 2, EOD PST so it can be part of stable RC #2 for M145, this is the final RC we will use for stable promotion 

### sa...@gmail.com (2026-01-30)

Hi Google VRP Team,

Now that the fix has been successfully merged into the stable/beta release and the issue is marked as 'Fixed', I would like to follow up.

Regarding my previous findings on Linux [invalid free](https://issues.chromium.org/issues/475893566) and Windows (ASan behavior), I've noticed they are no longer reproducible in the latest build. I assume the committed fix addressed the root cause of these memory instabilities as well.

Could you please provide an update for this report?

Thank you, Best regards.

### dx...@google.com (2026-01-30)

Project: chromium/src  

Branch:  refs/branch-heads/7632  

Author:  Etienne Pierre-doray [etiennep@chromium.org](mailto:etiennep@chromium.org)  

Link:    <https://chromium-review.googlesource.com/7532792>

[M145][trace] Hold PaintTimingVisualizer as unique\_ptr to fix use-after-poison

---


Expand for full commit details
```
     
    See crbug.com/475613896 for use-after-poison 
    The blamed CL didn't introduce the bug but probably made it show 
    up because more notifications are sent to observers: 
    https://chromium-review.googlesource.com/c/chromium/src/+/7234082 
     
    In local testing, a pointer to PaintTimingVisualizer is poisoned before 
    its destructor is invoke. This is because oilpan forbids holding 
    references to GCed memory from non GC (in this case the observer list points to PaintTimingVisualizer which is within a GCed object) and poisons such memory. 
    The solution is to hold PaintTimingVisualizer outside of GCed memory 
    with a unique_ptr. 
     
    (cherry picked from commit 209f799f3e3e5f32cb6d4756481c9eaaaffd7478) 
     
    Bug: 475613896 
    Change-Id: I4fe4e3c91e03074f3a8b7fa21f152bdfaede761b 
    Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/7473763 
    Reviewed-by: Scott Haseley <shaseley@chromium.org> 
    Commit-Queue: Etienne Pierre-Doray <etiennep@chromium.org> 
    Cr-Original-Commit-Position: refs/heads/main@{#1569820} 
    Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/7532792 
    Reviewed-by: Michal Mocny <mmocny@chromium.org> 
    Cr-Commit-Position: refs/branch-heads/7632@{#1492} 
    Cr-Branched-From: 0bbdf2913883391365383b0a5dfe7bf9fd1a5213-refs/heads/main@{#1568190}

```

---

Files:

- M `third_party/blink/renderer/core/paint/timing/image_paint_timing_detector.cc`
- M `third_party/blink/renderer/core/paint/timing/paint_timing_detector.cc`
- M `third_party/blink/renderer/core/paint/timing/paint_timing_detector.h`
- M `third_party/blink/renderer/core/paint/timing/paint_timing_visualizer.h`
- M `third_party/blink/renderer/core/paint/timing/text_paint_timing_detector.cc`

---

Hash: [c782b7694c1850a9595c5ce0c2397162b7eb85dc](https://chromiumdash.appspot.com/commit/c782b7694c1850a9595c5ce0c2397162b7eb85dc)  

Date: Fri Jan 30 16:33:04 2026


---

### ch...@google.com (2026-02-02)

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.

### pe...@google.com (2026-02-03)

LTS Milestone M144

This issue has been flagged as a merge candidate for Chrome OS' LTS channel. If selected, our merge team will handle any additional merges. To help us determine if this issue requires a merge to LTS, please answer this short questionnaire:

1. Was this issue a regression for the milestone it was found in?
2. Is this issue related to a change or feature merged after the latest LTS Milestone?

### et...@chromium.org (2026-02-03)

> LTS Milestone M144

This issue was found on M145 though

1. Yes, in M145
2. Yes

### qk...@google.com (2026-02-04)

Labeled this issue as not applicable for LTS M138 because M138 doesn't have the suspected CL[1]. And also, the fix requires several dependant CLs.

[1] <https://chromium-review.googlesource.com/c/chromium/src/+/6635889>

### sa...@gmail.com (2026-02-06)

Hi, team.
Are there any recent updates regarding this report?


On Wed, Feb 4, 2026, 10:52 AM <buganizer-system@google.com> wrote:

> Replying to this email means your email address will be shared with the
> team that works on this product.
> https://issues.chromium.org/issues/475613896
>
> *Changed*
>
> *qk...@google.com <qk...@google.com> added comment #20
> <https://issues.chromium.org/issues/475613896#comment20>:*
>
> Labeled this issue as not applicable for LTS M138 because M138 doesn't
> have the suspected CL[1]. And also, the fix requires several dependant CLs.
>
> [1] https://chromium-review.googlesource.com/c/chromium/src/+/6635889
>
> _______________________________
>
> *Reference Info: 475613896 use-after-poison on address thread T0*
> component:  Public Trackers > 1362134 > Chromium > Speed > Tracing
> <https://issues.chromium.org/components/1457213>
> status:  Verified
> reporter:  sancyty@gmail.com
> assignee:  et...@chromium.org
> verifier:  et...@chromium.org
> cc:  dr...@chromium.org, sancyty@gmail.com
> collaborators:  se...@chromium.org
> type:  Vulnerability
> access level:  Limited visibility
> priority:  P1
> severity:  S1
> duplicate:  475893566 <https://issues.chromium.org/issues/475893566>
> found in:  145
> hotlist:  external_security_report
> <https://issues.chromium.org/hotlists/5433527>, reward-topanel
> <https://issues.chromium.org/hotlists/5432096>, Security_Impact-Beta
> <https://issues.chromium.org/hotlists/5433097>
> retention:  Component default
> Chromium Labels:  Disable-Nags, LTS-NotApplicable-138
> Component Ancestor Tags:  Speed, Speed>Tracing
> Component Tags:  Speed>Tracing
> Merge:  Merged-145, Merged-7632
> Milestone:  145
> OS:  Android, Linux, Mac, Windows, ChromeOS
> ReleaseBlock:  Stable
>
>
> Generated by Google IssueTracker notification system.
>
> You're receiving this email because you have the following role(s) on the
> issue: cc, reporter
> Unsubscribe from this issue
> <https://issues.chromium.org/issues/475613896?unsubscribe=true>.
>


### dr...@chromium.org (2026-02-06)

[security triage] The bug is currently fixed and in the queue for evaluation at the VRP panel. We'll update the bug once we have made a reward decision.

### sa...@gmail.com (2026-02-18)

Dear Team,

​I hope you are doing well.

​Could you please update/change the reporter for this submission to my primary account, `muriarfad@gmail.com`? Additionally, if the VRP reward has been decided, I would appreciate it if the payment could be directed to that primary account as well.

​I am requesting this because my current account is not yet verified on Bugcrowd, and I would like to ensure everything is processed smoothly through my main profile.

​Thank you for your assistance.
​Best regards,

### mu...@gmail.com (2026-02-18)

deleted

### sa...@gmail.com (2026-02-18)

Dear team.

Thanks,

For adding my primary account to be reporter.

Best regards.
muriarfad.

### sp...@google.com (2026-02-19)

** NOTE: This is an automatically generated email **

Hello,

Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $2000.00 for this report.

Rationale for this decision:
Moderately mitigated memory corruption in a sandboxed process


Important: This payment will be issued by Bugcrowd. You will receive an email from Bugcrowd in the next 24 hours which contains a submission you must claim to be rewarded.

If you do not receive an email from them, please check your spam folder and then reach out to us via a comment here. For issues related to Bugcrowd itself, please contact them via https://bugcrowd.com/support.


Thank you for your efforts and helping us make Chrome more secure for all users!

Cheers,
Chrome VRP Panel Bot


P.S. One other thing we'd like to mention:

* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.

Please contact security-vrp@chromium.org with any questions.

### mu...@gmail.com (2026-02-19)

deleted

### pe...@google.com (2026-03-30)

This issue requires additional review before it can be merged to the LTS channel. Please answer the following questions to help us evaluate this merge:

1. Number of CLs needed for this fix and links to them.
2. Level of complexity (High, Medium, Low - Explain)
3. Has this been merged to a stable release? beta release?
4. Overall Recommendation (Yes, No)

### qk...@google.com (2026-03-30)

1. https://chromium-review.git.corp.google.com/c/chromium/src/+/7667983
2. Low - There was a small conflict.
3. 145
4. Yes, M144 has the suspected CL[1]. Thus, the bug can occur in M144.

[1]  https://chromium-review.googlesource.com/c/chromium/src/+/6635889

### an...@google.com (2026-03-30)

Merge approved for LTS-144

### aj...@google.com (2026-04-07)

VRP category renderer\_corrupt severity S1 identified for this issue.

Comment created using go/buganizer-mcp-server

### dx...@google.com (2026-04-09)

Project: chromium/src  

Branch:  refs/branch-heads/7559  

Author:  Gyuyoung Kim [qkim@google.com](mailto:qkim@google.com)  

Link:    <https://chromium-review.googlesource.com/7667983>

[M144-LTS][trace] Hold PaintTimingVisualizer as unique\_ptr to fix use-after-poison

---


Expand for full commit details
```
     
    See crbug.com/475613896 for use-after-poison 
    The blamed CL didn't introduce the bug but probably made it show 
    up because more notifications are sent to observers: 
    https://chromium-review.googlesource.com/c/chromium/src/+/7234082 
     
    In local testing, a pointer to PaintTimingVisualizer is poisoned before 
    its destructor is invoke. This is because oilpan forbids holding 
    references to GCed memory from non GC (in this case the observer list points to PaintTimingVisualizer which is within a GCed object) and poisons such memory. 
    The solution is to hold PaintTimingVisualizer outside of GCed memory 
    with a unique_ptr. 
     
    (cherry picked from commit 209f799f3e3e5f32cb6d4756481c9eaaaffd7478) 
     
    Bug: 475613896 
    Change-Id: I4fe4e3c91e03074f3a8b7fa21f152bdfaede761b 
    Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/7473763 
    Reviewed-by: Scott Haseley <shaseley@chromium.org> 
    Commit-Queue: Etienne Pierre-Doray <etiennep@chromium.org> 
    Cr-Original-Commit-Position: refs/heads/main@{#1569820} 
    Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/7667983 
    Commit-Queue: Gyuyoung Kim (xWF) <qkim@google.com> 
    Reviewed-by: Michael Ershov <miersh@google.com> 
    Cr-Commit-Position: refs/branch-heads/7559@{#4811} 
    Cr-Branched-From: 223dfbac1c7542a06b422390d954afe5b560b607-refs/heads/main@{#1552494}

```

---

Files:

- M `third_party/blink/renderer/core/paint/timing/image_paint_timing_detector.cc`
- M `third_party/blink/renderer/core/paint/timing/paint_timing_detector.cc`
- M `third_party/blink/renderer/core/paint/timing/paint_timing_detector.h`
- M `third_party/blink/renderer/core/paint/timing/paint_timing_visualizer.h`
- M `third_party/blink/renderer/core/paint/timing/text_paint_timing_detector.cc`

---

Hash: [cf2bad680b4463e8df11c6035c9f550703941b0a](https://chromiumdash.appspot.com/commit/cf2bad680b4463e8df11c6035c9f550703941b0a)  

Date: Thu Apr 9 04:03:37 2026


---

### ch...@google.com (2026-05-01)

This bug has been closed for more than 14 weeks. Removing issue access restrictions.

## Bounty Award

> Moderately mitigated memory corruption in a sandboxed process

---
*Data from [Chromium Issue Tracker](https://issues.chromium.org/issues/475613896)*
