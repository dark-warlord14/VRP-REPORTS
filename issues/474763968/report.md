# ClipboardHost custom format methods bypass IsClipboardPasteAllowed (Issue 40051481 incomplete)

| Field | Value |
|-------|-------|
| **Issue ID** | [474763968](https://issues.chromium.org/issues/474763968) |
| **Status** | Assigned |
| **Severity** | S3-Low |
| **Priority** | P3 |
| **Component** | Blink>DataTransfer |
| **Platforms** | Android, Linux, Mac, Windows, ChromeOS |
| **Chrome Version** | 145.0.7626.0 |
| **Reporter** | vi...@gmail.com |
| **Assignee** | ro...@microsoft.com |
| **Created** | 2026-01-10 |
| **Bounty** | $2,000.00 |

## Description

# Steps to reproduce the problem

STEPS TO REPRODUCE:

1. Build Chromium content\_shell
2. Start HTTP server from the Release directory:
   cd [chromium\_src]/out/Release
   python -m http.server 8888
3. Copy the attached PoC files (poc.html, victim.html) to the Release directory
4. Open victim.html in NORMAL Chrome browser:
   <http://localhost:8888/victim.html>
   Click "Copy Sensitive Data" to put test data on clipboard
5. Launch content\_shell with MojoJS (simulates compromised renderer):
   .\content\_shell.exe --enable-blink-features=MojoJS,MojoJSTest <http://localhost:8888/poc.html>

VULNERABILITY:
In content/browser/renderer\_host/clipboard\_host\_impl.cc:

- ReadAvailableCustomAndStandardFormats() (line 607)
- ReadUnsanitizedCustomFormat() (line 616)

These methods do not call IsRendererPasteAllowed() before accessing clipboard.

Other Read methods (ReadText, ReadHtml, ReadImage, etc.) do have this check.

Related: [Issue 40051481](https://issues.chromium.org/issues/40051481) addressed similar clipboard permission bypass.

# Problem Description

In content/browser/renderer\_host/clipboard\_host\_impl.cc, two methods access clipboard data without calling IsRendererPasteAllowed():

ReadAvailableCustomAndStandardFormats() (line 607)
ReadUnsanitizedCustomFormat() (line 616)
Other Read methods in the same file do call IsRendererPasteAllowed() before accessing clipboard data:

ReadText()
ReadHtml()
ReadSvg()
ReadRtf()
ReadPng()
ReadFiles()
ReadDataTransferCustomData()
Historical Context:

The custom format methods were added in September 2021 (commit 8aa9dc97 - "[Clipboard API] Clipboard Custom Formats implementation Part 7"). [Issue 40051481](https://issues.chromium.org/issues/40051481) was fixed in October 2022, which added IsRendererPasteAllowed() checks to clipboard read methods. However, ReadAvailableCustomAndStandardFormats() and ReadUnsanitizedCustomFormat() were not updated as part of that fix.

Affected Code:
void ClipboardHostImpl::ReadAvailableCustomAndStandardFormats(
ReadAvailableCustomAndStandardFormatsCallback callback) {
// No IsRendererPasteAllowed() check
std::vector[std::u16string](javascript:void(0);) format\_types =
ui::Clipboard::GetForCurrentThread()
->ReadAvailableStandardAndCustomFormatNames(...);
std::move(callback).Run(std::move(format\_types));
}

void ClipboardHostImpl::ReadUnsanitizedCustomFormat(
const std::u16string& format,
ReadUnsanitizedCustomFormatCallback callback) {
// No IsRendererPasteAllowed() check
// ... reads clipboard data directly
}

# Additional Comments

These methods were added in September 2021 (commit 8aa9dc97) without IsRendererPasteAllowed() checks. When [Issue 40051481](https://issues.chromium.org/issues/40051481) was fixed in October 2022, the permission check was added to other clipboard read methods but these two custom format methods were not included. This is an incomplete fix of [Issue 40051481](https://issues.chromium.org/issues/40051481) rather than a regression.

The W3C Clipboard API spec Section 7.3.1 requires read() to run "check clipboard read permission" (Section 9.1.1) before accessing clipboard data. If the check fails, the operation must reject with NotAllowedError. The vulnerable methods bypass this requirement.

Reference: <https://w3c.github.io/clipboard-apis/#dom-clipboard-read>

# Summary

ClipboardHost custom format methods bypass IsClipboardPasteAllowed ([Issue 40051481](https://issues.chromium.org/issues/40051481) incomplete)

# Custom Questions

#### Reporter credit:

vicevirus

# Additional Data

Category: Security   

Chrome Channel: Not sure   

Regression: No \

## Attachments

- [poc.html](attachments/poc.html) (text/html, 3.6 KB)
- [victim.html](attachments/victim.html) (text/html, 1.1 KB)
- deleted (application/octet-stream, 0 B)
- Screen Recording 2026-01-13 at 4.08.34 PM.mov (video/quicktime, 9.2 MB)

## Timeline

### vi...@gmail.com (2026-01-10)

## Affected code:

ReadAvailableCustomAndStandardFormats():
<https://source.chromium.org/chromium/chromium/src/+/main:content/browser/renderer_host/clipboard_host_impl.cc;l=607>

ReadUnsanitizedCustomFormat():
<https://source.chromium.org/chromium/chromium/src/+/main:content/browser/renderer_host/clipboard_host_impl.cc;l=616>

The PoC uses `content_shell` + `MojoJS` only to simulate an already-compromised renderer (post-exploitation). The underlying issue is still in production code: `ClipboardHostImpl::ReadAvailableCustomAndStandardFormats` and `ReadUnsanitizedCustomFormat` do not enforce `IsRendererPasteAllowed()`, unlike other clipboard read endpoints, so a compromised renderer can bypass the paste-permission gate to enumerate and read web custom clipboard formats. Expected behavior is to apply the same gate and return empty/deny when paste is not allowed.

### ct...@chromium.org (2026-01-13)

> Launch content\_shell with MojoJS (simulates compromised renderer): .\content\_shell.exe --enable-blink-features=MojoJS,MojoJSTest <http://localhost:8888/poc.html>

This step is a bit confusing -- content\_shell is not a shipping configuration and running it with MojoJS is not a great way to simulate a compromised renderer. Are you able to reproduce in regular Chrome using a renderer with MojoJS?

That aside, this looks clearly reachable from a compromised renderer without a permission check. I think the severity of this is slightly less than [Issue 40051481](https://issues.chromium.org/issues/40051481) which allowed reading arbitrary clipboard data, as this is restricted to web custom formats.

dcheng@ do you know who is still working on Clipboard API stuff who could own this security bug?

### vi...@gmail.com (2026-01-13)

deleted

### vi...@gmail.com (2026-01-13)

Apologies for the initial confusion, this is my first time setting up a MojoJS-based repro.

I can reproduce this in Chrome for Testing 143.0.7499.192 (mac-arm64) with:

```
--enable-blink-features=MojoJS

```

Attached a repro video to demonstrate that no clipboard permissions or prior grants are involved.

Steps in the video:

1. Copied data from another browser to the clipboard.
2. Open Chrome using a completely new profile and reproduce.

### ch...@google.com (2026-01-13)

Setting milestone because of s2 severity.

### ch...@google.com (2026-01-13)

Setting Priority to P1 to match Severity s2. If this is incorrect, please reset the priority. The automation bot account won't make this change again.

### dx...@google.com (2026-01-24)

Project: chromium/src  

Branch:  main  

Author:  Rohan Raja [roraja@microsoft.com](mailto:roraja@microsoft.com)  

Link:    <https://chromium-review.googlesource.com/7509483>

Add IsRendererPasteAllowed checks to clipboard custom format methods in ClipboardHostImpl

---


Expand for full commit details
```
     
    This CL fixes a security vulnerability where 
    ReadAvailableCustomAndStandardFormats() and 
    ReadUnsanitizedCustomFormat() bypass permission checks, allowing 
    compromised renderers to read web custom clipboard formats without user 
    activation. 
     
    Changes Made: 
    - Added IsRendererPasteAllowed() check to ReadAvailableCustomAndStandardFormats() 
      Returns empty vector if permission denied 
     
    - Added IsRendererPasteAllowed() check to ReadUnsanitizedCustomFormat() 
      Returns empty BigBuffer if permission denied 
     
    - Fixed all early return paths in ReadUnsanitizedCustomFormat() to properly invoke 
      callbacks, preventing callback leaks 
     
    Risk Assessment: Low 
    - Follows established pattern from existing 
    clipboard methods. 
    - No functional changes to legitimate use cases 
    requiring user activation 
     
    Bug: 474763968 
    Change-Id: I555360a1d3f2309f2a90b8da9709b014480606ca 
    Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/7509483 
    Reviewed-by: Sambamurthy Bandaru <sambamurthy.bandaru@microsoft.com> 
    Reviewed-by: Dan Clark <daniec@microsoft.com> 
    Reviewed-by: Shweta Bindal <shwetabindal@microsoft.com> 
    Commit-Queue: Rohan Raja <roraja@microsoft.com> 
    Cr-Commit-Position: refs/heads/main@{#1574177}

```

---

Files:

- M `content/browser/renderer_host/clipboard_host_impl.cc`
- M `content/browser/renderer_host/clipboard_host_impl_unittest.cc`

---

Hash: [67ed1f75de8df62e337bef6e7725a085ad045e36](https://chromiumdash.appspot.com/commit/67ed1f75de8df62e337bef6e7725a085ad045e36)  

Date: Sat Jan 24 17:30:40 2026


---

### aj...@google.com (2026-02-11)

Setting Low severity as this requires a compromised renderer.

### sp...@google.com (2026-02-20)

** NOTE: This is an automatically generated email **

Hello,

Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $2000.00 for this report.

Rationale for this decision:
Low impact web privilege escalation + bisect


Important: If you aren't already registered with Google as a supplier, p2p-vrp@google.com will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.

If you have any payment related requests, please direct them to p2p-vrp@google.com. Please remember to include the subject of this email and the email address that the report was sent from.


Thank you for your efforts and helping us make Chrome more secure for all users!

Cheers,
Chrome VRP Panel Bot


P.S. One other thing we'd like to mention:

* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.

Please contact security-vrp@chromium.org with any questions.

### ch...@google.com (2026-05-04)

This bug has been closed for more than 14 weeks. Removing issue access restrictions.

## Bounty Award

> Low impact web privilege escalation + bisect

---
*Data from [Chromium Issue Tracker](https://issues.chromium.org/issues/474763968)*
