# PIP Origin Attribution Missing When Triggered from `about:blank` via Injected JavaScript

| Field | Value |
|-------|-------|
| **Issue ID** | [475238879](https://issues.chromium.org/issues/475238879) |
| **Status** | Accepted |
| **Severity** | S3-Low |
| **Priority** | P3 |
| **Component** | Blink>Media>PictureInPicture |
| **Platforms** | Linux, Mac, Windows, ChromeOS |
| **Reporter** | se...@gmail.com |
| **Assignee** | bk...@google.com |
| **Created** | 2026-01-12 |
| **Bounty** | Confirmed (amount unknown) |

## Description

---

### Report description

PIP Origin Attribution Missing When Triggered from `about:blank` via Injected JavaScript

---

### Bug location

#### Where do you want to report your vulnerability?

Chrome VRP – Report security issues affecting the Chrome browser. [See program rules](https://bughunters.google.com/about/rules/5745167867576320/chrome-vulnerability-reward-program-rules)

---

### The problem

#### Please describe the technical details of the vulnerability

Summary
When a popup window is opened at `about:blank` and dynamically populated using JavaScript from its opener, initiating a Picture-in-Picture (PiP) request from this context results in missing or incorrect origin attribution in the PiP window UI. Instead of displaying the actual execution origin, the PiP window appears without any visible site attribution.

Steps to Reproduce

1. Open the PoC URL: <https://bughunter-6.github.io/SummaTest/emptytest.html>
2. Click the button to open the popup window.
3. The popup opens at `about:blank` and is populated via injected JavaScript from the opener.
4. Click the Picture-in-Picture button inside the popup.
5. Observe the PiP window UI.
6. The PiP window does not display any origin or site attribution.

POC URL: <https://drive.google.com/file/d/1AJyG06LioG1PsaPaX5ZSVJXceCHe61P8/view?usp=sharing>

Observed Behavior
The Picture-in-Picture window launches without showing the true origin responsible for the PiP request when the request is triggered from an `about:blank` document, despite the JavaScript executing under the opener’s origin.

Expected Behavior
The PiP window should consistently and clearly display the actual execution origin that initiated Picture-in-Picture, even if the visible document URL is `about:blank`. Blank or origin-less PiP UI should be avoided to ensure proper user awareness.

#### Impact analysis

This behavior allows attacker-controlled sites to present PiP content without exposing the real originating domain, enabling origin confusion and deceptive overlays. Users may trust a PiP window believing it is system-level or neutral, while it is actually controlled by a malicious site. An attacker could abuse this to display persistent phishing prompts, fake system alerts, or misleading media overlays while masking the true source. When combined with fullscreen or pointer lock, this significantly increases the risk of UI spoofing and social engineering attacks.

---

### The cause

#### What version of Chrome have you found the security issue in?

Version 143.0.7499.193 (Official Build) (arm64)

#### Is the security issue related to a crash?

No, it is not related to a crash.

#### Choose the type of vulnerability

Security UI Spoofing

#### How would you like to be publicly acknowledged for your report?

Barath Stalin K( <https://in.linkedin.com/in/barathstalin>)

## Attachments

- [emptytest.html](attachments/emptytest.html) (text/html, 7.8 KB)

## Timeline

### ct...@chromium.org (2026-01-12)

Please attach your POC files to this bug.

### se...@gmail.com (2026-01-13)

I've attached the POC file here, Please check and let me know if you need any additional information.
Thanks

### pe...@google.com (2026-01-13)

Thank you for providing more feedback. Adding the requester to the CC list.

### ct...@chromium.org (2026-01-13)

Thank you.

This is showing that a Video PIP window triggered from an about:blank page (which can be scripted by its opener) does not show any URL. This *might* be abusable to cause some user confusion, although the user would in most cases see the about:blank window already. Setting Sev-Low for now and passing to PIP folks.

If this also applies to Document PIP, I think we would consider this to be higher severity.

### ch...@google.com (2026-01-13)

Setting Priority to P2 to match Severity s3. If this is incorrect, please reset the priority. The automation bot account won't make this change again.

### bk...@google.com (2026-01-16)

Thanks for the report. This will not affect document PiP, I verified by updating the POC to try and open a document PiP window, which gets blocked.

The document PiP request gets blocked by the browser navigator [here](https://source.chromium.org/chromium/chromium/src/+/main:chrome/browser/ui/browser_navigator.cc;l=602-605;drc=a143e2d03fe493cb7e4b0b0fc327ba7f5ad0be58), since the url scheme is `kAboutBlankPath`.

Now for video PiP, like Chris mentioned I don't think there is much concern here. I am ok with continuing to allow opening video PiP windows from `about:blank` pages. To help with any confusion we could display the opener's last committed origin whenever the requesting origin is opaque.

### dx...@google.com (2026-01-23)

Project: chromium/src  

Branch:  main  

Author:  Benjamin Keen [bkeen@google.com](mailto:bkeen@google.com)  

Link:    <https://chromium-review.googlesource.com/7509243>

Handle opaque origins when determining the metadata source title

---


Expand for full commit details
```
     
    Currently, media from opaque origins can have an empty source title. 
    This change implements a recursive fallback strategy that traverses the 
    opener chain to find the closest ancestor with a non-empty precursor. 
     
    This ensures a recognizable domain is displayed to the user, whenever 
    possible. 
     
    Bug: 475238879 
    Change-Id: Ic729e6fd501a430a89039463d19b37f2c5efbe68 
    Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/7509243 
    Reviewed-by: Tommy Steimel <steimel@chromium.org> 
    Commit-Queue: Benjamin Keen <bkeen@google.com> 
    Cr-Commit-Position: refs/heads/main@{#1573950}

```

---

Files:

- M `chrome/browser/picture_in_picture/video_picture_in_picture_window_controller_browsertest.cc`
- M `content/browser/media/session/media_session_impl.cc`

---

Hash: [b7b72d7dfb58395d16190c437496f0f2d3d97c2d](https://chromiumdash.appspot.com/commit/b7b72d7dfb58395d16190c437496f0f2d3d97c2d)  

Date: Fri Jan 23 22:18:02 2026


---

### sp...@google.com (2026-02-20)

*NOTE: This is an automatically generated email*

Hello,

Chrome Vulnerability Rewards Program (VRP) Panel has decided that the security impact of this
issue does not meet the criteria to qualify for a reward.

Rationale for this decision:

A reasonable and prudent user would not suffer any security implications from this issue

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

> A reasonable and prudent user would not suffer any security implications from this issue
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
*Data from [Chromium Issue Tracker](https://issues.chromium.org/issues/475238879)*
