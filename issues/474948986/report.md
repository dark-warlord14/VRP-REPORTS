# Chrome Windows - PIP Window Displays Incorrect Origin When Domain Uses RTL Characters

| Field | Value |
|-------|-------|
| **Issue ID** | [474948986](https://issues.chromium.org/issues/474948986) |
| **Status** | Assigned |
| **Severity** | S3-Low |
| **Priority** | P2 |
| **Component** | Blink>Media>PictureInPicture |
| **Platforms** | Linux, Mac, Windows, ChromeOS |
| **Reporter** | se...@gmail.com |
| **Assignee** | bk...@google.com |
| **Created** | 2026-01-11 |
| **Bounty** | $3,000.00 |

## Description

---

### Report description

Chrome Windows - PIP Window Displays Incorrect Origin When Domain Uses RTL Characters

---

### Bug location

#### Where do you want to report your vulnerability?

Chrome VRP – Report security issues affecting the Chrome browser. [See program rules](https://bughunters.google.com/about/rules/5745167867576320/chrome-vulnerability-reward-program-rules)

---

### The problem

#### Please describe the technical details of the vulnerability

Summary

When a website uses Right-to-Left Override (RTLO) characters in its subdomain, the browser’s Picture-in-Picture (PiP) window displays an incorrect and misleading origin. Instead of showing the attacker-controlled root domain (eTLD+1), the PiP UI renders a spoofed trusted domain, allowing origin impersonation.

Steps to Reproduce

1. Register or host a domain containing RTLO characters in the subdomain. POC URL:<http://xn--mgb.accounts.login.apple.com.xn--mgb.https.google.com.summa.sbs/test.html>
2. Click the PIP button
3. Observe the origin shown in the PiP window.
4. Notice that the displayed origin shows a spoofed trusted domain (apple.com.I) instead of the real eTLD+1 (summa.sbs)

Expected Behavior
The PiP window should always display the actual eTLD+1 of the media’s origin and sanitize or neutralize RTL characters to prevent misleading rendering.

Actual Behavior
The PiP UI renders RTL characters in a way that causes the origin to appear as a different, trusted domain, hiding the attacker-controlled root domain.

Proof of Concept
Displayed in PiP:
apple.com.I

Actual media origin:
summa.sbs

#### Impact analysis

An attacker can abuse RTL characters in a domain to make the Picture-in-Picture (PiP) window display a trusted brand name (for example, apple.com) while the actual content is served from an attacker-controlled domain (summa.sbs). Since PiP is a trusted, persistent UI element, users are likely to rely on the displayed origin for trust decisions. This enables convincing phishing, social-engineering, and malware delivery scenarios, as users may interact with or trust content believing it originates from a legitimate site. The absence of any alternative way to verify the true origin further increases the risk of exploitation.

Refer:
<https://issues.chromium.org/issues/40065117>
<https://issues.chromium.org/issues/40066780>

---

### The cause

#### What version of Chrome have you found the security issue in?

Version 143.0.7499.193 (Official Build) (64-bit)

#### Is the security issue related to a crash?

No, it is not related to a crash.

#### Choose the type of vulnerability

Security UI Spoofing

#### How would you like to be publicly acknowledged for your report?

Barath Stalin K (<https://www.linkedin.com/in/barathstalin/>)

## Attachments

- [Chrome PIP origin Spoof.mp4](attachments/Chrome PIP origin Spoof.mp4) (video/mp4, 6.1 MB)
- Chrome POC.mov (video/quicktime, 8.6 MB)
- Chrome Document PIP Spoof.mp4 (video/mp4, 5.4 MB)
- [test.html](attachments/test.html) (text/html, 11.1 KB)
- [pip-doc.html](attachments/pip-doc.html) (text/html, 1.6 KB)

## Timeline

### ct...@chromium.org (2026-01-13)

Thanks for the report.

Setting some security labels: FoundIn-142 (current extended stable), Sev-Medium (S2).

Assigning to steimel@ -- could you please take a look?

### ct...@chromium.org (2026-01-13)

Question for the reporter: are you able to reproduce this using Document PIP (not just Video PIP)? IMO Video PIP is less concerning here than Document PIP.

### ch...@google.com (2026-01-13)

Setting milestone because of s2 severity.

### ch...@google.com (2026-01-13)

Setting Priority to P1 to match Severity s2. If this is incorrect, please reset the priority. The automation bot account won't make this change again.

### se...@gmail.com (2026-01-13)

Thank you for the prompt response Team. After further verification, I confirmed that the RTL spoofing issue in Picture-in-Picture (PiP) is also applicable to PiP document mode. The same behavior was observed across all platform ( macOS and Linux)

Please note that the attached POC video was recorded on a macOS device (MacBook with M2 chip) for reference. Kindly use the following POC URL to reproduce the issue.

POC Domain: https://xn--mgb.summa.sbs

Let me know if you need any additional details or have any questions regarding this issue. I’ll be happy to provide further clarification if required.

Regards,
Stalin

### se...@gmail.com (2026-01-15)

Hi Team, thank you for the prompt response. I was able to fully spoof the domain using two RTL characters. The updated PoC URL is https://xn--mgb.google.com.xn--mgb.yen.summa.sbs/pip.html
 Please refer to the attached PoC video to observe the complete spoofing behavior. I have changed the URL mentioned above kindly use this updated PoC URL for further reproduction steps.

### dx...@google.com (2026-01-20)

Project: chromium/src  

Branch:  main  

Author:  Benjamin Keen [bkeen@google.com](mailto:bkeen@google.com)  

Link:    <https://chromium-review.googlesource.com/7488911>

Set Pip window title directionality mode to DIRECTIONALITY\_AS\_URL

---


Expand for full commit details
```
     
    This change addresses a security UI spoofing vulnerability in both 
    Document and Video Picture-in-Picture (PiP) windows where Right-to-Left 
    Override (RTLO) characters in a malicious domain could cause the 
    displayed origin to appear as a trusted domain. 
     
    The fix ensures that the `views::Label` used for the PiP window title 
    always renders text in a Left-to-Right (LTR) direction. This is achieved 
    by setting the label directionality mode to `DIRECTIONALITY_AS_URL`, as 
    suggested in 
    https://chromium.googlesource.com/chromium/src/+/HEAD/docs/security/url_display_guidelines/url_display_guidelines.md#rtl 
     
    Bug: 474948986 
    Change-Id: I56298ea3f267dfb5be8509addb30bbd0b34f1163 
    Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/7488911 
    Reviewed-by: Fr <beaufort.francois@gmail.com> 
    Commit-Queue: Benjamin Keen <bkeen@google.com> 
    Cr-Commit-Position: refs/heads/main@{#1571906}

```

---

Files:

- M `chrome/browser/ui/views/frame/picture_in_picture_browser_frame_view.cc`
- M `chrome/browser/ui/views/frame/picture_in_picture_browser_frame_view.h`
- M `chrome/browser/ui/views/frame/picture_in_picture_browser_frame_view_interactive_uitest.cc`
- M `chrome/browser/ui/views/overlay/video_overlay_window_views.cc`
- M `chrome/browser/ui/views/overlay/video_overlay_window_views_unittest.cc`

---

Hash: [58a8c057b2b3b113e41ef8d8fb1228eb05d5a10c](https://chromiumdash.appspot.com/commit/58a8c057b2b3b113e41ef8d8fb1228eb05d5a10c)  

Date: Tue Jan 20 22:54:43 2026


---

### wf...@chromium.org (2026-02-04)

reporter: please do not host PoCs on external sites, add them to as attachments to the issue. (comments #1, #6, #7)

reporter: please do not restrict comments. ([comment #6](https://issues.chromium.org/issues/474948986#comment6))

repeated failure to comply will result in your disqualification from the chrome VRP program.

### se...@gmail.com (2026-02-04)

Hi Team,

Sorry for the inconvenience caused. The issue is with the hosting domain (origin display), so I have added only the domain.

I’ve attached the POC files for your reference please check them. I’ve also removed the comment restrictions. Comments are restricted by default, Kindly check this configuration.

Please let me know if any additional information is needed from my side.

Thanks.

### sp...@google.com (2026-02-20)

** NOTE: This is an automatically generated email **

Hello,

Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $3000.00 for this report.

Rationale for this decision:
Sec UI spoof, medium impact


Important: This payment will be issued by Bugcrowd. You will receive an email from Bugcrowd in the next 24 hours which contains a submission you must claim to be rewarded.

If you do not receive an email from them, please check your spam folder and then reach out to us via a comment here. For issues related to Bugcrowd itself, please contact them via https://bugcrowd.com/support.


Thank you for your efforts and helping us make Chrome more secure for all users!

Cheers,
Chrome VRP Panel Bot


P.S. One other thing we'd like to mention:

* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.

Please contact security-vrp@chromium.org with any questions.

### ch...@google.com (2026-05-01)

This bug has been closed for more than 14 weeks. Removing issue access restrictions.

## Bounty Award

> Sec UI spoof, medium impact

---
*Data from [Chromium Issue Tracker](https://issues.chromium.org/issues/474948986)*
