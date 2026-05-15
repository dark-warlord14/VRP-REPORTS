# Regression 440523110: User Activation Bypass via showOpenFilePicker and contextmenu delay

| Field | Value |
|-------|-------|
| **Issue ID** | [474583539](https://issues.chromium.org/issues/474583539) |
| **Status** | Accepted |
| **Severity** | S3-Low |
| **Priority** | P3 |
| **Component** | UI>Browser>TopChrome>TabStrip>SplitView |
| **Platforms** | Linux, Mac, Windows, ChromeOS |
| **Chrome Version** | 143.0.7499.193 |
| **Reporter** | az...@gmail.com |
| **Assignee** | ag...@google.com |
| **Created** | 2026-01-10 |
| **Bounty** | $3,000.00 |

## Description

# Steps to reproduce the problem

1. Open the attached poc-spooff.html
2. Right-click the link and select “Open in Split View”.
3. Observe the right pane displaying drive.google.com (trusted origin).
4. After ~1 second, a native file picker dialog appears.
5. Select an image file.
6. The selected image is rendered fully in the left (attacker-controlled) split pane, despite the user being visually anchored to Google Drive.

# Problem Description

This is a regression bypass of [issue 440523110](https://issues.chromium.org/issues/440523110), not a new variant.
The previous fix correctly invalidates user activation for input[type=file].click() when triggered asynchronously after contextmenu.
However, the same user-activation invalidation does not apply to showOpenFilePicker().

As a result:

- contextmenu is still treated as a valid user activation source.
- User activation persists across setTimeout when calling File System Access API.
- Opening a link in Split View does not invalidate or reset the activation state.
- The file picker can be invoked by an attacker-controlled origin, while the user is visually anchored to a trusted origin (drive.google.com).

This creates inconsistent enforcement between legacy file input APIs and the modern File System Access API, effectively bypassing the intended fix in 440523110.

The issue is not permission bypass, but trust misattribution / UX spoofing:
users reasonably believe the file picker originates from Google Drive, while it is actually triggered by the attacker page.

# Additional Comments

For additional validation, the same proof-of-concept was reproduced on Brave Browser (latest stable version) under identical conditions.
In Brave, performing the same contextmenu + Split View interaction does not trigger any file picker or file explorer UI at all. The file selection dialog is fully blocked.

This demonstrates that the issue is not an inherent or required web platform behavior, but rather a Chromium-specific regression in how user activation is preserved for showOpenFilePicker() after asynchronous execution.

A short demonstration video recorded on Brave is attached as braveExpectedResults.mp4, showing the expected behavior where no file picker is displayed and no trust confusion occurs.

This comparison further strengthens the conclusion that Chromium currently enforces user activation inconsistently between legacy file inputs and the File System Access API, and that stricter invalidation (as implemented by Brave) is feasible and effective.

# Summary

Regression 440523110: User Activation Bypass via showOpenFilePicker and contextmenu delay

# Custom Questions

#### Type of crash:

N/A

#### Crash state:

N/A

#### Reporter credit:

Azza Tegar Naufal Ataullah

# Additional Data

Category: Security   

Chrome Channel: Stable   

Regression: Yes \

## Attachments

- [poc-spooff.html](attachments/poc-spooff.html) (text/html, 1.3 KB)
- [chromespoof#1.mp4](attachments/chromespoof#1.mp4) (video/mp4, 5.7 MB)
- [Screenshot 2026-01-10 202522.png](attachments/Screenshot 2026-01-10 202522.png) (image/png, 475.7 KB)
- braveExpectedResults.mp4 (video/mp4, 5.1 MB)

## Timeline

### ct...@chromium.org (2026-01-12)

Thanks for the report.

agale@ could you take a look? This is a bypass of the fix in [Issue 440523110](https://issues.chromium.org/issues/440523110) (as another way to trigger a file picker window).

### az...@gmail.com (2026-01-12)

Hello, thank you for the follow-up and for assigning this.

for additional information :

The previous fix correctly invalidates user activation for asynchronous invocation of input[type=file].click(). However, the same invalidation logic does not apply to showOpenFilePicker(), which allows an alternative path to invoke the file picker after a contextmenu gesture and delayed execution.

Because showOpenFilePicker() still treats the preserved activation as valid, it can be triggered while the user is visually anchored to a trusted origin via Split View, resulting in file picker trust confusion. This indicates inconsistent user activation enforcement across file selection mechanisms, rather than an issue limited to legacy input elements.

a minimal PoC is provided to demonstrate that the behavior persists despite the earlier fix, and that the bypass does not rely on race conditions, permissions, or browser extensions.

regards

### ag...@google.com (2026-01-13)

Yeah, I had been working on this a couple of months ago as a followup to [crbug.com/454484864](https://crbug.com/454484864). I actually just picked that up today so I should be able to get a CL out this week. That bug uses the other file picker API than this bug describes, but I had been working with Fergal on how to handle both.

### az...@gmail.com (2026-01-13)

deleted

### ch...@google.com (2026-01-13)

Setting milestone because of s2 severity.

### ch...@google.com (2026-01-13)

Setting Priority to P1 to match Severity s2. If this is incorrect, please reset the priority. The automation bot account won't make this change again.

### ag...@google.com (2026-01-13)

Changing the priority to P2 to match the other duplicate bugs for this topic

### az...@gmail.com (2026-01-14)

Thanks for the update. Happy to help test the fix.

### az...@gmail.com (2026-01-30)

Hi, I can confirm that this bug is no longer reproducible/has been fixed in the latest Chrome version: 144.0.7559.110

thanks

### ag...@google.com (2026-02-02)

I can close this out then. I still have some in progress work to clean up all the remaining edge cases but I can track that on the other bug I have

### az...@gmail.com (2026-02-02)

deleted

### az...@gmail.com (2026-02-09)

Hii
Is there any update regarding VRP rewards? Is it possible to receive VRP rewards in this case?

### sp...@google.com (2026-02-20)

** NOTE: This is an automatically generated email **

Hello,

Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $3000.00 for this report.

Rationale for this decision:
Security UI spoofing, Baseline // Lower Impact


Important: This payment will be issued by Bugcrowd. You will receive an email from Bugcrowd in the next 24 hours which contains a submission you must claim to be rewarded.

If you do not receive an email from them, please check your spam folder and then reach out to us via a comment here. For issues related to Bugcrowd itself, please contact them via https://bugcrowd.com/support.


Thank you for your efforts and helping us make Chrome more secure for all users!

Cheers,
Chrome VRP Panel Bot


P.S. One other thing we'd like to mention:

* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.

Please contact security-vrp@chromium.org with any questions.

### az...@gmail.com (2026-02-20)

Thank u for the bounty

### dx...@google.com (2026-04-23)

Project: chromium/src  

Branch:  main  

Author:  Alison Gale [agale@chromium.org](mailto:agale@chromium.org)  

Link:    <https://chromium-review.googlesource.com/7154160>

[SxS] Cancel file picker if active tab changes

---


Expand for full commit details
```
     
    This handles the case where a tab gets deactivated while the file picker 
    is open. One example of this happening is in split view where the user 
    is mid drag and drop when the file picker is opened. 
     
    #top-chrome-bug-fixit 
     
    Bug: 454484864,474583539 
    Change-Id: I91e869ea26b0884c5beb358516c602ec8178d5c9 
    Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/7154160 
    Commit-Queue: Alison Gale <agale@chromium.org> 
    Reviewed-by: Dana Fried <dfried@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#1619839}

```

---

Files:

- M `chrome/browser/file_select_helper.cc`
- M `chrome/browser/file_select_helper.h`
- M `chrome/browser/ui/views/file_system_access/file_system_access_browsertest.cc`

---

Hash: [9c6ca0273599b9e2713247bb751a1891ad05adf4](https://chromiumdash.appspot.com/commit/9c6ca0273599b9e2713247bb751a1891ad05adf4)  

Date: Thu Apr 23 23:45:57 2026


---

### ch...@google.com (2026-05-12)

This bug has been closed for more than 14 weeks. Removing issue access restrictions.

## Bounty Award

> Security UI spoofing, Baseline // Lower Impact

---
*Data from [Chromium Issue Tracker](https://issues.chromium.org/issues/474583539)*
